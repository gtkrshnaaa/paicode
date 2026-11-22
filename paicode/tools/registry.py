import json
from pathlib import Path

from ..core.errors import PathSecurityError
from ..hooks import HookRunner
from ..mcp import get_mcp_manager
from ..plugins import PluginHost
from ..rules.skills import SkillMeta, find_skill, load_skill_text
from ..security import request_approval
from ..settings import load_settings, permission_effect
from ..tools.schemas import TOOL_SCHEMAS
from .diagnostics import DiagnosticsTools
from .explore import ExploreTools
from .fs import FileTools
from .search import SearchTools
from .shell import ShellTools
from .types import ToolResult


class ToolRegistry:
    def __init__(
        self,
        root: Path,
        stats,
        skills: list[SkillMeta],
        stop_event=None,
        allowed_write_paths: set[Path] | None = None,
        read_only_shell: bool = False,
        strict_read_only_shell: bool = False,
        enable_mcp: bool | None = None,
    ):
        self.root = root
        self.stats = stats
        self.skills = skills
        self.finished = False
        self.summary = ""
        self.files = FileTools(root, stats, allowed_write_paths=allowed_write_paths)
        self.search = SearchTools(root, stats)
        self.shell = ShellTools(
            root,
            stats,
            stop_event=stop_event,
            read_only_workspace=read_only_shell,
            strict_read_only=strict_read_only_shell,
        )
        self.explore_tools = ExploreTools(root, stats)
        self.settings = load_settings(root)
        self.diagnostics = DiagnosticsTools(root, self.settings.diagnostics)
        self.read_only = read_only_shell or strict_read_only_shell
        self.hooks = HookRunner(root, self.settings)
        external = not (read_only_shell or strict_read_only_shell)
        if enable_mcp is None:
            enable_mcp = external
        self.mcp = get_mcp_manager(root, self.settings) if enable_mcp else None
        self.plugins = PluginHost(root, self.settings) if external else None

    @property
    def schemas(self) -> list[dict]:
        blocked: set[str] = set()
        if self.read_only:
            blocked.update({"diagnostics", "write", "edit", "mkdir", "move", "delete"})
        schemas = [
            schema for schema in TOOL_SCHEMAS if schema["function"]["name"] not in blocked
        ]
        if self.plugins is not None:
            schemas.extend(self.plugins.schemas())
        if self.mcp is not None:
            schemas.extend(self.mcp.schemas())
        return schemas

    def execute(self, name: str, arguments: dict | str) -> ToolResult:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError as exc:
                return ToolResult(False, f"Error: Invalid tool arguments JSON: {exc}")
        if not isinstance(arguments, dict):
            return ToolResult(False, "Error: Tool arguments must be an object.")

        normalized = name.strip().lower()
        action, resource = self._permission_target(normalized, arguments)
        effect = permission_effect(self.settings, action, resource)
        if effect == "deny":
            return ToolResult(False, f"Denied by permission policy: {action} {resource}")
        if effect == "ask" and not request_approval(action, resource):
            return ToolResult(
                False,
                f"Approval required by permission policy: {action} {resource}",
            )
        pre_hook = self.hooks.run("pre_tool", {"tool": normalized, "arguments": arguments}, blocking=True)
        if not pre_hook.allowed:
            return ToolResult(False, "Blocked by hook: " + "; ".join(pre_hook.reasons))
        try:
            result = self._dispatch(normalized, arguments)
            self.hooks.run(
                "post_tool",
                {
                    "tool": normalized,
                    "arguments": arguments,
                    "ok": result.ok,
                    "output": result.output[:4_000],
                    "changed": result.changed,
                },
            )
            return result
        except PathSecurityError as exc:
            return ToolResult(False, f"Security error: {exc}")
        except (ValueError, OSError) as exc:
            return ToolResult(False, f"Error: {exc}")
        except Exception as exc:
            return ToolResult(False, f"Error: {type(exc).__name__}: {exc}")

    def _permission_target(self, name: str, args: dict) -> tuple[str, str]:
        if name == "bash":
            return "shell", str(args.get("command", "")).strip()
        if name in {"write", "edit", "delete"}:
            return "write", str(args.get("path", "")).strip()
        if name == "mkdir":
            return "write", str(args.get("path", "")).strip()
        if name == "move":
            return "write", f"{args.get('source', '')} -> {args.get('destination', '')}".strip()
        if name == "explore":
            return "explore", str(args.get("path", "")).strip()
        if name.startswith("mcp__"):
            return "mcp", name
        if name.startswith("plugin__"):
            return "plugin", name
        return "read", name

    def _dispatch(self, name: str, args: dict) -> ToolResult:
        if self.read_only and name in {"write", "edit", "mkdir", "move", "delete"}:
            return ToolResult(False, "Error: mutating tools are disabled in read-only mode.")
        if name == "read":
            return self.files.read(args["path"], args.get("offset", 1), args.get("limit", 400))
        if name == "write":
            return self.files.write(args["path"], args.get("content", ""))
        if name == "edit":
            return self.files.edit(
                args["path"],
                args.get("old_string", ""),
                args.get("new_string", ""),
                bool(args.get("replace_all", False)),
            )
        if name == "list":
            return self.files.list_dir(args.get("path", "."))
        if name == "glob":
            return self.search.glob(args["pattern"])
        if name == "grep":
            return self.search.grep(args["pattern"], args.get("path", "."), args.get("include"))
        if name == "bash":
            return self.shell.run(
                args["command"],
                args.get("timeout", 0),
                args.get("cwd", ""),
            )
        if name == "explore":
            return self.explore_tools.explore(
                args["path"],
                args.get("reason", ""),
                args.get("pattern", "*"),
                args.get("limit", 200),
            )
        if name == "skill":
            skill = find_skill(self.skills, args["name"])
            if skill is None:
                return ToolResult(False, f"Error: Skill '{args['name']}' was not found.")
            content = load_skill_text(skill)
            return ToolResult(True, f"# Skill: {skill.name}\n\n{content}", kind="skill")
        if name == "mkdir":
            return self.files.mkdir(args["path"])
        if name == "move":
            return self.files.move(args["source"], args["destination"])
        if name == "delete":
            return self.files.delete(args["path"], bool(args.get("recursive", False)))
        if name == "diagnostics":
            if self.read_only:
                return ToolResult(False, "Error: diagnostics are disabled in read-only mode.")
            return self.diagnostics.run(int(args.get("timeout", 120) or 120))
        if name == "finish":
            self.finished = True
            self.summary = str(args.get("summary", "")).strip()
            return ToolResult(True, self.summary or "Task complete.", kind="finish")
        if name.startswith("plugin__") and self.plugins is not None:
            result = self.plugins.execute(name, args)
            return result if result is not None else ToolResult(False, f"Error: Unknown plugin tool '{name}'.")
        if name.startswith("mcp__") and self.mcp is not None:
            return self.mcp.call(name, args)
        return ToolResult(False, f"Error: Unknown tool '{name}'.")
