from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Static

from .. import __version__
from ..agent.events import ErrorEvent, Finished, ReasoningDelta, TextDelta, ToolFinished, ToolStarted, UsageUpdated
from ..agent.loop import AgentRunner
from ..agent.session import read_brain
from ..core.stats import UsageStats
from ..providers.store import ProviderStore
from ..rules.loader import load_rules
from ..rules.skills import discover_skills
from ..tools.diff import looks_binary
from .actions import SlashActions
from .messages import FileSelected
from .modals.preview import FilePreviewScreen
from .widgets.chat import ChatPane
from .widgets.diff import DiffPane
from .widgets.explorer import ExplorerPane
from .widgets.stats import StatsBar

PREVIEW_BYTES = 5_000_000

CSS = """
Screen {
    background: #0b0b0c;
    color: #d4d4d4;
}
#topbar {
    height: 1;
    background: #111111;
    color: #8a8a8a;
    padding: 0 1;
}
#workspace {
    height: 1fr;
}
#explorer {
    width: 30;
    border: round #262626;
    background: #0b0b0c;
}
#diff {
    width: 1fr;
    border: round #262626;
    background: #0b0b0c;
}
#chat {
    width: 46;
    border: round #262626;
    background: #0b0b0c;
}
.pane-title {
    height: 1;
    background: #111111;
    color: #8a8a8a;
    padding: 0 1;
}
#prompt {
    height: 3;
    border: round #262626;
    background: #111111;
    color: #d4d4d4;
    padding: 0 1;
}
#prompt:focus {
    border: round #666666;
}
#stats {
    height: 1;
    background: #111111;
    color: #8a8a8a;
    padding: 0 1;
}
.msg {
    margin: 0 0 1 0;
    padding: 0 1;
}
.msg.user {
    background: #171717;
}
.msg.assistant {
    background: #0f0f0f;
}
.msg.tool {
    color: #8a8a8a;
}
.msg.system {
    color: #8a8a8a;
}
#modal-card {
    width: 86;
    height: auto;
    border: round #3a3a3a;
    background: #111111;
    padding: 1 2;
}
#preview-card {
    width: 90%;
    height: 90%;
    border: round #3a3a3a;
    background: #111111;
    padding: 1 2;
}
#preview-text {
    height: 1fr;
    background: #0b0b0c;
}
.modal-title {
    text-style: bold;
    color: #d4d4d4;
    margin-bottom: 1;
}
.hint {
    color: #8a8a8a;
    margin-bottom: 1;
}
.error {
    color: #ff6b6b;
    height: 1;
}
.modal-actions {
    height: auto;
    align-horizontal: right;
    margin-top: 1;
}
Button {
    min-width: 10;
    background: #262626;
    color: #d4d4d4;
    border: none;
}
Button:hover {
    background: #333333;
}
#save {
    background: #d4d4d4;
    color: #0a0a0a;
}
#save:hover {
    background: #e5e5e5;
}
OptionList {
    height: auto;
    max-height: 18;
    background: #0b0b0c;
    border: round #262626;
}
"""


class PaiCodeApp(SlashActions, App):
    CSS = CSS
    TITLE = "Paicode"
    BINDINGS = [
        ("ctrl+l", "clear_chat", "Clear chat"),
        ("ctrl+r", "refresh_explorer", "Refresh files"),
        ("f1", "help", "Help"),
    ]

    def __init__(self, root: Path, store: ProviderStore | None = None):
        super().__init__()
        self.root = root
        self.store = store or ProviderStore()
        self.stats = UsageStats()
        self.rules = []
        self.skills = []
        self.busy = False
        self.chat = None
        self.diff = None
        self.explorer = None
        self.prompt = None
        self.stats_bar = None
        self._tool_line = None

    def compose(self) -> ComposeResult:
        yield Static("Paicode", id="topbar")
        yield Horizontal(
            ExplorerPane(self.root),
            DiffPane(),
            ChatPane(),
            id="workspace",
        )
        yield Input(placeholder="Message Paicode or type /help", id="prompt")
        yield StatsBar()

    def on_mount(self) -> None:
        self.chat = self.query_one(ChatPane)
        self.diff = self.query_one(DiffPane)
        self.explorer = self.query_one(ExplorerPane)
        self.prompt = self.query_one("#prompt", Input)
        self.stats_bar = self.query_one(StatsBar)
        self._reload_context()
        self._refresh_topbar()
        self._refresh_stats()
        self.chat.add_system(
            f"Paicode {__version__}. Type a request or /help. File operations are limited to the project root."
        )
        brain = read_brain(self.root)
        if brain:
            self.chat.add_system("Previous session:\n" + brain[:1200])
        provider = self.store.active()
        if provider:
            self.chat.add_system(
                f"Provider: {provider.name} | Model: {provider.model or 'unset'} | Keys: {len(provider.api_keys)}"
            )
        else:
            self.chat.add_system("No provider configured. Use /connect deepseek or /connect opencode.")
        self.prompt.focus()

    def _reload_context(self) -> None:
        self.rules = load_rules(self.root)
        self.skills = discover_skills(self.root)

    def _refresh_topbar(self) -> None:
        provider = self.store.active()
        provider_name = provider.name if provider else "no provider"
        model = provider.model if provider and provider.model else "no model"
        self.query_one("#topbar", Static).update(
            f" Paicode {__version__}  |  {provider_name} / {model}  |  {self.root}"
        )

    def _refresh_stats(self) -> None:
        provider = self.store.active()
        provider_name = provider.name if provider else ""
        model = provider.model if provider else ""
        self.stats_bar.update_stats(self.stats, provider_name, model, self.busy)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.prompt.value = ""
        if not text:
            return
        if self._handle_slash(text):
            return
        self._start_prompt(text)

    def _start_prompt(self, text: str) -> None:
        if self.busy:
            self.chat.add_system("A task is already running. Wait for it to finish.")
            return
        provider = self.store.active()
        if provider is None or not provider.api_keys:
            self.chat.add_system("No provider configured. Use /connect deepseek or /connect opencode.")
            self._cmd_connect("")
            return
        if not provider.model:
            self.chat.add_system("No model selected. Use /models, then /model.")
            self._fetch_models(open_modal=True)
            return
        self.busy = True
        self._reload_context()
        self.chat.add_user(text)
        self.chat.begin_assistant()
        self.diff.add_note(f"Task: {text[:220]}")
        self._refresh_stats()
        self._run_agent(text)

    @work(thread=True, exclusive=True)
    def _run_agent(self, text: str) -> None:
        try:
            provider = self.store.active()
            if provider is None:
                raise RuntimeError("No active provider.")
            runner = AgentRunner(
                self.root,
                provider,
                self.stats,
                self.rules,
                self.skills,
                emit=lambda event: self.call_from_thread(self._handle_event, event),
            )
            runner.run(text)
        except Exception as exc:
            self.call_from_thread(self._handle_event, ErrorEvent(f"{type(exc).__name__}: {exc}"))

    def _handle_event(self, event) -> None:
        if isinstance(event, TextDelta):
            self.chat.append_assistant(event.text)
        elif isinstance(event, ReasoningDelta):
            return
        elif isinstance(event, ToolStarted):
            self._tool_line = self.chat.add_tool(
                event.name, "running", self._summarize_arguments(event.arguments)
            )
        elif isinstance(event, ToolFinished):
            status = "ok" if event.ok else "failed"
            if self._tool_line is not None:
                self.chat.update_tool(self._tool_line, event.name, status, event.output)
                self._tool_line = None
            else:
                self.chat.add_tool(event.name, status, event.output)
            if event.diff:
                path = event.changed[0] if event.changed else event.name
                self.diff.add_diff(path, event.diff)
            if event.changed:
                self.explorer.refresh_tree()
            self._refresh_stats()
        elif isinstance(event, UsageUpdated):
            self.chat.end_assistant()
            self._refresh_stats()
        elif isinstance(event, Finished):
            self.chat.end_assistant()
            self.chat.add_system(f"Finished in {event.steps} step(s): {event.message[:400]}")
            self.busy = False
            self._refresh_stats()
            self.prompt.focus()
        elif isinstance(event, ErrorEvent):
            self.chat.end_assistant()
            self.chat.add_system(f"Error: {event.message}")
            self.busy = False
            self._refresh_stats()
            self.prompt.focus()

    def _summarize_arguments(self, arguments: dict) -> str:
        for key in ("command", "path", "pattern", "name", "source", "summary"):
            if key in arguments:
                return str(arguments[key])[:220]
        return ""

    def on_file_selected(self, message: FileSelected) -> None:
        try:
            raw = message.path.read_bytes()
            if len(raw) > PREVIEW_BYTES:
                self.chat.add_system(f"{message.path} is too large to preview.")
                return
            if looks_binary(raw):
                self.chat.add_system(f"{message.path} is a binary file.")
                return
            self.push_screen(
                FilePreviewScreen(message.path, raw.decode("utf-8", errors="ignore")),
                lambda _: self.prompt.focus(),
            )
        except OSError as exc:
            self.chat.add_system(f"Could not open {message.path}: {exc}")

    def action_clear_chat(self) -> None:
        self._cmd_clear("")

    def action_refresh_explorer(self) -> None:
        self.explorer.refresh_tree()

    def action_help(self) -> None:
        self._cmd_help("")
