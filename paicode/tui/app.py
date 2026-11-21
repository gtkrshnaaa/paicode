import time
from pathlib import Path

from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static

from .. import __version__
from ..agent.events import ErrorEvent, Finished, ReasoningDelta, TextDelta, ToolFinished, ToolStarted, UsageUpdated
from ..agent.loop import AgentRunner
from ..core.stats import UsageStats
from ..providers.store import ProviderStore
from ..rules.loader import load_rules
from ..rules.skills import discover_skills
from ..sessions import SessionData, SessionStore, display_time, format_session_detail, format_sessions, now_iso
from ..tools.diff import looks_binary
from .actions import SlashActions
from .commands import filter_commands
from .messages import FileSelected
from .modals.preview import FilePreviewScreen
from .theme import MONOCHROME
from .widgets.chat import ChatPane
from .widgets.diff import DiffPane
from .widgets.explorer import ExplorerPane
from .widgets.prompt import PromptInput
from .widgets.stats import StatsBar
from .widgets.suggestions import SuggestionBar

PREVIEW_BYTES = 5_000_000

CSS = """
Screen {
    background: #0b0b0c;
    color: #d4d4d4;
    scrollbar-color: #3a3a3a;
    scrollbar-color-hover: #4a4a4a;
    scrollbar-color-active: #5a5a5a;
    scrollbar-background: #111111;
    scrollbar-background-hover: #111111;
    scrollbar-background-active: #111111;
    scrollbar-corner-color: #111111;
}
ModalScreen {
    align: center middle;
}
VerticalScroll, RichLog, Tree, TextArea, OptionList {
    scrollbar-size-vertical: 0;
    scrollbar-size-horizontal: 0;
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
    padding: 1 0 0 0;
}
#diff {
    width: 1fr;
    border: round #262626;
    background: #0b0b0c;
    padding: 1 0 0 0;
}
#chat {
    width: 46;
    border: round #262626;
    background: #0b0b0c;
    padding: 1 0 0 0;
}
#chat-scroll {
    height: 1fr;
}
#chat-status {
    height: 2;
    background: #111111;
    color: #8a8a8a;
    padding: 0 1;
}
#suggestions {
    display: none;
    height: auto;
    border: round #262626;
    background: #111111;
    color: #8a8a8a;
    padding: 0 1;
}
#prompt {
    height: 3;
    min-height: 3;
    max-height: 14;
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
    height: 85%;
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
    color: #e5e5e5;
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

    def __init__(
        self,
        root: Path,
        store: ProviderStore | None = None,
        session_store: SessionStore | None = None,
        session: SessionData | None = None,
    ):
        super().__init__()
        self.register_theme(MONOCHROME)
        self.theme = MONOCHROME.name
        self.session_store = session_store or SessionStore()
        self.session = session or self.session_store.create(root)
        self.root = Path(self.session.record.workspace)
        self.store = store or ProviderStore()
        self.stats = UsageStats.from_dict(self.session.stats) if self.session.stats else UsageStats()
        self.rules = []
        self.skills = []
        self.busy = False
        self.chat = None
        self.diff = None
        self.explorer = None
        self.prompt = None
        self.stats_bar = None
        self.suggestions_bar = None
        self._tool_line = None
        self._suggestions = []
        self._suggestion_index = 0
        self._prompt_queue = []
        self._active_runner = None
        self._escape_count = 0
        self._last_escape = 0.0

    def compose(self) -> ComposeResult:
        yield Static("Paicode", id="topbar")
        yield Horizontal(
            ExplorerPane(self.root),
            DiffPane(),
            ChatPane(),
            id="workspace",
        )
        yield SuggestionBar()
        yield PromptInput(placeholder="Message Paicode or type /help. Shift+Enter for a new line.", id="prompt")
        yield StatsBar()

    def on_mount(self) -> None:
        self.chat = self.query_one(ChatPane)
        self.diff = self.query_one(DiffPane)
        self.explorer = self.query_one(ExplorerPane)
        self.prompt = self.query_one("#prompt", PromptInput)
        self.stats_bar = self.query_one(StatsBar)
        self.suggestions_bar = self.query_one(SuggestionBar)
        self._reload_context()
        self._refresh_topbar()
        self._refresh_stats()
        if self.session.transcript:
            self.chat.restore(self.session.transcript)
            self.chat.add_system(
                f"Resumed session {self.session.record.id} at {self.session.record.workspace}"
            )
        else:
            self.chat.add_system(
                f"Paicode {__version__}. Type a request or /help. "
                "Workspace writes are limited to the project root. "
                "Read-only host exploration is available with a reason. "
                "Esc x3 stops a running task. Type while working to queue the next prompt."
            )
            provider = self.store.active()
            if provider:
                self.chat.add_system(
                    f"Provider: {provider.name} | Model: {provider.model or 'unset'} | "
                    f"Keys: {len(provider.api_keys)}"
                )
            else:
                self.chat.add_system("No provider configured. Use /connect deepseek or /connect opencode.")
            self.chat.reset_transcript()

        for entry in self.session.diffs:
            self.diff.add_diff(
                str(entry.get("path", "")),
                str(entry.get("diff", "")),
                display_time(str(entry.get("created_at", ""))),
            )
        if self.session.diffs:
            self.diff.add_note(
                f"Restored {len(self.session.diffs)} AI diff(s) from session {self.session.record.id}."
            )
        self.prompt.focus()
        self._save_session()

    def _reload_context(self) -> None:
        self.rules = load_rules(self.root)
        self.skills = discover_skills(self.root)

    def _refresh_topbar(self) -> None:
        provider = self.store.active()
        provider_name = provider.name if provider else "no provider"
        model = provider.model if provider and provider.model else "no model"
        self.query_one("#topbar", Static).update(
            f" Paicode {__version__}  |  {self.session.record.id}  |  "
            f"{provider_name} / {model}  |  {self.root}"
        )

    def _refresh_stats(self) -> None:
        provider = self.store.active()
        provider_name = provider.name if provider else ""
        model = provider.model if provider else ""
        self.stats_bar.update_stats(self.stats, provider_name, model, self.busy)

    def on_prompt_input_content_changed(self, event: PromptInput.ContentChanged) -> None:
        self._refresh_suggestions(event.value)

    def _refresh_suggestions(self, text: str) -> None:
        if not text.startswith("/") or "\n" in text or " " in text:
            self._hide_suggestions()
            return
        matches = filter_commands(text[1:])
        if not matches:
            self._hide_suggestions()
            return
        self._suggestions = matches
        self._suggestion_index = 0
        self.suggestions_bar.show(matches, 0)
        self.prompt.suggestions_visible = True

    def _hide_suggestions(self) -> None:
        self._suggestions = []
        self._suggestion_index = 0
        if self.suggestions_bar is not None:
            self.suggestions_bar.hide()
        if self.prompt is not None:
            self.prompt.suggestions_visible = False

    def _accept_suggestion(self) -> None:
        if not self._suggestions:
            return
        spec = self._suggestions[self._suggestion_index]
        self._hide_suggestions()
        self.prompt.apply_completion(f"/{spec.name} ")

    def on_prompt_input_suggestion_navigate(self, event: PromptInput.SuggestionNavigate) -> None:
        if not self._suggestions:
            return
        self._suggestion_index = (self._suggestion_index + event.delta) % len(self._suggestions)
        self.suggestions_bar.show(self._suggestions, self._suggestion_index)

    def on_prompt_input_suggestion_accept(self, event: PromptInput.SuggestionAccept) -> None:
        self._accept_suggestion()

    def on_prompt_input_suggestion_dismiss(self, event: PromptInput.SuggestionDismiss) -> None:
        self._hide_suggestions()

    def on_prompt_input_submitted(self, event: PromptInput.Submitted) -> None:
        display = event.display.strip()
        expanded = event.expanded
        if not display:
            return
        if self._suggestions:
            if display == "/":
                self.prompt.apply_completion("/")
                self._refresh_suggestions("/")
                return
            if not any(display == f"/{spec.name}" for spec in self._suggestions):
                self._accept_suggestion()
                return
        self._hide_suggestions()
        if self._handle_slash(display):
            return
        self._start_prompt(expanded, event.images, display)

    def on_key(self, event: events.Key) -> None:
        if event.key != "escape" or not self.busy:
            return
        if isinstance(self.screen, ModalScreen):
            return
        now = time.monotonic()
        if now - self._last_escape > 1.2:
            self._escape_count = 0
        self._last_escape = now
        self._escape_count += 1
        remaining = 3 - self._escape_count
        if remaining > 0:
            self.chat.set_work_message(f"press Esc {remaining} more to stop")
        else:
            self._escape_count = 0
            self._request_stop()
        event.prevent_default()
        event.stop()

    def _request_stop(self) -> None:
        if self._active_runner is None:
            return
        self._active_runner.request_stop()
        self.chat.set_stopping()
        self.chat.add_system("Stop requested. Paicode will stop after the current step.")

    def _save_session(self, messages=None) -> None:
        try:
            self.session.record.workspace = str(self.root)
            self.session.record.last_opened_at = now_iso()
            if self.chat is not None:
                self.session.transcript = list(self.chat.transcript)
            self.session.stats = self.stats.to_dict()
            if messages is not None:
                self.session.messages = messages
            self.session_store.save(self.session)
        except Exception:
            pass

    def _switch_session(self, session_id: str) -> bool:
        if self.busy:
            self.chat.add_system("Stop the current task before switching sessions.")
            return False
        record = self.session_store.find(session_id)
        if record is None:
            self.chat.add_system(f"Session '{session_id}' was not found.")
            return False
        if record.id == self.session.record.id:
            self.chat.add_system(format_session_detail(record))
            return True
        workspace = Path(record.workspace)
        if not workspace.is_dir():
            self.chat.add_system(f"Session workspace is missing: {record.workspace}")
            return False
        self._save_session()
        data = self.session_store.get(record.id)
        if data is None:
            self.chat.add_system(f"Session '{record.id}' could not be loaded.")
            return False

        self.session = data
        self.root = workspace
        self.stats = UsageStats.from_dict(data.stats) if data.stats else UsageStats()
        self.chat.clear()
        self.diff.clear()
        self.chat.restore(data.transcript)
        for entry in data.diffs:
            self.diff.add_diff(
                str(entry.get("path", "")),
                str(entry.get("diff", "")),
                display_time(str(entry.get("created_at", ""))),
            )
        if data.diffs:
            self.diff.add_note(
                f"Restored {len(data.diffs)} AI diff(s) from session {data.record.id}."
            )
        self.explorer.root = self.root
        self.explorer.refresh_tree()
        self._reload_context()
        self._prompt_queue.clear()
        self.chat.set_queue(0)
        self.chat.end_work()
        self._hide_suggestions()
        self.prompt.text = ""
        self.prompt.placeholder = PromptInput.DEFAULT_PLACEHOLDER
        self._refresh_topbar()
        self._refresh_stats()
        self.chat.add_system(
            f"Switched to session {data.record.id} at {data.record.workspace}"
        )
        self.prompt.focus()
        self._save_session()
        return True

    def _start_prompt(self, text: str, images=None, display: str | None = None) -> None:
        images = images or []
        display = display or text
        if self.busy:
            self._prompt_queue.append((text, images, display))
            self.chat.set_queue(len(self._prompt_queue))
            self.chat.add_system(
                f"Queued prompt {len(self._prompt_queue)}. It will run after the current task."
            )
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
        if not any(entry.get("kind") == "user" for entry in self.chat.transcript):
            first_line = display.strip().splitlines()[0][:60] if display.strip() else ""
            if first_line:
                self.session.record.title = first_line
        self.chat.add_user(display)
        self.chat.begin_assistant()
        self.chat.begin_work()
        self.chat.set_queue(len(self._prompt_queue))
        self.chat.set_work_message("thinking")
        self.diff.add_note(f"Task: {display[:220]}")
        self.prompt.placeholder = PromptInput.BUSY_PLACEHOLDER
        self._refresh_stats()
        try:
            runner = AgentRunner(
                self.root,
                provider,
                self.stats,
                self.rules,
                self.skills,
                emit=lambda event: self.call_from_thread(self._handle_event, event),
                history=self.session.messages,
            )
        except Exception as exc:
            self.chat.add_system(f"Could not start the task: {exc}")
            self._finish_work()
            return
        self._active_runner = runner
        self._run_agent(runner, text, images)

    def _start_next_queued(self) -> None:
        if self.busy or not self._prompt_queue:
            return
        text, images, display = self._prompt_queue.pop(0)
        self.chat.set_queue(len(self._prompt_queue))
        self._start_prompt(text, images, display)

    def _finish_work(self) -> None:
        self.busy = False
        self._active_runner = None
        self._tool_line = None
        self.chat.end_work()
        self.chat.set_queue(len(self._prompt_queue))
        self.prompt.placeholder = PromptInput.DEFAULT_PLACEHOLDER
        self._refresh_stats()
        self.prompt.focus()
        if self._prompt_queue:
            self.set_timer(0.2, self._start_next_queued)

    @work(thread=True, exclusive=False)
    def _run_agent(self, runner, text: str, images) -> None:
        try:
            runner.run(text, images=images)
        except Exception as exc:
            self.call_from_thread(self._handle_event, ErrorEvent(f"{type(exc).__name__}: {exc}"))

    def _handle_event(self, event) -> None:
        if isinstance(event, TextDelta):
            self.chat.append_assistant(event.text)
        elif isinstance(event, ReasoningDelta):
            return
        elif isinstance(event, ToolStarted):
            self.chat.set_work_message(f"{event.name} ...")
            self._tool_line = self.chat.add_tool(
                event.name, "running", self._summarize_arguments(event.arguments)
            )
        elif isinstance(event, ToolFinished):
            status = "ok" if event.ok else "failed"
            self.chat.set_work_message("thinking")
            if self._tool_line is not None:
                self.chat.update_tool(self._tool_line, event.name, status, event.output)
                self._tool_line = None
            else:
                self.chat.add_tool(event.name, status, event.output)
            if event.diff:
                path = event.changed[0] if event.changed else event.name
                stamp = now_iso()
                self.diff.add_diff(path, event.diff, display_time(stamp))
                self.session.diffs.append(
                    {"path": path, "diff": event.diff, "created_at": stamp}
                )
                self._save_session()
            if event.changed:
                self.explorer.refresh_tree()
            self._refresh_stats()
        elif isinstance(event, UsageUpdated):
            self.chat.end_assistant()
            self.chat.set_work_message("thinking")
            self._refresh_stats()
        elif isinstance(event, Finished):
            self.chat.end_assistant()
            self.chat.add_system(f"Finished in {event.steps} step(s): {event.message[:400]}")
            messages = getattr(self._active_runner, "messages", None)
            self._save_session(messages=messages[1:] if messages else None)
            self._finish_work()
        elif isinstance(event, ErrorEvent):
            self.chat.end_assistant()
            self.chat.add_system(f"Error: {event.message}")
            messages = getattr(self._active_runner, "messages", None)
            self._save_session(messages=messages[1:] if messages else None)
            self._finish_work()

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

    def on_unmount(self) -> None:
        messages = getattr(self._active_runner, "messages", None)
        self._save_session(messages=messages[1:] if messages else None)
