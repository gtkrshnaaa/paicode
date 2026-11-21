import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from uuid import uuid4

import openai
from openai import OpenAI

from .. import __version__
from ..core.errors import ConfigError, ProviderError
from .store import ProviderConfig


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class ChatUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: ChatUsage = field(default_factory=ChatUsage)
    finish_reason: str = ""
    model: str = ""


class KeyRing:
    def __init__(self, keys: list[str]):
        self.keys = [key for key in keys if key]
        self.index = 0
        self.cooldowns: dict[str, float] = {}
        self._lock = threading.RLock()

    def __len__(self) -> int:
        return len(self.keys)

    def current(self) -> str:
        with self._lock:
            if not self.keys:
                raise ProviderError("No API key configured. Use /connect or /key.")
            now = time.time()
            for _ in range(len(self.keys)):
                key = self.keys[self.index % len(self.keys)]
                if self.cooldowns.get(key, 0) <= now:
                    return key
                self.index = (self.index + 1) % len(self.keys)
            raise ProviderError("All API keys are temporarily rate limited. Retry in a few minutes.")

    def rotate(self) -> None:
        with self._lock:
            if self.keys:
                self.index = (self.index + 1) % len(self.keys)

    def mark(self, seconds: int = 600) -> None:
        with self._lock:
            if self.keys:
                self.cooldowns[self.keys[self.index % len(self.keys)]] = time.time() + seconds


class ProviderClient:
    def __init__(
        self,
        provider: ProviderConfig,
        timeout: float = 120.0,
        max_concurrency: int = 0,
    ):
        self.provider = provider
        self.timeout = timeout
        self.ring = KeyRing(provider.api_keys)
        self._gate = (
            threading.BoundedSemaphore(max(1, int(max_concurrency)))
            if max_concurrency
            else None
        )

    def _client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            base_url=self.provider.base_url,
            timeout=self.timeout,
            max_retries=0,
        )

    def _model_url(self) -> str:
        if self.provider.models_url:
            return self.provider.models_url
        return self.provider.base_url.rstrip("/") + "/models"

    def _get_json(self, url: str, api_key: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": f"paicode/{__version__}",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_models(self) -> list[str]:
        last_error = ""
        attempts = max(1, len(self.ring))
        for _ in range(attempts):
            api_key = self.ring.current()
            try:
                if self.provider.models_url:
                    payload = self._get_json(self._model_url(), api_key)
                    items = payload.get("data") or payload.get("models") or []
                else:
                    items = self._client(api_key).models.list().data
                models = []
                for item in items:
                    model_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
                    if model_id:
                        models.append(str(model_id))
                return sorted(set(models))
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code}"
                if exc.code in (401, 402, 403, 429):
                    self.ring.mark()
                    self.ring.rotate()
                    continue
                raise ProviderError(f"Model discovery failed: {last_error}") from exc
            except (openai.AuthenticationError, openai.PermissionDeniedError, openai.RateLimitError) as exc:
                last_error = str(exc)
                self.ring.mark()
                self.ring.rotate()
            except Exception as exc:
                raise ProviderError(f"Model discovery failed: {exc}") from exc
        raise ProviderError(f"Model discovery failed for all keys. {last_error}".strip())

    def stream(self, messages: list[dict], tools: list[dict] | None = None, on_text=None, on_reasoning=None, stop_event=None) -> ChatResult:
        if self._gate is None:
            return self._stream(messages, tools, on_text, on_reasoning, stop_event)
        with self._gate:
            return self._stream(messages, tools, on_text, on_reasoning, stop_event)

    def _stream(self, messages: list[dict], tools: list[dict] | None = None, on_text=None, on_reasoning=None, stop_event=None) -> ChatResult:
        if not self.provider.model:
            raise ConfigError("No model selected. Use /model or /models.")
        if not self.ring.keys:
            raise ProviderError("No API key configured. Use /connect or /key.")
        if stop_event is not None and stop_event.is_set():
            raise ProviderError("Stopped by user.")

        last_error = ""
        attempts = max(3, len(self.ring) * 3)
        for attempt in range(attempts):
            if stop_event is not None and stop_event.is_set():
                raise ProviderError("Stopped by user.")
            try:
                api_key = self.ring.current()
            except ProviderError:
                if attempt < attempts - 1:
                    time.sleep(min(8, 2 + attempt))
                    continue
                raise
            try:
                try:
                    return self._stream_once(api_key, messages, tools, on_text, on_reasoning, include_usage=True, stop_event=stop_event)
                except openai.BadRequestError as exc:
                    if "stream_options" in str(exc).lower():
                        return self._stream_once(api_key, messages, tools, on_text, on_reasoning, include_usage=False, stop_event=stop_event)
                    raise
            except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
                last_error = str(exc)
                self.ring.mark(600)
                self.ring.rotate()
            except openai.RateLimitError as exc:
                last_error = str(exc)
                wait = min(10, 2 ** min(attempt, 4))
                self.ring.mark(wait + 1)
                time.sleep(wait)
            except openai.APIConnectionError as exc:
                last_error = str(exc)
                if attempt >= attempts - 1:
                    raise ProviderError(f"Provider connection failed: {exc}") from exc
                time.sleep(min(8, 2 + attempt))
            except openai.APIStatusError as exc:
                if exc.status_code >= 500:
                    last_error = f"HTTP {exc.status_code}: {exc}"
                    if attempt >= attempts - 1:
                        raise ProviderError(f"Provider request failed ({exc.status_code}): {exc}") from exc
                    time.sleep(min(8, 2 + attempt))
                    continue
                raise ProviderError(f"Provider request failed ({exc.status_code}): {exc}") from exc
        raise ProviderError(f"All API keys failed. {last_error}".strip())

    def _stream_once(
        self,
        api_key: str,
        messages: list[dict],
        tools: list[dict] | None,
        on_text,
        on_reasoning,
        include_usage: bool,
        stop_event=None,
    ) -> ChatResult:
        if stop_event is None:
            return self._stream_once_blocking(
                api_key, messages, tools, on_text, on_reasoning, include_usage, None
            )
        result: dict = {}
        error: dict = {}
        finished = threading.Event()

        def guarded_text(chunk: str) -> None:
            if not stop_event.is_set() and on_text:
                on_text(chunk)

        def guarded_reasoning(chunk: str) -> None:
            if not stop_event.is_set() and on_reasoning:
                on_reasoning(chunk)

        def worker() -> None:
            try:
                result["value"] = self._stream_once_blocking(
                    api_key,
                    messages,
                    tools,
                    guarded_text,
                    guarded_reasoning,
                    include_usage,
                    stop_event,
                )
            except Exception as exc:
                error["value"] = exc
            finally:
                finished.set()

        thread = threading.Thread(target=worker, name="paicode-stream", daemon=True)
        thread.start()
        while not finished.wait(0.1):
            if stop_event.is_set():
                raise ProviderError("Stopped by user.")
        if stop_event.is_set():
            raise ProviderError("Stopped by user.")
        if "value" in error:
            raise error["value"]
        return result["value"]

    def _stream_once_blocking(
        self,
        api_key: str,
        messages: list[dict],
        tools: list[dict] | None,
        on_text,
        on_reasoning,
        include_usage: bool,
        stop_event=None,
    ) -> ChatResult:
        client = self._client(api_key)
        kwargs = {
            "model": self.provider.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if include_usage:
            kwargs["stream_options"] = {"include_usage": True}

        stream = client.chat.completions.create(**kwargs)
        text_parts: list[str] = []
        tool_state: dict[int, dict] = {}
        usage = ChatUsage()
        finish_reason = ""
        done = threading.Event()
        watcher = None

        def watch_stop() -> None:
            while not done.wait(0.1):
                if stop_event is not None and stop_event.is_set():
                    try:
                        stream.close()
                    except Exception:
                        pass
                    return

        if stop_event is not None:
            watcher = threading.Thread(target=watch_stop, name="paicode-stream-stop", daemon=True)
            watcher.start()

        try:
            for chunk in stream:
                if stop_event is not None and stop_event.is_set():
                    raise ProviderError("Stopped by user.")
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    usage = ChatUsage(
                        prompt_tokens=int(getattr(chunk_usage, "prompt_tokens", 0) or 0),
                        completion_tokens=int(getattr(chunk_usage, "completion_tokens", 0) or 0),
                        total_tokens=int(getattr(chunk_usage, "total_tokens", 0) or 0),
                    )
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                finish_reason = choice.finish_reason or finish_reason
                delta = choice.delta
    
                content = getattr(delta, "content", None)
                if isinstance(content, str) and content:
                    text_parts.append(content)
                    if on_text:
                        on_text(content)
    
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning is None and getattr(delta, "model_extra", None):
                    reasoning = delta.model_extra.get("reasoning_content")
                if isinstance(reasoning, str) and reasoning and on_reasoning:
                    on_reasoning(reasoning)
    
                for call_delta in (getattr(delta, "tool_calls", None) or []):
                    index = call_delta.index if call_delta.index is not None else 0
                    state = tool_state.setdefault(index, {"id": "", "name": "", "arguments": ""})
                    if call_delta.id:
                        state["id"] = call_delta.id
                    function = getattr(call_delta, "function", None)
                    if function is not None:
                        if function.name:
                            state["name"] += function.name
                        if function.arguments:
                            state["arguments"] += function.arguments
    
        except Exception:
            if stop_event is not None and stop_event.is_set():
                raise ProviderError("Stopped by user.")
            raise
        finally:
            done.set()
            if watcher is not None:
                watcher.join(timeout=1)
            try:
                stream.close()
            except Exception:
                pass
        tool_calls = []
        for index in sorted(tool_state):
            state = tool_state[index]
            tool_calls.append(
                ToolCall(
                    id=state["id"] or f"call_{index}_{uuid4().hex[:8]}",
                    name=state["name"],
                    arguments=state["arguments"] or "{}",
                )
            )

        return ChatResult(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
            model=self.provider.model,
        )
