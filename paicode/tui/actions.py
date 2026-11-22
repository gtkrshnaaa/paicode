from textual import work

from ..agents import DiscussionRunner, MultiAgentRunner, SmartRunner
from ..agents.store import AgentStore
from ..agent.loop import context_budget
from ..core.atomic import atomic_write_text
from ..providers.client import ProviderClient
from ..providers.presets import get_preset
from ..mcp import get_mcp_manager
from ..settings import load_settings
from ..rules.loader import load_rules, render_rules, rule_summary
from ..rules.skills import discover_skills, find_skill, load_skill_text, render_catalog
from ..sessions import (
    format_session_detail,
    format_session_detail_markdown,
    format_sessions,
    format_sessions_markdown,
)
from .commands import HELP_TEXT, parse_slash
from .modals.models import ModelModal
from .modals.provider import ProviderModal
from .modals.value import ValueModal

PAICODE_TEMPLATE = """# PAICODE.md

## Project
Describe the project, its stack, and its conventions.

## Commands
- Test:
- Lint:
- Build:

## Constraints
- Keep changes surgical.
- Do not touch generated or vendor directories.
"""


class SlashActions:
    def _handle_slash(self, text: str) -> bool:
        command = parse_slash(text)
        if command is None:
            return False
        handler = getattr(self, f"_cmd_{command.name}", None)
        if handler is None:
            self.chat.add_system(f"Unknown command /{command.name}. Type /help for the list.")
        else:
            handler(command.args)
        return True

    def _cmd_help(self, args: str) -> None:
        self.chat.add_system(HELP_TEXT)

    def _cmd_connect(self, args: str) -> None:
        parts = args.split(maxsplit=1)
        name = parts[0] if parts else ""
        url = parts[1] if len(parts) > 1 else ""
        self.push_screen(ProviderModal(name, url), self._on_provider_saved)

    def _on_provider_saved(self, result: dict | None) -> None:
        if not result:
            return
        name = result["name"]
        base_url = result["base_url"]
        api_key = result.get("api_key") or None
        existing = self.store.get(name)
        preset = get_preset(name)
        model = None if existing and existing.model else (preset.model if preset else None)
        models_url = preset.models_url if preset else None
        try:
            provider = self.store.upsert(
                name,
                base_url,
                api_key=api_key,
                model=model,
                models_url=models_url,
            )
            self.store.set_active(provider.name)
        except Exception as exc:
            self.chat.add_system(f"Could not save provider: {exc}")
            return
        self.chat.add_system(
            f"Provider '{provider.name}' saved at {provider.base_url}. "
            f"Model: {provider.model or 'unset'}. Keys: {len(provider.api_keys)}."
        )
        self._refresh_topbar()
        self._refresh_stats()
        self._fetch_models(open_modal=False)

    def _cmd_key(self, args: str) -> None:
        provider = self.store.active()
        if provider is None:
            self.chat.add_system("No active provider. Use /connect first.")
            return
        if args:
            self._on_key_saved(args)
        else:
            self.push_screen(
                ValueModal("Add API key", "API key", placeholder="sk-...", password=True),
                self._on_key_saved,
            )

    def _on_key_saved(self, value: str | None) -> None:
        if not value:
            return
        provider = self.store.active()
        if provider is None:
            self.chat.add_system("No active provider. Use /connect first.")
            return
        try:
            updated = self.store.add_key(provider.name, value)
        except Exception as exc:
            self.chat.add_system(f"Could not add key: {exc}")
            return
        self.chat.add_system(f"Key added. Provider '{updated.name}' now has {len(updated.api_keys)} key(s).")
        self._refresh_topbar()

    def _cmd_baseurl(self, args: str) -> None:
        provider = self.store.active()
        if provider is None:
            self.chat.add_system("No active provider. Use /connect first.")
            return
        if args:
            self._on_baseurl_saved(args)
        else:
            self.push_screen(
                ValueModal("Set base URL", "Base URL", value=provider.base_url),
                self._on_baseurl_saved,
            )

    def _on_baseurl_saved(self, value: str | None) -> None:
        if not value:
            return
        provider = self.store.active()
        if provider is None:
            return
        try:
            updated = self.store.upsert(provider.name, value)
        except Exception as exc:
            self.chat.add_system(f"Could not update base URL: {exc}")
            return
        self.chat.add_system(f"Base URL updated to {updated.base_url}.")
        self._refresh_topbar()

    def _cmd_provider(self, args: str) -> None:
        if args:
            try:
                provider = self.store.set_active(args.strip())
            except Exception as exc:
                self.chat.add_system(f"Could not switch provider: {exc}")
                return
            self.chat.add_system(f"Active provider: {provider.name} ({provider.base_url}).")
            self._refresh_topbar()
            self._refresh_stats()
            self._fetch_models(open_modal=False)
            return
        providers = self.store.list()
        if not providers:
            self.chat.add_system("No providers configured. Use /connect.")
            return
        active = self.store.load().get("active")
        lines = ["Configured providers:"]
        for provider in providers:
            marker = "*" if provider.name == active else " "
            lines.append(
                f"{marker} {provider.name}: {provider.base_url} model={provider.model or 'unset'} "
                f"keys={len(provider.api_keys)}"
            )
        self.chat.add_system("\n".join(lines))

    def _cmd_models(self, args: str) -> None:
        self._fetch_models(open_modal=False)

    def _cmd_model(self, args: str) -> None:
        provider = self.store.active()
        if provider is None:
            self.chat.add_system("No active provider. Use /connect first.")
            return
        if args:
            try:
                updated = self.store.set_model(provider.name, args.strip())
            except Exception as exc:
                self.chat.add_system(f"Could not set model: {exc}")
                return
            self.chat.add_system(f"Model set to {updated.model}.")
            self._refresh_topbar()
            self._refresh_stats()
            return
        if provider.models:
            self.push_screen(ModelModal(provider.models, provider.model), self._on_model_selected)
        else:
            self._fetch_models(open_modal=True)

    def _on_model_selected(self, model: str | None) -> None:
        if not model:
            return
        provider = self.store.active()
        if provider is None:
            return
        updated = self.store.set_model(provider.name, model)
        self.chat.add_system(f"Model set to {updated.model}.")
        self._refresh_topbar()
        self._refresh_stats()

    def _fetch_models(self, open_modal: bool = False) -> None:
        provider = self.store.active()
        if provider is None:
            self.chat.add_system("No active provider. Use /connect first.")
            return
        self.chat.add_system(f"Fetching models from {provider.base_url}...")
        self._run_model_fetch(provider.name, open_modal)

    @work(thread=True, exclusive=False)
    def _run_model_fetch(self, provider_name: str, open_modal: bool) -> None:
        provider = self.store.get(provider_name)
        if provider is None:
            self.call_from_thread(self.chat.add_system, "Provider disappeared before model discovery.")
            return
        try:
            models = ProviderClient(provider).list_models()
        except Exception as exc:
            self.call_from_thread(self.chat.add_system, f"Model discovery failed: {exc}")
            return
        self.call_from_thread(self._models_ready, provider_name, models, open_modal)

    def _models_ready(self, provider_name: str, models: list[str], open_modal: bool) -> None:
        if not models:
            self.chat.add_system("The provider returned no models.")
            return
        self.store.set_models(provider_name, models)
        self.chat.add_system("Models: " + ", ".join(models))
        if open_modal:
            provider = self.store.get(provider_name)
            self.push_screen(
                ModelModal(models, provider.model if provider else ""),
                self._on_model_selected,
            )

    def _cmd_rules(self, args: str) -> None:
        self._reload_context()
        self.chat.add_system(rule_summary(self.rules))
        if self.rules:
            self.chat.add_system(render_rules(self.rules)[:6_000])

    def _cmd_skills(self, args: str) -> None:
        self._reload_context()
        self.chat.add_system(render_catalog(self.skills))

    def _cmd_skill(self, args: str) -> None:
        if not args:
            self.chat.add_system("Usage: /skill <name>")
            return
        self._reload_context()
        skill = find_skill(self.skills, args)
        if skill is None:
            self.chat.add_system(f"Skill '{args}' was not found.")
            return
        try:
            self.chat.add_system(load_skill_text(skill)[:6_000])
        except Exception as exc:
            self.chat.add_system(f"Could not load skill: {exc}")

    def _cmd_stats(self, args: str) -> None:
        self.chat.add_system(self.stats.detailed())

    def _cmd_sessions(self, args: str) -> None:
        records = self.session_store.list()
        self.chat.add_markdown_system(
            format_sessions_markdown(records, self.session.record.id),
            plain_text=format_sessions(records, self.session.record.id),
        )

    def _cmd_session(self, args: str) -> None:
        value = args.strip()
        if not value:
            self.chat.add_markdown_system(
                format_session_detail_markdown(self.session.record),
                plain_text=format_session_detail(self.session.record),
            )
            return
        if value.lower() == "new":
            if self.busy:
                self.chat.add_system("Stop the current task before starting a new session.")
                return
            self._save_session()
            created = self.session_store.create(self.root)
            self._switch_session(created.record.id)
            return
        self._switch_session(value)

    def _cmd_agents(self, args: str) -> None:
        runner = self._active_runner
        if isinstance(runner, (MultiAgentRunner, SmartRunner)):
            rows = runner.agent_status()
            if not rows:
                self.chat.add_system("The council has not started yet.")
                return
            lines = ["## Agents", ""]
            for row in rows:
                lines.append(
                    f"- Agent {row['agent_id']} {row['role']}: {row['phase']} / {row['status']} "
                    f"({row.get('total_tokens', 0)} tokens)"
                )
            self.chat.add_markdown_system("\n".join(lines))
            return
        self.chat.add_system("This run is using a single agent. Start a new prompt to use the council.")

    def _cmd_contract(self, args: str) -> None:
        runner = self._active_runner
        contract = runner.contract if isinstance(runner, (MultiAgentRunner, SmartRunner)) else None
        if contract is None:
            contract = AgentStore().latest_contract(self.session.record.id)
        if contract is None:
            self.chat.add_system("No frozen contract in this session yet.")
            return
        self.chat.add_markdown_system(contract.markdown(), plain_text=contract.feature)

    def _cmd_bugs(self, args: str) -> None:
        runner = self._active_runner
        if isinstance(runner, (MultiAgentRunner, SmartRunner)):
            rows = runner.latest_findings()
        else:
            rows = AgentStore().latest_findings(self.session.record.id)
        if not rows:
            self.chat.add_system("No validation findings.")
            return
        lines = ["## Validation Findings", ""]
        for row in rows[:25]:
            lines.append(
                f"- Agent {row['owner']} [{row['severity']}] {row['title']} "
                f"`{row['file'] or 'unknown'}`: {row['message'] or row['actual']}"
            )
        self.chat.add_markdown_system("\n".join(lines))

    def _cmd_disscus(self, args: str) -> None:
        prompt = args.strip()
        if not prompt:
            self.chat.add_system("Usage: /disscus <prompt>. Discussion mode is read-only.")
            return
        if self.busy:
            self.chat.add_system("Stop the current task before starting a discussion.")
            return
        self._start_prompt(prompt, [], prompt, mode="discussion")

    def _cmd_discuss(self, args: str) -> None:
        self._cmd_disscus(args)

    def _cmd_stop(self, args: str) -> None:
        if self._active_runner is None:
            self.chat.add_system("No task is running.")
            return
        self._request_stop()

    def _cmd_queue(self, args: str) -> None:
        if args.strip().lower() == "clear":
            count = len(self._prompt_queue)
            self._prompt_queue.clear()
            self.chat.set_queue(0)
            self.chat.add_system(f"Cleared {count} queued prompt(s).")
            return
        if not self._prompt_queue:
            self.chat.add_system("No prompts queued.")
            return
        lines = ["Queued prompts:"]
        for index, (_, images, display) in enumerate(self._prompt_queue, start=1):
            suffix = f" ({len(images)} image(s))" if images else ""
            lines.append(f"{index}. {display[:120]}{suffix}")
        self.chat.add_system("\n".join(lines))

    def _cmd_limits(self, args: str) -> None:
        self.chat.add_system(
            "Steps: unlimited by default. Use --max-steps in headless mode to set a ceiling.\n"
            f"Context budget: {context_budget():,} characters. "
            "Override with PAICODE_CONTEXT_CHARS.\n"
            "Repeated identical tool calls are stopped after five consecutive attempts.\n"
            "Filesystem: writes are confined to the workspace. Read-only host exploration "
            "is available through the explore tool with a required reason."
        )

    def _cmd_mcp(self, args: str) -> None:
        parts = args.split()
        action = parts[0].lower() if parts else "status"
        server = parts[1] if len(parts) > 1 else ""
        manager = get_mcp_manager(self.root, load_settings(self.root))
        if action == "tools":
            schemas = manager.schemas()
            if not schemas:
                self.chat.add_system("No MCP tools are available.")
                return
            lines = ["## MCP Tools", ""]
            for schema in schemas:
                function = schema.get("function", {})
                lines.append(f"- `{function.get('name')}`: {function.get('description', '')}")
            self.chat.add_markdown_system("\n".join(lines))
            return
        if action in {"resources", "prompts"}:
            if not server:
                self.chat.add_system(f"Usage: /mcp {action} <server>")
                return
            try:
                items = manager.resources(server) if action == "resources" else manager.prompts(server)
            except Exception as exc:
                self.chat.add_system(f"MCP {action} failed: {exc}")
                return
            self.chat.add_system("\n".join(str(item.get("uri") or item.get("name") or item) for item in items) or "None.")
            return
        rows = manager.status()
        if not rows:
            self.chat.add_system("No MCP servers configured. Add mcp.servers in .paicode/settings.json.")
            return
        lines = ["## MCP Servers", ""]
        for row in rows:
            state = "connected" if row.connected else "failed"
            detail = f"{row.tools} tools" if row.connected else row.error
            lines.append(f"- **{row.name}** ({row.transport}): {state}, {detail}")
        self.chat.add_markdown_system("\n".join(lines))

    def _cmd_config(self, args: str) -> None:
        self.chat.add_system(self.store.redacted())

    def _cmd_init(self, args: str) -> None:
        path = self.root / "PAICODE.md"
        if path.exists():
            self.chat.add_system(f"{path} already exists.")
            return
        atomic_write_text(path, PAICODE_TEMPLATE, mode=0o644)
        self._reload_context()
        self.chat.add_system(f"Created {path}.")

    def _cmd_refresh(self, args: str) -> None:
        self._reload_context()
        self.query_one("#explorer").refresh_tree()
        self.chat.add_system("Rules, skills, and the file tree were reloaded.")
        self.prompt.focus()

    def _cmd_clear(self, args: str) -> None:
        if self.busy:
            self.chat.add_system("Wait for the current task to finish.")
            return
        self.chat.clear()
        self.diff.clear()
        self.chat.add_system("Chat and diff panes cleared.")

    def _cmd_new(self, args: str) -> None:
        if self.busy:
            self.chat.add_system("Wait for the current task to finish.")
            return
        self.stats.reset()
        self.chat.clear()
        self.diff.clear()
        self.chat.add_system("New session started.")
        self._refresh_stats()

    def _cmd_exit(self, args: str) -> None:
        self.exit()
