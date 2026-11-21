# Internal Architecture

Paicode is split into a provider layer, a typed tool layer, an agent loop, and a Textual interface. The control plane is deterministic Python. The model decides what to do next, but code decides how tools execute, how paths are validated, and how failures are reported.

## Layers

### Provider layer

`paicode/providers/` contains the OpenAI-compatible client, provider presets, and the configuration store.

- `client.py` streams chat completions, assembles tool call deltas, records usage, and rotates API keys on authentication or rate-limit failures.
- `store.py` persists providers, base URLs, keys, selected models, and cached model lists in `~/.config/paicode/config.json`.
- `presets.py` defines DeepSeek, OpenCode Console, OpenAI, OpenRouter, Google OpenAI compatibility, and custom providers.

The OpenCode preset uses `https://opencode.ai/inference/openai/v1` for chat and `https://opencode.ai/inference/v1/models` for discovery.

### Tool layer

`paicode/tools/` exposes twelve typed tools to the model through OpenAI function calling:

`read`, `write`, `edit`, `list`, `glob`, `grep`, `bash`, `skill`, `mkdir`, `move`, `delete`, and `finish`.

`registry.py` dispatches calls and converts security errors into tool results. `fs.py` implements atomic writes, surgical replacements, diffs, and in-process syntax checks for Python and JSON. `shell.py` enforces the command allowlist and scrubs provider secrets from the environment. `search.py` provides bounded glob and regex search.

### Agent loop

`paicode/agent/loop.py` owns one turn:

1. Build a system prompt from the base contract, global rules, project rules, and the skill catalog.
2. Stream a completion from the provider.
3. Append the assistant message and any tool calls to the conversation.
4. Execute each tool, emit a result event, and append a tool message.
5. Repeat until the model stops, calls `finish`, or repeats the same tool call five times consecutively. There is no default step cap.

The loop compacts old context by truncating tool output and dropping complete tool call groups. It never delegates pass or fail decisions to a second model. Syntax checks, exit codes, and diffs are deterministic.

### Interface layer

`paicode/tui/` is a Textual application with four regions: explorer, diff stream, chat, and statistics. The agent runs in a worker thread and reports events to the interface through `call_from_thread`, so streaming text, tool updates, and diffs do not block input.

`paicode/tui/actions.py` implements slash commands. Provider and model dialogs are separate modal screens.

## Events

The agent emits dataclasses from `paicode/agent/events.py`:

- `TextDelta` for streamed assistant text.
- `ToolStarted` and `ToolFinished` for tool activity.
- `UsageUpdated` after each provider response.
- `Finished` when the turn completes.
- `ErrorEvent` when the provider or a tool aborts the turn.

The TUI renders diffs from `ToolFinished.diff`, which contains a unified diff generated from the actual file contents. Git is not involved.

## Persistence

`.pai_brain/session.md` stores the last request, turn count, summary, changed files, and token totals. `.pai_history/session-YYYYMMDD.log` stores an append-only turn log. Both directories are self-contained and can be removed safely.

## Context strategy

Paicode does not summarize the conversation with another model call. It truncates individual tool results, keeps recent turns, and drops complete assistant and tool call groups when the character budget is exceeded. This keeps latency and cost predictable.
