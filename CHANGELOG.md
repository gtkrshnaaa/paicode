# Changelog

## 0.6.1 - 2026-11-21

### Changed

- Image paste now uses `Ctrl+V` instead of `Ctrl+G`.
- Clipboard images use `wl-paste` from wl-clipboard on Wayland, with `xclip` as the X11 fallback.
- When the clipboard contains text, `Ctrl+V` falls back to inserting the clipboard text or a multiline paste marker.

## 0.6.0 - 2026-11-21

### Added

- Multiline paste markers: `[pasted N lines]` is highlighted in the prompt and expands to the full text when submitted.
- Image attachments through a pasted image path or `Ctrl+G`. Images are highlighted as `[image-1]`, `[image-2]`, and sent as OpenAI-compatible multimodal content.
- `Ctrl+E` toggles a larger upward-expanding prompt composer.
- Chat-bottom work status with an animated loading bar, current action, elapsed time, Esc hint, and queue count.
- Triple-Esc cooperative stop for a running task.
- Prompt queue while Paicode is working. Queued prompts start automatically after the current task.
- `/stop` and `/queue [clear]` commands.

### Changed

- The prompt displays attachment markers instead of flooding the input with pasted content.
- Chat history shows compact markers while the model receives the full expanded text and images.

## 0.5.6 - 2026-11-21

### Changed

- Installer output is now a structured monochrome report with mode, platform, Python, install root, launcher, and source information.
- Six-phase progress bar with an animated spinner on TTY, elapsed time per phase, and `[ok]` or `[failed]` status.
- Package manager output is captured in per-step logs. Failures print the last 40 lines and preserve the full log at the install root.
- Completion summary shows version, launcher, config path, next command, and total elapsed time.
- Added `--quiet` to disable the spinner while keeping step lines.

## 0.5.5 - 2026-11-21

### Added

- Read-only `explore` tool for guarded host filesystem inspection outside the workspace. It requires a concrete reason and blocks credentials, private keys, shell history, browser profiles, Paicode configuration, and pseudo-filesystems.
- Read-only host commands in the shell allowlist: uname, df, free, ps, lscpu, lsblk, read-only systemctl, and read-only journalctl.
- System prompt now states the cwd, project root, home, platform, and the OS exploration policy.

### Changed

- Writes, edits, deletes, and moves remain confined to the workspace.

## 0.5.4 - 2026-11-21

### Changed

- Hidden scrollbars across the chat, diff, explorer, prompt, preview, and option lists while preserving wheel and keyboard scrolling.

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
