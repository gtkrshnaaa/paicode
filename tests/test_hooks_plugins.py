import json
import sys
from pathlib import Path

from paicode.core.stats import UsageStats
from paicode.tools.registry import ToolRegistry


def write_settings(project: Path, payload: dict) -> None:
    path = project / ".paicode" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_pre_tool_hook_can_block_and_post_tool_hook_runs(project: Path, config_home: Path):
    guard = project / "guard.py"
    guard.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "if payload['event'] == 'pre_tool' and payload['tool'] in {'write', 'bash'}:\n"
        "    print('write and bash are blocked', file=sys.stderr)\n"
        "    sys.exit(2)\n"
        "print('allowed')\n",
        encoding="utf-8",
    )
    marker = project / "post.log"
    post = project / "post.py"
    post.write_text(
        "import json, pathlib, sys\n"
        "payload = json.load(sys.stdin)\n"
        "pathlib.Path('post.log').write_text(payload['event'] + ':' + payload['tool'])\n",
        encoding="utf-8",
    )
    write_settings(
        project,
        {
            "hooks": [
                {"event": "pre_tool", "command": f"{sys.executable} {guard}"},
                {"event": "post_tool", "command": f"{sys.executable} {post}"},
            ]
        },
    )
    registry = ToolRegistry(project, UsageStats(), [])
    blocked = registry.execute("bash", {"command": "echo nope"})
    assert blocked.ok is False
    assert "Blocked by hook" in blocked.output
    read = registry.execute("read", {"path": "README.md"})
    assert read.ok is True
    assert marker.read_text(encoding="utf-8") == "post_tool:read"


def test_plugin_tools_are_loaded_and_executed(project: Path, config_home: Path):
    plugin = project / "tools" / "hello.py"
    plugin.parent.mkdir()
    plugin.write_text(
        "def register(api):\n"
        "    api.add_tool(\n"
        "        'hello',\n"
        "        'Say hello',\n"
        "        lambda args: 'hello ' + str(args.get('name', 'world')),\n"
        "        {'type': 'object', 'properties': {'name': {'type': 'string'}}},\n"
        "    )\n",
        encoding="utf-8",
    )
    write_settings(project, {"plugins": ["tools/hello.py"]})
    registry = ToolRegistry(project, UsageStats(), [])
    names = {item["function"]["name"] for item in registry.schemas}
    assert "plugin__hello__hello" in names
    result = registry.execute("plugin__hello__hello", {"name": "paicode"})
    assert result.ok is True
    assert result.output == "hello paicode"
    assert registry.plugins.errors == []


def test_read_only_registry_hides_plugins(project: Path, config_home: Path):
    plugin = project / "hello.py"
    plugin.write_text(
        "def register(api):\n"
        "    api.add_tool('hello', 'Say hello', lambda args: 'hello')\n",
        encoding="utf-8",
    )
    write_settings(project, {"plugins": ["hello.py"]})
    registry = ToolRegistry(project, UsageStats(), [], read_only_shell=True, strict_read_only_shell=True)
    names = {item["function"]["name"] for item in registry.schemas}
    assert "plugin__hello__hello" not in names
    result = registry.execute("plugin__hello__hello", {})
    assert result.ok is False
