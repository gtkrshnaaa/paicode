from textual import work

from ..core.atomic import atomic_write_text
from ..providers.client import ProviderClient
from ..providers.presets import get_preset
from ..rules.loader import load_rules, render_rules, rule_summary
from ..rules.skills import discover_skills, find_skill, load_skill_text, render_catalog
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
