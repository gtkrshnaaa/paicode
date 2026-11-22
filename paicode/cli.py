import argparse
import os
import shutil
import sys
from pathlib import Path

from rich.console import Console

from . import __version__
from .core.paths import project_root
from .core.stats import UsageStats
from .providers.client import ProviderClient
from .providers.presets import get_preset
from .providers.store import ProviderStore
from .settings import load_settings
from .checkpoints import CheckpointStore
from .mcp import get_mcp_manager
from .rules.loader import load_rules, rule_summary
from .rules.skills import discover_skills, render_catalog
from .db import Database
from .sessions import SessionStore, format_sessions
from .tools.sandbox import sandbox_available


def _root(args) -> Path:
    if getattr(args, "path", ""):
        return Path(args.path).expanduser().resolve()
    return project_root()


def _require_provider(store: ProviderStore):
    provider = store.active()
    if provider is None:
        raise SystemExit("No provider configured. Run: pai connect deepseek <base_url> --key-env DEEPSEEK_API_KEY")
    if not provider.api_keys:
        raise SystemExit(f"Provider '{provider.name}' has no API key. Use the /key command in the TUI.")
    return provider


def _run_headless(root: Path, prompt: str, max_steps: int, show_diff: bool, single_agent: bool = False) -> int:
    from .agent.events import (
        AgentPhase,
        AgentStatus,
        ErrorEvent,
        Finished,
        TextDelta,
        ToolFinished,
        ToolStarted,
        UsageUpdated,
    )
    from .agent.loop import AgentRunner
    from .agents import SmartRunner

    store = ProviderStore()
    provider = _require_provider(store)
    if not provider.model:
        raise SystemExit("No model selected. Run: pai config set-model <model>")

    console = Console(highlight=False, soft_wrap=True)
    stats = UsageStats()
    rules = load_rules(root)
    skills = discover_skills(root)
    state = {"error": False, "started": False}

    def on_event(event) -> None:
        if isinstance(event, TextDelta):
            state["started"] = True
            console.print(event.text, end="", markup=False)
        elif isinstance(event, ToolStarted):
            if state["started"]:
                console.print("")
                state["started"] = False
            console.print(f"[dim]{event.name}[/dim]", end=" ")
        elif isinstance(event, ToolFinished):
            status = "ok" if event.ok else "failed"
            console.print(f"[dim]{status}[/dim]")
            if show_diff and event.diff:
                console.print(event.diff, style="dim")
        elif isinstance(event, UsageUpdated):
            return
        elif isinstance(event, AgentPhase):
            if state["started"]:
                console.print("")
                state["started"] = False
            count = f" {event.active}/{event.total}" if event.total else ""
            console.print(f"[dim]phase {event.phase}: {event.detail}{count}[/dim]")
        elif isinstance(event, AgentStatus):
            if event.status in {"failed", "object"}:
                console.print(f"[dim]agent {event.agent_id} {event.role}: {event.status} {event.detail}[/dim]")
        elif isinstance(event, Finished):
            if state["started"]:
                console.print("")
            console.print(f"[dim]finished in {event.steps} step(s)[/dim]")
        elif isinstance(event, ErrorEvent):
            state["error"] = True
            if state["started"]:
                console.print("")
            console.print(f"[red]error: {event.message}[/red]")

    if single_agent:
        runner = AgentRunner(root, provider, stats, rules, skills, emit=on_event, max_steps=max_steps)
    else:
        runner = SmartRunner(root, provider, stats, rules, skills, emit=on_event)
    runner.run(prompt)
    if state["started"]:
        console.print("")
    console.print(f"[dim]{stats.summary()}[/dim]")
    return 1 if state["error"] else 0


def _cmd_models(root: Path) -> int:
    store = ProviderStore()
    provider = _require_provider(store)
    client = ProviderClient(provider)
    try:
        models = client.list_models()
    except Exception as exc:
        print(f"Model discovery failed: {exc}", file=sys.stderr)
        return 1
    if models:
        store.set_models(provider.name, models)
        for model in models:
            marker = "*" if model == provider.model else " "
            print(f"{marker} {model}")
    else:
        print("The provider returned no models.")
    return 0


def _cmd_connect(args) -> int:
    api_key = args.api_key or ""
    if args.key_env:
        api_key = os.getenv(args.key_env, "")
    if not api_key:
        print("Provide an API key or --key-env with the environment variable name.", file=sys.stderr)
        return 1
    store = ProviderStore()
    preset = get_preset(args.name)
    models_url = args.models_url or (preset.models_url if preset else "")
    try:
        provider = store.upsert(
            args.name,
            args.base_url,
            api_key=api_key,
            model=args.model or (preset.model if preset else ""),
            models_url=models_url,
        )
        store.set_active(provider.name)
    except Exception as exc:
        print(f"Could not save provider: {exc}", file=sys.stderr)
        return 1
    print(store.redacted())
    return 0


def _cmd_config(args) -> int:
    store = ProviderStore()
    command = args.config_cmd or "show"
    if command == "show":
        print(store.redacted())
        return 0
    provider = store.active()
    if provider is None:
        print("No active provider.", file=sys.stderr)
        return 1
    try:
        if command == "set-key":
            store.add_key(provider.name, args.value)
        elif command == "set-base-url":
            store.upsert(provider.name, args.value)
        elif command == "set-model":
            store.set_model(provider.name, args.value)
        elif command == "use":
            store.set_active(args.value)
        elif command == "remove":
            store.remove(args.value)
    except Exception as exc:
        print(f"Configuration failed: {exc}", file=sys.stderr)
        return 1
    print(store.redacted())
    return 0


def _cmd_sessions() -> int:
    print(format_sessions(SessionStore().list()))
    return 0


def _expand_session_args(argv: list[str]) -> list[str]:
    if not any(argument.startswith("--s-") for argument in argv):
        return list(argv)
    store = SessionStore()
    expanded = []
    for argument in argv:
        if argument.startswith("--") and not argument.startswith("---"):
            candidate = argument[2:]
            if candidate.startswith("s-") and store.find(candidate):
                expanded.extend(["--session", candidate])
                continue
        expanded.append(argument)
    return expanded


def _cmd_serve(host: str, port: int, token: str) -> int:
    from .server import create_server

    server = create_server(host, port, token)
    actual_host, actual_port = server.server_address[:2]
    print(f"Paicode console: http://{actual_host}:{actual_port}")
    print(f"Token: {server.token}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()
    return 0


def _cmd_rewind(root: Path, checkpoint_id: str) -> int:
    store = CheckpointStore(root)
    if not checkpoint_id:
        rows = store.list(limit=20)
        if not rows:
            print("No checkpoints yet.")
            return 0
        for row in rows:
            print(f"{row.id}  {row.created_at}  files={len(row.files)}")
        return 0
    checkpoint, restored = store.restore("" if checkpoint_id == "latest" else checkpoint_id)
    if checkpoint is None:
        print(f"Checkpoint '{checkpoint_id}' was not found.", file=sys.stderr)
        return 1
    print(f"Restored {checkpoint.id}: {len(restored)} file(s)")
    for path in restored:
        print(f"  {path}")
    return 0


def _cmd_mcp(root: Path, action: str, server: str) -> int:
    manager = get_mcp_manager(root, load_settings(root))
    rows = manager.status()
    if action == "status":
        if not rows:
            print("No MCP servers configured. Add them under mcp.servers in .paicode/settings.json.")
            return 0
        for row in rows:
            state = "connected" if row.connected else "failed"
            detail = f" tools={row.tools}" if row.connected else f" {row.error}"
            print(f"{row.name}: {row.transport} {state}{detail}")
        return 0
    if action == "tools":
        for schema in manager.schemas():
            function = schema.get("function", {})
            print(f"{function.get('name')}: {function.get('description', '')}")
        return 0
    if action == "resources":
        if not server:
            print("Usage: pai mcp resources <server>", file=sys.stderr)
            return 1
        for item in manager.resources(server):
            print(f"{item.get('uri', '')} {item.get('name', '')}")
        return 0
    if action == "prompts":
        if not server:
            print("Usage: pai mcp prompts <server>", file=sys.stderr)
            return 1
        for item in manager.prompts(server):
            print(f"{item.get('name', '')}: {item.get('description', '')}")
        return 0
    print(f"Unknown MCP action: {action}", file=sys.stderr)
    return 1


def _cmd_doctor(root: Path) -> int:
    store = ProviderStore()
    provider = store.active()
    tools = [tool for tool in ["git", "rg", "pytest", "python3", "node", "npm", "cargo", "go"] if shutil.which(tool)]
    print(f"Paicode: {__version__}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Project root: {root}")
    print(f"Provider: {provider.name if provider else 'none'}")
    if provider:
        print(f"Base URL: {provider.base_url}")
        print(f"Model: {provider.model or 'unset'}")
        print(f"Keys: {len(provider.api_keys)}")
    print(f"Tools: {', '.join(tools) or 'none'}")
    print(f"Shell: {'bubblewrap sandbox' if sandbox_available() else 'direct execution'}")
    print("Agents: smart routing | 22-agent team | single-agent fallback")
    database = Database()
    database.initialize()
    counts = database.counts()
    print(f"Database: {database.path}")
    print(f"Sessions: {counts['sessions']}")
    print(f"Provider presets: {counts['provider_presets']}")
    print(rule_summary(load_rules(root)))
    skills = discover_skills(root)
    print(f"Skills: {len(skills)}")
    if skills:
        print(render_catalog(skills))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pai",
        description="Paicode, a terminal coding agent with a multi-pane TUI.",
    )
    parser.add_argument("--version", action="version", version=f"Paicode {__version__}")
    parser.add_argument("--path", default="", help="Project root. Defaults to the current directory.")
    parser.add_argument("--session", default="", help="Open a session by ID or unique prefix.")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Back up the database, drop every table, migrate fresh, and seed provider presets.",
    )
    parser.add_argument(
        "--single-agent",
        action="store_true",
        help="Bypass the 22-agent council for a small task.",
    )
    parser.add_argument(
        "--session-lists",
        "--sessions",
        action="store_true",
        dest="session_lists",
        help="List every Paicode session with workspace and timestamps.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one prompt without the TUI.")
    run_parser.add_argument("prompt", nargs="+")
    run_parser.add_argument(
        "--max-steps",
        type=int,
        default=0,
        help="Optional model-turn ceiling. 0 means unlimited (default).",
    )
    run_parser.add_argument("--diff", action="store_true", help="Print file diffs.")
    run_parser.add_argument(
        "--single-agent",
        action="store_true",
        dest="single_agent",
        help="Bypass the 22-agent council for a small task.",
    )

    subparsers.add_parser("models", help="List models from the active provider.")
    subparsers.add_parser(
        "session-lists",
        aliases=["sessions"],
        help="List every Paicode session with workspace and timestamps.",
    )

    connect_parser = subparsers.add_parser("connect", help="Configure a provider from the command line.")
    connect_parser.add_argument("name")
    connect_parser.add_argument("base_url")
    connect_parser.add_argument("api_key", nargs="?", default="")
    connect_parser.add_argument("--key-env", default="", help="Read the API key from this environment variable.")
    connect_parser.add_argument("--model", default="")
    connect_parser.add_argument("--models-url", default="")

    config_parser = subparsers.add_parser("config", help="Inspect or edit provider configuration.")
    config_sub = config_parser.add_subparsers(dest="config_cmd")
    config_sub.add_parser("show")
    for name in ["set-key", "set-base-url", "set-model", "use", "remove"]:
        child = config_sub.add_parser(name)
        child.add_argument("value")

    serve_parser = subparsers.add_parser("serve", help="Run the local HTTP API and web console.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--token", default=os.getenv("PAICODE_SERVER_TOKEN", ""))

    rewind_parser = subparsers.add_parser("rewind", help="List or restore file checkpoints.")
    rewind_parser.add_argument("checkpoint", nargs="?", default="", help="Checkpoint ID prefix or 'latest'.")

    mcp_parser = subparsers.add_parser("mcp", help="Inspect configured MCP servers and tools.")
    mcp_parser.add_argument("action", nargs="?", default="status", choices=["status", "tools", "resources", "prompts"])
    mcp_parser.add_argument("server", nargs="?", default="")

    subparsers.add_parser("doctor", help="Show environment, provider, rules, and skill status.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(_expand_session_args(raw_args))

    if args.session_lists:
        return _cmd_sessions()

    if args.reset_db:
        result = Database().reset()
        print("Paicode database reset")
        print("----------------------")
        print(f"Database:  {result['path']}")
        print(f"Backup:    {result['backup'] or 'none'}")
        print(f"Migrations:{result['migrations']:>2}")
        print(f"Seeded:    {len(result['seeded'])} provider presets")
        print("Providers: " + ", ".join(result["seeded"]))
        return 0

    if args.command in {"session-lists", "sessions"}:
        return _cmd_sessions()

    root = _root(args)

    if args.command == "run":
        return _run_headless(
            root,
            " ".join(args.prompt),
            args.max_steps,
            args.diff,
            single_agent=bool(args.single_agent),
        )
    if args.command == "models":
        return _cmd_models(root)
    if args.command == "connect":
        return _cmd_connect(args)
    if args.command == "config":
        return _cmd_config(args)
    if args.command == "doctor":
        return _cmd_doctor(root)
    if args.command == "mcp":
        return _cmd_mcp(root, args.action, args.server)
    if args.command == "rewind":
        return _cmd_rewind(root, args.checkpoint)
    if args.command == "serve":
        return _cmd_serve(args.host, args.port, args.token)

    from .tui.app import PaiCodeApp

    session_store = SessionStore()
    if args.session:
        record = session_store.find(args.session)
        if record is None:
            print(f"Session '{args.session}' was not found.", file=sys.stderr)
            return 1
        root = Path(record.workspace).expanduser().resolve()
        if not root.is_dir():
            print(f"Session workspace is missing: {record.workspace}", file=sys.stderr)
            return 1
        session_data = session_store.touch(record.id) or session_store.get(record.id)
    else:
        if not root.is_dir():
            print(f"Project root does not exist: {root}", file=sys.stderr)
            return 1
        session_data = session_store.create(root)
    app = PaiCodeApp(
        root,
        ProviderStore(),
        session_store=session_store,
        session=session_data,
        multi_agent=not bool(args.single_agent),
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
