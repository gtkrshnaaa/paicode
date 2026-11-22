import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from ..settings import McpServer, Settings, load_settings
from .client import HttpTransport, McpClient, McpError, StdioTransport


def _normalize(value: str, limit: int = 40) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()
    return (cleaned or "tool")[:limit]


@dataclass
class McpStatus:
    name: str
    transport: str
    connected: bool
    tools: int = 0
    error: str = ""


@dataclass
class McpManager:
    root: Path
    settings: Settings
    _clients: dict[str, McpClient] = field(default_factory=dict)
    _errors: dict[str, str] = field(default_factory=dict)
    _tool_map: dict[str, tuple[McpClient, str]] = field(default_factory=dict)
    _schemas: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _connect(self, server: McpServer) -> McpClient:
        if server.transport == "stdio":
            transport = StdioTransport(server.command, self.root, server.env)
        else:
            transport = HttpTransport(server.url, server.headers, server.timeout)
        client = McpClient(server.name, transport, server.timeout)
        client.start()
        return client

    def start(self) -> None:
        with self._lock:
            if self._clients or self._errors:
                return
            for name, server in self.settings.mcp_servers.items():
                if not server.enabled:
                    continue
                try:
                    client = self._connect(server)
                except Exception as exc:
                    self._errors[name] = f"{type(exc).__name__}: {exc}"
                    continue
                self._clients[name] = client
                for tool in client.tools:
                    tool_name = str(tool.get("name", "")).strip()
                    if not tool_name:
                        continue
                    exposed = f"mcp__{_normalize(name, 20)}__{_normalize(tool_name)}"[:64]
                    self._tool_map[exposed] = (client, tool_name)
                    schema = tool.get("inputSchema", {})
                    if not isinstance(schema, dict):
                        schema = {"type": "object", "properties": {}}
                    schema.setdefault("type", "object")
                    self._schemas.append(
                        {
                            "type": "function",
                            "function": {
                                "name": exposed,
                                "description": f"[{name}] {tool.get('description', tool_name)}"[:1024],
                                "parameters": schema,
                            },
                        }
                    )

    def schemas(self) -> list[dict]:
        self.start()
        return list(self._schemas)

    def call(self, name: str, arguments: dict):
        from ..tools.types import ToolResult

        self.start()
        target = self._tool_map.get(name)
        if target is None:
            return ToolResult(False, f"Error: Unknown MCP tool '{name}'.")
        client, tool_name = target
        try:
            output, ok = client.call_tool(tool_name, arguments)
        except McpError as exc:
            return ToolResult(False, f"Error: {exc}")
        return ToolResult(ok, output, kind="mcp")

    def status(self) -> list[McpStatus]:
        self.start()
        rows = []
        for name, server in self.settings.mcp_servers.items():
            if not server.enabled:
                continue
            client = self._clients.get(name)
            rows.append(
                McpStatus(
                    name=name,
                    transport=server.transport,
                    connected=client is not None,
                    tools=len(client.tools) if client else 0,
                    error=self._errors.get(name, ""),
                )
            )
        return rows

    def resources(self, server: str) -> list[dict]:
        self.start()
        client = self._clients.get(server)
        return client.list_resources() if client else []

    def read_resource(self, server: str, uri: str) -> str:
        self.start()
        client = self._clients.get(server)
        if client is None:
            raise McpError(f"MCP server '{server}' is not connected.")
        return client.read_resource(uri)

    def prompts(self, server: str) -> list[dict]:
        self.start()
        client = self._clients.get(server)
        return client.list_prompts() if client else []

    def get_prompt(self, server: str, name: str, arguments: dict | None = None) -> str:
        self.start()
        client = self._clients.get(server)
        if client is None:
            raise McpError(f"MCP server '{server}' is not connected.")
        return client.get_prompt(name, arguments)

    def close(self) -> None:
        with self._lock:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
            self._tool_map.clear()
            self._schemas.clear()
            self._errors.clear()


_MANAGERS: dict[str, McpManager] = {}
_MANAGER_LOCK = threading.Lock()


def get_mcp_manager(root: Path | str, settings: Settings | None = None) -> McpManager:
    key = str(Path(root).expanduser().resolve())
    with _MANAGER_LOCK:
        manager = _MANAGERS.get(key)
        if manager is None:
            manager = McpManager(Path(key), settings or load_settings(key))
            _MANAGERS[key] = manager
        return manager


def reset_mcp_manager(root: Path | str | None = None) -> None:
    with _MANAGER_LOCK:
        keys = [str(Path(root).expanduser().resolve())] if root else list(_MANAGERS)
        for key in keys:
            manager = _MANAGERS.pop(key, None)
            if manager is not None:
                manager.close()
