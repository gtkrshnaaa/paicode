import argparse
import os
import shutil
import sys
from pathlib import Path

from rich.console import Console

from . import __version__
from .core.paths import config_file, project_root
from .core.stats import UsageStats
from .providers.client import ProviderClient
from .providers.presets import get_preset
from .providers.store import ProviderStore
from .rules.loader import load_rules, rule_summary
from .rules.skills import discover_skills, render_catalog
from .sessions import SessionStore, format_sessions, sessions_root


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


def _run_headless(root: Path, prompt: str, max_steps: int, show_diff: bool) -> int:
    from .agent.events import ErrorEvent, Finished, TextDelta, ToolFinished, ToolStarted, UsageUpdated
    from .agent.loop import AgentRunner

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
        elif isinstance(event, Finished):
            if state["started"]:
                console.print("")
            console.print(f"[dim]finished in {event.steps} step(s)[/dim]")
        elif isinstance(event, ErrorEvent):
            state["error"] = True
            if state["started"]:
                console.print("")
            console.print(f"[red]error: {event.message}[/red]")

    runner = AgentRunner(root, provider, stats, rules, skills, emit=on_event, max_steps=max_steps)
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


def _cmd_doctor(root: Path) -> int:
    store = ProviderStore()
    provider = store.active()
    tools = [tool for tool in ["git", "rg", "pytest", "python3", "node", "npm", "cargo", "go"] if shutil.which(tool)]
    print(f"Paicode: {__version__}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Project root: {root}")
    print(f"Config: {config_file()}")
    print(f"Provider: {provider.name if provider else 'none'}")
    if provider:
        print(f"Base URL: {provider.base_url}")
        print(f"Model: {provider.model or 'unset'}")
        print(f"Keys: {len(provider.api_keys)}")
    print(f"Tools: {', '.join(tools) or 'none'}")
    print(f"Sessions: {sessions_root()} ({len(SessionStore().list())})")
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

    subparsers.add_parser("doctor", help="Show environment, provider, rules, and skill status.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(_expand_session_args(raw_args))

    if args.command in {"session-lists", "sessions"}:
        return _cmd_sessions()

    root = _root(args)

    if args.command == "run":
        return _run_headless(root, " ".join(args.prompt), args.max_steps, args.diff)
    if args.command == "models":
        return _cmd_models(root)
    if args.command == "connect":
        return _cmd_connect(args)
    if args.command == "config":
        return _cmd_config(args)
    if args.command == "doctor":
        return _cmd_doctor(root)

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
    app = PaiCodeApp(root, ProviderStore(), session_store=session_store, session=session_data)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
