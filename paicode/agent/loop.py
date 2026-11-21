import json
import os
import re
from pathlib import Path

from ..core.errors import PaicodeError
from ..core.stats import UsageStats
from ..providers.client import ProviderClient
from ..providers.store import ProviderConfig
from ..rules.loader import RuleFile
from ..rules.skills import SkillMeta
from ..tools.registry import ToolRegistry
from ..tools.schemas import TOOL_SCHEMAS
from ..tools.types import ToolResult
from .events import (
    ErrorEvent,
    Finished,
    ReasoningDelta,
    TextDelta,
    ToolFinished,
    ToolStarted,
    UsageUpdated,
)
from .prompts import build_system_prompt
from .session import SessionState, append_history, write_brain


DEFAULT_CONTEXT_CHARS = 2_500_000
TOOL_CONTENT_CHARS = 200_000
ASSISTANT_CONTENT_CHARS = 400_000
LOOP_WINDOW = 5


def _redact(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-...", str(text))


def context_budget() -> int:
    raw = os.getenv("PAICODE_CONTEXT_CHARS", str(DEFAULT_CONTEXT_CHARS))
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_CONTEXT_CHARS
    return value if value > 0 else 10**12


def call_signature(name: str, arguments: str) -> str:
    try:
        payload = json.loads(arguments or "{}")
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        normalized = arguments
    return f"{name}:{normalized}"[:8_000]


def compact_messages(messages: list[dict], max_chars: int | None = None, keep_last: int = 6) -> list[dict]:
    budget = context_budget() if max_chars is None else max_chars
    system = [message for message in messages if message.get("role") == "system"]
    rest = [dict(message) for message in messages if message.get("role") != "system"]

    for message in rest:
        if message.get("role") == "tool" and isinstance(message.get("content"), str):
            message["content"] = message["content"][:TOOL_CONTENT_CHARS]
        elif message.get("role") == "assistant" and isinstance(message.get("content"), str):
            message["content"] = message["content"][:ASSISTANT_CONTENT_CHARS]

    def size() -> int:
        return sum(len(str(message.get("content", ""))) for message in rest)

    while size() > budget and len(rest) > keep_last:
        dropped = rest.pop(0)
        if dropped.get("role") == "assistant" and dropped.get("tool_calls"):
            while rest and rest[0].get("role") == "tool":
                rest.pop(0)

    return system + rest


class AgentRunner:
    def __init__(
        self,
        root: Path,
        provider: ProviderConfig,
        stats: UsageStats,
        rules: list[RuleFile],
        skills: list[SkillMeta],
        emit,
        max_steps: int = 0,
    ):
        self.root = root
        self.provider = provider
        self.stats = stats
        self.emit = emit
        self.max_steps = max(0, int(max_steps))
        self.rules = rules
        self.skills = skills
        self.client = ProviderClient(provider)
        self.registry = ToolRegistry(root, stats, skills)
        self.session = SessionState(root=root)
        self.messages = [{"role": "system", "content": build_system_prompt(root, rules, skills)}]

    def _send(self, event) -> None:
        try:
            self.emit(event)
        except Exception:
            pass

    def run(self, user_text: str) -> str:
        self.session.turns += 1
        self.session.last_request = user_text
        self.messages.append({"role": "user", "content": user_text})

        steps = 0
        final_text = ""
        failed = False
        try:
            recent_calls: list[str] = []
            while True:
                if self.max_steps > 0 and steps >= self.max_steps:
                    failed = True
                    self._send(ErrorEvent(f"Configured step limit reached after {steps} model turns."))
                    break
                steps += 1
                self.messages = compact_messages(self.messages)
                result = self.client.stream(
                    self.messages,
                    TOOL_SCHEMAS,
                    on_text=lambda chunk: self._send(TextDelta(chunk)),
                    on_reasoning=lambda chunk: self._send(ReasoningDelta(chunk)),
                )
                self.stats.record_usage(
                    result.usage.prompt_tokens,
                    result.usage.completion_tokens,
                    result.usage.total_tokens,
                )
                self._send(UsageUpdated(self.stats))
                final_text = result.text or final_text

                assistant_message = {"role": "assistant", "content": result.text or None}
                if result.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": call.arguments},
                        }
                        for call in result.tool_calls
                    ]
                if result.text or result.tool_calls:
                    self.messages.append(assistant_message)

                if not result.tool_calls:
                    if not result.text and not final_text:
                        failed = True
                        self._send(ErrorEvent("Provider returned an empty response."))
                    break

                loop_detected = False
                for call in result.tool_calls:
                    signature = call_signature(call.name, call.arguments)
                    recent_calls.append(signature)
                    recent_calls = recent_calls[-8:]
                    if len(recent_calls) >= LOOP_WINDOW and len(set(recent_calls[-LOOP_WINDOW:])) == 1:
                        failed = True
                        loop_detected = True
                        self._send(
                            ErrorEvent(
                                "Repeated identical tool call detected. "
                                "Stopping to avoid an infinite loop."
                            )
                        )
                        break
                    try:
                        parsed_arguments = json.loads(call.arguments or "{}")
                        if not isinstance(parsed_arguments, dict):
                            raise ValueError("arguments must be an object")
                    except (json.JSONDecodeError, ValueError) as exc:
                        self._send(ToolStarted(call.name, {"raw": call.arguments}))
                        tool_result = ToolResult(
                            ok=False,
                            output=f"Error: invalid tool arguments: {exc}",
                            kind="error",
                        )
                    else:
                        self._send(ToolStarted(call.name, parsed_arguments))
                        tool_result = self.registry.execute(call.name, parsed_arguments)

                    self._send(
                        ToolFinished(
                            name=call.name,
                            ok=tool_result.ok,
                            output=tool_result.output,
                            diff=tool_result.diff,
                            changed=tool_result.changed,
                            kind=tool_result.kind,
                        )
                    )
                    self.session.add_changed(tool_result.changed)
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": tool_result.output[:TOOL_CONTENT_CHARS],
                        }
                    )

                if loop_detected:
                    break

                if self.registry.finished:
                    final_text = self.registry.summary or final_text
                    break
        except PaicodeError as exc:
            failed = True
            self._send(ErrorEvent(_redact(str(exc))))
        except Exception as exc:
            failed = True
            self._send(ErrorEvent(_redact(f"{type(exc).__name__}: {exc}")))

        self.session.last_summary = final_text
        try:
            write_brain(self.session, self.stats)
            append_history(
                self.root,
                self.session.last_request,
                f"Summary: {final_text}\nChanged: {', '.join(self.session.changed_files)}",
            )
        except OSError:
            pass
        if not failed:
            self._send(Finished(final_text or "Task finished.", steps))
        return final_text
