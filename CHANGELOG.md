# Changelog

## 0.13.1 - 2026-11-22

### Fixed

- Clicking a markdown table cell that was replaced during a chat refresh no longer crashes the TUI. Textual 8.2.8 reads a detached cell parent while starting text selection; the default Paicode screen now guards that specific stale-widget error, logs it, and keeps the session alive.

## 0.13.0 - 2026-11-22

### Changed

- Collapsed agents 2 to 21 into 20 identical universal Builders with no specialties.
- Lead, Builder, and Validator are now the only role types.
- Builder proposals, contract reviews, and build prompts use universal language.
- The lead must assign one work unit per builder. Duplicate builder ownership is rejected.
- Work units carry dependency, integration-order, and integration-note metadata.
- The validator audits changed files against the ownership map and shared files.
- The Agent Rail shows LEAD, BUILDER, and VALIDATOR labels only.

### Added

- Ownership audit findings for unowned changed files.
- Tests for universal builder roles, duplicate owner rejection, paste metadata, and validator audit.

## 0.12.1 - 2026-11-22

### Added

- `pai --session-lists` root flag as an equivalent to `pai session-lists`.
- `pai --sessions` alias.
- Flag-form tests for complete session output and the empty-database message.

## 0.12.0 - 2026-11-22

### Added

- Agent 1 triage before every prompt. `SmartRunner` classifies intent, expected file count, and routes to read-only discussion, one-file single-agent work, or the 22-agent team.
- Multi-file, scaffolding, feature, migration, and unknown-size write work is forced to the team.
- The Agent Rail on the right shows all 22 agents with status, nested turn count, timestamps, and read, create, edit, delete, list, command, explore, skill, council, and validation actions.
- Council, builder, validator, triage, and final report produce `AgentAction` events for the rail.
- TUI layout includes a dedicated 34-column Agent Rail.

### Changed

- TUI and headless default now use `SmartRunner`, not unconditional multi-agent.
- `/agents` and the Agent Rail stay available for both single and team routes.
- Chat, diff, and rail share monochrome styling and chronological event delivery.

## 0.11.0 - 2026-11-22

### Added

- `/disscus <prompt>` read-only discussion mode with `/discuss` as an alias.
- Discussion mode blocks file writes, builds, package installs, git mutations, inline code evaluation, in-place edits, and shell redirection.
- Discussion shell runs on a disposable overlay with a host-cache-free cache path.
- Monochrome syntax highlighting for the diff stream and file preview.
- Strong diff header bands, closing rules, and wider spacing between diff blocks.
- `Esc` now stops immediately by aborting active provider streams and killing sandboxed shell process groups.

### Changed

- Provider streams use a watchdog plus worker thread for immediate cancellation.
- The work status and help text describe one-press stop.
- File preview uses the shared language detector and monochrome TextArea theme.

## 0.10.6 - 2026-11-21

### Fixed

- Multi-agent events now pass through one FIFO dispatcher, so tool rows and validator status cannot appear after the final report.
- Assistant cards close before a tool row or system notice is mounted; later assistant text starts a new card below the tools.
- Every assistant card label includes a timestamp.
- Fixed a Markdown mount race that could leave assistant cards visually empty.
- Added tests for event ordering, card ordering, timestamps, and non-empty assistant content.
- Added a visual review of the ordered chat layout.

## 0.10.5 - 2026-11-21

### Fixed

- All active builders are dispatched to the executor before any completion is collected. Builders no longer wait for one another to start.
- The build phase shows the full active builder count from the start, not `0/N`.
- Each builder emits a running status with its owned files.
- Builder diffs are flushed together after the bulk build instead of appearing one by one as builders finish.
- The chat announces that all builders started together and that validation starts only after every builder finishes.
- Added an eight-builder barrier test and a validator-after-all assertion.

## 0.10.4 - 2026-11-21

### Fixed

- Contract-review objections are no longer rendered as empty `object:` chat errors. Objections are normal council input and are resolved by the lead.
- Only failed, blocked, or errored agent states render as chat notices.
- Objection details are stored in the agent status summary for `/agents`.
- The council work status now shows a compact objection count before lead arbitration.
- Added TUI regression tests for objection suppression and failure notices.

## 0.10.3 - 2026-11-21

### Fixed

- The lead now writes a user-facing final report after every multi-agent run, including validation success, failure, strike limit, partial build, and stopped runs.
- The report covers summary, delivered work, files, validation, defects, and next steps.
- Report generation uses the mandatory PAICODE.md rule envelope.
- A model report failure falls back to a deterministic report.
- Stopped runs emit the deterministic report without another model call.
- Added fake-provider and provider-down report tests.

## 0.10.2 - 2026-11-21

### Changed

- Every AI diff now has a labelled separator with an index, path, additions, removals, and timestamp.
- Diff lines use distinct monochrome treatments for additions, removals, hunks, and context.
- Every chat turn after the first starts with a labelled turn divider and time.
- User and assistant cards now use rounded borders, cleaner role labels, and consistent spacing.
- Tool rows, system notices, panel borders, and the status bar have tighter visual hierarchy.
- Added separator tests and a real Textual screenshot review.

## 0.10.1 - 2026-11-21

### Fixed

- Every model request now carries the full global and project `PAICODE.md` rules, including council proposals, lead synthesis, contract review, arbitration, builder turns, validator turns, and single-agent turns.
- Removed the 100,000 character rule truncation and raised the per-file rule loading limit to 1,000,000 characters.
- Added a request audit test that verifies every fake-provider request contains a unique global rule marker.
- Documented the performance model and live measurements.

## 0.10.0 - 2026-11-21

### Added

- 22-agent council enabled by default for TUI and headless runs.
- Agent 1 lead, agents 2 to 21 builders, and agent 22 independent validator.
- Parallel council proposals, lead contract synthesis, and 22-agent contract review.
- Typed build contracts with work units, file ownership, interfaces, API, database, UI, tests, commands, and non-goals.
- Parallel builder execution with per-agent write allowlists.
- Independent validation with structured findings, strict owner accountability, strikes, and repair rounds.
- SQLite audit tables for agent runs, messages, tasks, contracts, ownership, validation runs, findings, strikes, and events.
- `/agents`, `/contract`, and `/bugs` commands.
- Agent phase and status reporting in the TUI and headless output.
- `make matrix` coverage and a 22-agent fake-provider end-to-end test.
- Live DeepSeek 22-agent smoke test: 66 requests, 2 active builders, 20 idle, validator passed.

### Changed

- `pai` and `pai run` default to the multi-agent council.
- Provider clients now support a shared concurrency gate and backoff for rate limits and transient failures.
- Usage statistics are thread-safe and shared across agents.
- File tools support per-agent write allowlists.
- Session transcripts and diffs still persist; agent audit data has its own tables.

### Compatibility

- `--single-agent` restores the original single-agent path for small tasks.

## 0.9.0 - 2026-11-21

### Added

- Real bash execution with pipes, redirection, multi-command scripts, package managers, compilers, test runners, formatters, and git.
- Optional bubblewrap sandbox that keeps workspace writes isolated, hides the real home directory, and isolates package caches.
- Process-group cancellation on timeout or user stop, with bounded output and truncation markers.
- Coding capability matrix covering Python, Node, C, C++, Java, shell, Git, SQLite, JSON, HTTP and static web tasks, refactors, debugging, and the full agent loop.
- Optional Go, Rust, TypeScript, and Docker matrix cases with clean skips.
- `make matrix` target and `docs/capability-matrix.md`.
- `pai doctor` reports the shell isolation mode.

### Changed

- `bash` accepts an optional project-relative `cwd` and a timeout up to 600 seconds.
- Python bytecode caches are cleared after edits so same-size fixes cannot be masked by stale `.pyc` files.
- Shell environment scrubbing now also removes SSH agent sockets and common cloud provider credentials.

### Removed

- The read-only command allowlist and the no-shell command policy.

## 0.8.3 - 2026-11-21

### Fixed

- `Shift+Enter` inserts a newline for Kitty keyboard protocol and xterm modifyOtherKeys sequences. `Ctrl+J` is available as a fallback on legacy terminals.
- `Ctrl+Shift+C` copies the prompt selection or the full prompt text.
- `Ctrl+Shift+V` pastes clipboard text without attaching images. `Ctrl+V` keeps the image-first paste behavior.
- Copy uses `wl-copy` on Wayland and `xclip` on X11 when available; text paste uses `wl-paste` or `xclip`. Both also use the terminal clipboard as a fallback.
- Clipboard text reads request text MIME types, so an image-only clipboard is ignored instead of pasted as binary data.

## 0.8.2 - 2026-11-21

### Changed

- Chat pane is wider, with inset content padding and dedicated user and assistant cards.
- User messages carry a `You` label; assistant messages carry a `Pai` label and a card container.
- Assistant Markdown renders headings, lists, blockquotes, inline code, fenced code blocks, and tables with monochrome styling.
- Tool activity renders as compact single-line rows with ellipsized detail.
- `/sessions` and current-session details render as Markdown blocks instead of a wide fixed table.

## 0.8.1 - 2026-11-21

### Fixed

- Installer and `pai doctor` now report the SQLite database path instead of the retired JSON configuration path.

## 0.8.0 - 2026-11-21

### Added

- One SQLite database for sessions, transcripts, diffs, model messages, stats, providers, keys, models, and provider presets.
- `pai --reset-db` backs up the database, drops every table, migrates fresh, and seeds provider base URLs.
- Provider preset seeder ordered with DeepSeek, OpenAI, OpenRouter, Google, and additional OpenAI-compatible providers.
- Automatic migration of legacy `~/.config/paicode/config.json` provider configuration and JSON session files into SQLite.

### Changed

- Removed `.pai_brain` and `.pai_history` writes from the agent loop.
- Provider configuration and session state now live in `~/.local/state/paicode/paicode.db`.

## 0.7.0 - 2026-11-21

### Added

- Persistent sessions stored under `~/.local/state/paicode/sessions`.
- `pai session-lists` shows every session with ID, workspace, creation time, last-opened time, and title.
- `pai --session <id>` and `pai --s-xxxx` open a session and its workspace from anywhere.
- TUI `/sessions`, `/session <id>`, and `/session new` commands.
- Per-session chat transcript, AI diff history, model messages, and usage stats.
- Reopening a session restores its chat and diff history. A normal `pai` launch creates a new session.

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
- DeepSeek, OpenAI, OpenRouter, Google OpenAI compatibility, and custom provider presets.
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
