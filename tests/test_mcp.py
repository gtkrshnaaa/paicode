import json
import sys
from pathlib import Path

from paicode.cli import main
from paicode.mcp import reset_mcp_manager
from paicode.tools.registry import ToolRegistry
from paicode.core.stats import UsageStats

SERVER = r'''
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    method = message.get("method", "")
    params = message.get("params", {})
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}, "resources": {}}, "serverInfo": {"name": "demo", "version": "1"}}
    elif method == "tools/list":
        result = {"tools": [{"name": "echo", "description": "Echo text", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}]}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": "echo: " + str(params.get("arguments", {}).get("text", ""))}], "isError": False}
    elif method == "resources/list":
        result = {"resources": [{"uri": "demo://readme", "name": "readme"}]}
    elif method == "resources/read":
        result = {"contents": [{"uri": params.get("uri", ""), "text": "resource body"}]}
    elif method == "prompts/list":
        result = {"prompts": []}
    else:
        result = {}
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''


def write_settings(project: Path, command: list[str]) -> None:
    path = project / ".paicode" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "mcp": {
                    "servers": {
                        "demo": {
                            "transport": "stdio",
                            "command": command,
                            "timeout": 5,
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_mcp_stdio_tools_are_discovered_and_executed(project: Path, config_home: Path):
    server = project / "fake_mcp.py"
    server.write_text(SERVER, encoding="utf-8")
    write_settings(project, [sys.executable, str(server)])
    reset_mcp_manager(project)
    try:
        registry = ToolRegistry(project, UsageStats(), [])
        schemas = registry.schemas
        names = {item["function"]["name"] for item in schemas}
        assert "mcp__demo__echo" in names
        result = registry.execute("mcp__demo__echo", {"text": "hello"})
        assert result.ok
        assert result.output == "echo: hello"
        status = registry.mcp.status()
        assert status[0].name == "demo"
        assert status[0].connected is True
        assert status[0].tools == 1
        assert registry.mcp.read_resource("demo", "demo://readme") == "resource body"
    finally:
        reset_mcp_manager(project)


def test_read_only_registry_hides_mcp_tools(project: Path, config_home: Path):
    server = project / "fake_mcp.py"
    server.write_text(SERVER, encoding="utf-8")
    write_settings(project, [sys.executable, str(server)])
    reset_mcp_manager(project)
    try:
        registry = ToolRegistry(project, UsageStats(), [], read_only_shell=True, strict_read_only_shell=True)
        names = {item["function"]["name"] for item in registry.schemas}
        assert not any(name.startswith("mcp__") for name in names)
        result = registry.execute("mcp__demo__echo", {"text": "blocked"})
        assert result.ok is False
        assert "Unknown tool" in result.output
    finally:
        reset_mcp_manager(project)


def test_mcp_cli_status_and_tools(project: Path, config_home: Path, capsys):
    server = project / "fake_mcp.py"
    server.write_text(SERVER, encoding="utf-8")
    write_settings(project, [sys.executable, str(server)])
    reset_mcp_manager(project)
    try:
        assert main(["--path", str(project), "mcp", "status"]) == 0
        status = capsys.readouterr().out
        assert "demo: stdio connected tools=1" in status
        assert main(["--path", str(project), "mcp", "tools"]) == 0
        tools = capsys.readouterr().out
        assert "mcp__demo__echo" in tools
    finally:
        reset_mcp_manager(project)


def test_mcp_http_transport(project: Path, config_home: Path):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            message = json.loads(self.rfile.read(length))
            if "id" not in message:
                self.send_response(202)
                self.end_headers()
                return
            method = message.get("method")
            if method == "initialize":
                result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "remote"}}
            elif method == "tools/list":
                result = {"tools": [{"name": "ping", "description": "Ping", "inputSchema": {"type": "object", "properties": {}}}]}
            elif method == "tools/call":
                result = {"content": [{"type": "text", "text": "pong"}]}
            else:
                result = {}
            body = json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        path = project / ".paicode" / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "mcp": {
                        "servers": {
                            "remote": {
                                "transport": "http",
                                "url": f"http://127.0.0.1:{server.server_address[1]}/mcp",
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        reset_mcp_manager(project)
        registry = ToolRegistry(project, UsageStats(), [])
        result = registry.execute("mcp__remote__ping", {})
        assert result.ok is True
        assert result.output == "pong"
    finally:
        reset_mcp_manager(project)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
