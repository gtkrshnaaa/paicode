# Changelog

## 0.5.3 - 2026-11-21

### Added

- Filtered slash command palette above the prompt. Up and Down navigate, Tab completes, Escape dismisses, and Enter accepts partial commands or runs exact ones.
- Command metadata is now a single source used by both `/help` and suggestions.

## 0.5.2 - 2026-11-21

### Added

- Remote installer through `curl | bash`, with a GitHub source archive download and the same isolated environment as the local installer.
- `--ref`, `--remote`, `PAICODE_REF`, and `PAICODE_SOURCE_URL` installer options.
- Prominent quick install section in the README with a two-step inspection alternative.

### Changed

- `install.sh` now detects local checkout mode and piped remote mode automatically.
- Installer help documents both local and remote workflows.

## 0.5.1 - 2026-11-21

### Changed

- Removed the default 12 model-turn cap. Runs are unlimited unless `--max-steps` is set to a positive value.
- Raised the context compaction budget from 180,000 to 2,500,000 characters. Override with `PAICODE_CONTEXT_CHARS`.
- Raised tool limits: 20,000 lines per read request, 20 MB files, 5,000 list and search results, 200,000 characters of shell output.
- Added repeated-action detection. Five consecutive identical tool calls stop the loop with a clear error instead of an arbitrary step cap.

### Added

- `/limits` slash command for the active step and context policy.

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
