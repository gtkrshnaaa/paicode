# Changelog

## 0.5.0 - 2026-11-21

### Added

- OpenAI-compatible provider layer with streaming chat completions, tool calls, usage reporting, and multi-key rotation.
- DeepSeek, OpenCode Console, OpenAI, OpenRouter, Google OpenAI compatibility, and custom provider presets.
- Textual multi-pane interface with a file explorer, AI diff stream, chat pane, and live session statistics.
- In-TUI slash commands for provider setup, keys, base URLs, provider and model switching, rules, skills, statistics, configuration, and session control.
- `PAICODE.md` global and project rules with `AGENTS.md` compatibility fallback.
- Global and project skill discovery with on-demand loading through the `skill` tool.
- Typed tool registry with path confinement, atomic writes, surgical edits, syntax checks, and a shell allowlist.
- `install.sh` with an isolated runtime, a `~/.local/bin/pai` launcher, development mode, and uninstall mode.
- Opt-in live DeepSeek integration test.
- Agenticway Paicode edition with English and bilingual rules, skills, and installers.

### Changed

- Replaced the Gemini-only runtime with a provider-agnostic agent loop.
- Reworked context handling into deterministic truncation instead of extra model calls.
- Reworked configuration storage into an atomic, locked JSON store with corruption backups.

### Removed

- `google-generativeai`, `python-dotenv`, and the legacy text-command execution loop.

## 0.4.2 - 2026-11-21

- Release marker before the provider and TUI overhaul.
