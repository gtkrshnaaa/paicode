import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .settings import Settings, load_settings


def _normalize(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()
    return (cleaned or "tool")[:48]


@dataclass
class PluginTool:
    exposed: str
    original: str
    description: str
    parameters: dict
    handler: Callable[[dict], Any]


class PluginAPI:
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.tools: list[PluginTool] = []

    def add_tool(
        self,
        name: str,
        description: str,
        handler: Callable[[dict], Any],
        parameters: dict | None = None,
    ) -> None:
        original = str(name).strip()
        if not original:
            raise ValueError("Plugin tool requires a name.")
        if not callable(handler):
            raise ValueError("Plugin tool handler must be callable.")
        schema = parameters if isinstance(parameters, dict) else {"type": "object", "properties": {}}
        schema.setdefault("type", "object")
        self.tools.append(
            PluginTool(
                exposed=f"plugin__{_normalize(self.plugin_name)}__{_normalize(original)}"[:64],
                original=original,
                description=str(description).strip() or original,
                parameters=schema,
                handler=handler,
            )
        )


class PluginHost:
    def __init__(self, root: Path, settings: Settings | None = None):
        self.root = root
        self.settings = settings or load_settings(root)
        self.tools: dict[str, PluginTool] = {}
        self.errors: list[str] = []
        self._loaded = False
        self._load()

    def _resolve(self, value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else (self.root / path).resolve()

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        for index, entry in enumerate(self.settings.plugins):
            path = self._resolve(entry)
            if not path.is_file():
                self.errors.append(f"Plugin not found: {entry}")
                continue
            module_name = f"paicode_plugin_{index}_{_normalize(path.stem)}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise ImportError("could not create module spec")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                register = getattr(module, "register", None)
                if not callable(register):
                    raise ImportError("plugin must export register(api)")
                api = PluginAPI(path.stem)
                register(api)
            except Exception as exc:
                self.errors.append(f"Plugin {entry} failed: {type(exc).__name__}: {exc}")
                continue
            for tool in api.tools:
                if tool.exposed in self.tools:
                    self.errors.append(f"Plugin tool collision: {tool.exposed}")
                    continue
                self.tools[tool.exposed] = tool

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.exposed,
                    "description": tool.description[:1024],
                    "parameters": tool.parameters,
                },
            }
            for tool in self.tools.values()
        ]

    def execute(self, name: str, arguments: dict):
        from .tools.types import ToolResult

        tool = self.tools.get(name)
        if tool is None:
            return None
        try:
            result = tool.handler(arguments)
        except Exception as exc:
            return ToolResult(False, f"Error: plugin {tool.original} failed: {type(exc).__name__}: {exc}")
        if isinstance(result, ToolResult):
            return result
        if isinstance(result, tuple) and len(result) == 2:
            return ToolResult(bool(result[0]), str(result[1]), kind="plugin")
        return ToolResult(True, str(result), kind="plugin")
