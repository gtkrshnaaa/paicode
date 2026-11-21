import json
from pathlib import Path

from ..core.errors import PathSecurityError
from ..rules.skills import SkillMeta, find_skill, load_skill_text
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
        )
        self.explore_tools = ExploreTools(root, stats)

    def execute(self, name: str, arguments: dict | str) -> ToolResult:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError as exc:
                return ToolResult(False, f"Error: Invalid tool arguments JSON: {exc}")
        if not isinstance(arguments, dict):
            return ToolResult(False, "Error: Tool arguments must be an object.")

        try:
            return self._dispatch(name.strip().lower(), arguments)
        except PathSecurityError as exc:
            return ToolResult(False, f"Security error: {exc}")
        except (ValueError, OSError) as exc:
            return ToolResult(False, f"Error: {exc}")
        except Exception as exc:
            return ToolResult(False, f"Error: {type(exc).__name__}: {exc}")

    def _dispatch(self, name: str, args: dict) -> ToolResult:
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
        if name == "finish":
            self.finished = True
            self.summary = str(args.get("summary", "")).strip()
            return ToolResult(True, self.summary or "Task complete.", kind="finish")
        return ToolResult(False, f"Error: Unknown tool '{name}'.")
