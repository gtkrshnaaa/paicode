# Internal Architecture

Paicode is split into a provider layer, a typed tool layer, a multi-agent council, a single-agent loop, and a Textual interface. The control plane is deterministic Python. The model decides what to do next, but code decides how tools execute, how paths are validated, how ownership is enforced, and how failures are reported.

## Layers

### Multi-agent layer

`paicode/agents/` contains the 22-agent roster, typed build contract, council, parallel build coordinator, validator, SQLite audit store, and `MultiAgentRunner`. The council runs 22 parallel proposals, lead synthesis, and 22 parallel contract reviews. The lead freezes file ownership and work units. Active builders run concurrently with per-agent write allowlists. Agent 22 runs the validation matrix and produces structured findings. Findings are assigned to owners and repaired until green or the configured round and strike limits. The default path is multi-agent; `--single-agent` keeps the original loop available.

### Provider layer

`paicode/providers/` contains the OpenAI-compatible client, provider presets, and the configuration store.

- `client.py` streams chat completions, assembles tool call deltas, records usage, and rotates API keys on authentication or rate-limit failures. User messages may include text and image parts.
- `store.py` persists providers, base URLs, keys, selected models, and cached model lists in the SQLite `providers`, `provider_keys`, `provider_models`, and `settings` tables.
- `presets.py` defines DeepSeek, OpenCode Console, OpenAI, OpenRouter, Google OpenAI compatibility, and custom providers.

The OpenCode preset uses `https://opencode.ai/inference/openai/v1` for chat and `https://opencode.ai/inference/v1/models` for discovery.

### Tool layer

`paicode/tools/` exposes twelve typed tools to the model through OpenAI function calling:

`read`, `write`, `edit`, `list`, `glob`, `grep`, `bash`, `explore`, `skill`, `mkdir`, `move`, `delete`, and `finish`.

`explore` is the only tool that can read outside the workspace. It resolves the target, applies a sensitive-path denylist, requires a written reason, and returns the absolute path and scope. All write tools continue to use the workspace-confined path resolver.

`registry.py` dispatches calls and converts security errors into tool results. `fs.py` implements atomic writes, surgical replacements, diffs, bytecode invalidation, and in-process syntax checks for Python and JSON. `shell.py` runs real bash commands with bounded output, process-group cancellation, secret scrubbing, and optional bubblewrap isolation. `sandbox.py` builds the bubblewrap command, hides the real home directory, mounts the workspace read-write, isolates package caches, and probes sandbox support. `search.py` provides bounded glob and regex search.

### Agent loop

`paicode/agent/loop.py` owns one turn:

1. Build a system prompt from the base contract, global rules, project rules, and the skill catalog.
2. Stream a completion from the provider.
3. Append the assistant message and any tool calls to the conversation.
4. Execute each tool, emit a result event, and append a tool message.
5. Repeat until the model stops, calls `finish`, or repeats the same tool call five times consecutively. There is no default step cap.

The loop compacts old context by truncating tool output and dropping complete tool call groups. It never delegates pass or fail decisions to a second model. Syntax checks, exit codes, and diffs are deterministic.

### Interface layer

`paicode/tui/` is a Textual application with four regions: explorer, AI diff history, chat, and statistics. The agent runs in a worker thread and reports events to the interface through `call_from_thread`, so streaming text, tool updates, and diffs do not block input.

Assistant replies and command output are rendered with Textual Markdown widgets inside role-labeled cards. Markdown headings, lists, code fences, and tables use the monochrome theme; tool activity is rendered as compact single-line rows.

The prompt composer stores multiline pastes and clipboard images as local attachments. It displays highlighted `[pasted N lines]` and `[image-N]` markers, expands the paste text on submission, and passes images to the agent as OpenAI-compatible multimodal content. Newline keys are handled before submit, and copy and text-paste shortcuts use the system clipboard helpers before falling back to the terminal clipboard.

The chat pane keeps a two-line work status bar with an animated loading bar, current action, elapsed time, Esc hint, and queue count. Prompts submitted while a worker is active enter a local queue and start after the current turn finishes. The stop path uses a cooperative event checked between model turns and before each tool call.

`paicode/tui/actions.py` implements slash commands. Provider and model dialogs are separate modal screens.

## Events

The agent emits dataclasses from `paicode/agent/events.py`:

- `TextDelta` for streamed assistant text.
- `ToolStarted` and `ToolFinished` for tool activity.
- `UsageUpdated` after each provider response.
- `Finished` when the turn completes.
- `ErrorEvent` when the provider or a tool aborts the turn.

The TUI renders diffs from `ToolFinished.diff`, which contains a unified diff generated from the actual file contents. Git is not involved.

## Sessions

`paicode/db/` owns the SQLite schema, migrations, and provider seeder. The database is at `~/.local/state/paicode/paicode.db` or `$XDG_STATE_HOME/paicode/paicode.db`. Tables cover sessions, model messages, display transcript entries, AI diffs, usage stats, providers, provider keys, cached models, settings, and seeded provider presets.

The CLI creates a new session for a normal `pai` launch, resolves `--session` and `--s-xxxx` to the stored workspace, and lists sessions with `session-lists`. The TUI restores the transcript and diff history on session switch and saves diffs as they are produced. Multimodal image data is replaced with a text marker when messages are persisted, so the database does not retain raw image payloads.

Legacy JSON provider configuration and JSON session files are imported once and archived with a `.migrated-*` suffix. `pai --reset-db` checkpoints the database, creates a timestamped backup, drops every table, applies migrations, and seeds provider presets.

There are no `.pai_brain` or `.pai_history` writes in the workspace.

## Context strategy

Paicode does not summarize the conversation with another model call. It truncates individual tool results, keeps recent turns, and drops complete assistant and tool call groups when the character budget is exceeded. This keeps latency and cost predictable.
