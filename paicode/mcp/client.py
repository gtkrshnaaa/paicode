import json
import os
import queue
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ..core.errors import PaicodeError


class McpError(PaicodeError):
    """Raised when an MCP server cannot complete a request."""


class StdioTransport:
    def __init__(self, command: list[str], cwd: Path, env: dict[str, str] | None = None):
        if not command:
            raise McpError("MCP stdio server requires a command.")
        self._lines: queue.Queue[str | None] = queue.Queue()
        self.process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env={**os.environ, **(env or {})},
        )
        self._reader = threading.Thread(target=self._read, name="paicode-mcp-stdio", daemon=True)
        self._reader.start()
        self._lock = threading.Lock()

    def _read(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def send(self, payload: dict) -> dict:
        if self.process.poll() is not None:
            raise McpError("MCP stdio server exited.")
        assert self.process.stdin is not None
        with self._lock:
            self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self.process.stdin.flush()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                line = self._lines.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise McpError("MCP stdio request timed out.") from exc
            if line is None:
                raise McpError("MCP stdio server closed its output.")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and message.get("id") == payload.get("id"):
                return message
        raise McpError("MCP stdio request timed out.")

    def notify(self, payload: dict) -> None:
        if self.process.poll() is not None:
            raise McpError("MCP stdio server exited.")
        assert self.process.stdin is not None
        with self._lock:
            self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self.process.stdin.flush()

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()


class HttpTransport:
    def __init__(self, url: str, headers: dict[str, str] | None = None, timeout: int = 30):
        if not url:
            raise McpError("MCP HTTP server requires a URL.")
        self.url = url
        self.headers = {str(key): str(value) for key, value in (headers or {}).items()}
        self.timeout = max(1, timeout)
        self.session_id = ""

    def _post(self, payload: dict) -> tuple[str, str]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self.headers,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.headers.get("Mcp-Session-Id"):
                    self.session_id = response.headers["Mcp-Session-Id"]
                return response.headers.get("Content-Type", ""), response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise McpError(f"MCP HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise McpError(f"MCP HTTP request failed: {exc}") from exc

    def send(self, payload: dict) -> dict:
        content_type, text = self._post(payload)
        if "text/event-stream" in content_type:
            for line in text.splitlines():
                if line.startswith("data:"):
                    try:
                        message = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if isinstance(message, dict) and message.get("id") == payload.get("id"):
                        return message
            raise McpError("MCP HTTP stream returned no matching response.")
        try:
            message = json.loads(text)
        except json.JSONDecodeError as exc:
            raise McpError("MCP HTTP server returned invalid JSON.") from exc
        if not isinstance(message, dict):
            raise McpError("MCP HTTP server returned a non-object response.")
        return message

    def notify(self, payload: dict) -> None:
        try:
            self._post(payload)
        except McpError:
            return

    def close(self) -> None:
        return None


class McpClient:
    def __init__(self, name: str, transport, timeout: int = 30):
        self.name = name
        self.transport = transport
        self.timeout = timeout
        self._counter = 0
        self._lock = threading.Lock()
        self.server_info: dict[str, Any] = {}
        self.capabilities: dict[str, Any] = {}
        self.tools: list[dict] = []
        self.started = False

    def _request(self, method: str, params: dict | None = None) -> dict:
        with self._lock:
            self._counter += 1
            request_id = self._counter
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        response = self.transport.send(payload)
        if "error" in response:
            error = response["error"]
            raise McpError(f"MCP {self.name} {method} failed: {error}")
        result = response.get("result", {})
        return result if isinstance(result, dict) else {"value": result}

    def start(self) -> None:
        if self.started:
            return
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "paicode", "version": "1"},
            },
        )
        self.server_info = result.get("serverInfo", {}) if isinstance(result.get("serverInfo"), dict) else {}
        self.capabilities = result.get("capabilities", {}) if isinstance(result.get("capabilities"), dict) else {}
        notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        try:
            self.transport.notify(notification)
        except Exception:
            pass
        self.started = True
        self.tools = self.list_tools()

    def list_tools(self) -> list[dict]:
        try:
            result = self._request("tools/list", {})
        except McpError:
            return []
        tools = result.get("tools", [])
        return [tool for tool in tools if isinstance(tool, dict) and str(tool.get("name", "")).strip()]

    def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        parts = result.get("content", [])
        text: list[str] = []
        if isinstance(parts, list):
            for part in parts:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text":
                    text.append(str(part.get("text", "")))
                elif part.get("type") == "resource":
                    resource = part.get("resource", {})
                    text.append(str(resource.get("text", "")) if isinstance(resource, dict) else str(resource))
                else:
                    text.append(f"[{part.get('type', 'content')}]")
        if not text and result.get("structuredContent") is not None:
            text.append(json.dumps(result["structuredContent"], ensure_ascii=False))
        return "\n".join(text).strip() or "MCP tool returned no text.", not bool(result.get("isError"))

    def list_resources(self) -> list[dict]:
        try:
            result = self._request("resources/list", {})
        except McpError:
            return []
        return [item for item in result.get("resources", []) if isinstance(item, dict)]

    def read_resource(self, uri: str) -> str:
        result = self._request("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        if isinstance(contents, list):
            return "\n".join(str(item.get("text", "")) for item in contents if isinstance(item, dict))
        return json.dumps(contents, ensure_ascii=False)

    def list_prompts(self) -> list[dict]:
        try:
            result = self._request("prompts/list", {})
        except McpError:
            return []
        return [item for item in result.get("prompts", []) if isinstance(item, dict)]

    def get_prompt(self, name: str, arguments: dict | None = None) -> str:
        result = self._request("prompts/get", {"name": name, "arguments": arguments or {}})
        messages = result.get("messages", [])
        if isinstance(messages, list):
            return "\n".join(
                str(item.get("content", {}).get("text", "")) if isinstance(item.get("content"), dict) else str(item.get("content", ""))
                for item in messages
                if isinstance(item, dict)
            )
        return json.dumps(result, ensure_ascii=False)

    def close(self) -> None:
        self.transport.close()
