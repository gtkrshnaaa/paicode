# Platform configuration

Paicode reads settings from two files:

- Global: `~/.config/paicode/settings.json`
- Project: `<project>/.paicode/settings.json`

Project values override global values with a deep merge. Lists are replaced, not concatenated. All settings are optional. Invalid values fail fast with a configuration error.

## Full example

```json
{
  "permission_mode": "standard",
  "permissions": [
    {"action": "shell", "resource": "*", "effect": "ask"},
    {"action": "shell", "resource": "git status*", "effect": "allow"},
    {"action": "write", "resource": "vendor/*", "effect": "deny"}
  ],
  "budget": {
    "max_tokens": 2000000,
    "max_cost_usd": 5.0,
    "prompt_price_per_million": 0.30,
    "cache_hit_price_per_million": 0.006,
    "completion_price_per_million": 1.20
  },
  "compaction_threshold_chars": 1500000,
  "compaction_keep_last": 8,
  "telemetry": false,
  "diagnostics": ["pytest -q", "ruff check ."],
  "mcp": {
    "servers": {
      "docs": {
        "transport": "http",
        "url": "https://mcp.example.com/mcp",
        "headers": {"Authorization": "Bearer replace-with-token"},
        "timeout": 30
      },
      "local": {
        "transport": "stdio",
        "command": ["python3", "-m", "my_mcp_server"],
        "env": {"LOG_LEVEL": "info"}
      }
    }
  },
  "hooks": [
    {"event": "post_tool", "command": "python3 .paicode/hooks/format.py", "timeout": 30}
  ],
  "plugins": [".paicode/plugins/project_tools.py"]
}
```

Environment variables inside MCP headers are not expanded automatically. Pass literal values or start the server with the required environment.

## Permissions

Rules are evaluated in order and the last matching rule wins. `action` and `resource` accept shell-style globs.

Actions:

- `read`: read, list, glob, grep, skill
- `write`: write, edit, mkdir, move, delete
- `shell`: bash commands
- `explore`: host filesystem exploration
- `mcp`: MCP tools
- `plugin`: plugin tools

Effects:

- `allow`: run immediately
- `ask`: open the approval dialog in the TUI, deny in headless mode
- `deny`: block immediately

Modes:

- `standard`: default allow, explicit rules can deny or ask
- `strict`: shell, write, and MCP default to ask
- `trusted`: allow everything, intended for isolated disposable environments

## Budgets

`max_tokens` and `max_cost_usd` cap a session. Cost is estimated from the configured per-million token prices, including separate cache hit and cache miss input prices. When a cap is crossed, the current run stops with a budget error before the next model request. `/budget` shows the live total, cache hit and cache miss tokens, and the active prices. If prices are unset, cost remains zero; Paicode does not hardcode provider prices.

`PAICODE_MAX_OUTPUT_TOKENS` caps output per model turn. The default is 8,192. `PAICODE_SOLO_MAX_STEPS` caps solo turns and defaults to 60.

## Context compaction

Older turns are summarized when the context exceeds `compaction_threshold_chars`, or 80 percent of `PAICODE_CONTEXT_CHARS` when unset. The newest `compaction_keep_last` messages are retained verbatim. The summary is inserted as a `[COMPACTED HISTORY]` system block. If the provider summary fails, deterministic truncation is used.

## Checkpoints and rewind

Every write, edit, delete, and move captures the affected files before mutation. Checkpoints live under the Paicode state directory, not inside the repository.

```bash
pai rewind
pai rewind latest
pai rewind 20261122-101500
```

In the TUI, `/rewind` lists checkpoints and `/rewind latest` restores the newest one.

## MCP

Local servers use newline-delimited JSON over stdio. Remote servers use streamable HTTP. OAuth is not built in; pass an authorization header from a trusted environment when required.

```bash
pai mcp status
pai mcp tools
pai mcp resources docs
pai mcp prompts docs
```

MCP tools are namespaced as `mcp__<server>__<tool>`. Read-only discussion and validation runs never receive MCP tools.

## Hooks

Hooks receive one JSON object on stdin with `event`, `cwd`, and event-specific fields. Example for `pre_tool`:

```json
{"event": "pre_tool", "cwd": "/work/project", "tool": "bash", "arguments": {"command": "pytest -q"}}
```

Exit code 0 allows the action. A nonzero exit blocks it for `pre_tool` and `pre_compact`. Hook output is truncated and returned to the agent for blocking hooks. Provider secrets are removed from the hook environment.

## Plugins

A plugin is a Python file listed explicitly under `plugins`. It must export `register(api)`:

```python
def register(api):
    api.add_tool(
        "project_stats",
        "Return repository statistics",
        lambda args: "42 files",
        {"type": "object", "properties": {}},
    )
```

Tools are exposed as `plugin__<file>__<tool>`. Plugin code runs in the Paicode process, so only enable plugins you trust. Plugins are not loaded in read-only runs.

## Diagnostics

`diagnostics` is a list of shell commands. The `diagnostics` tool runs them and returns combined output and exit codes. The tool is hidden in read-only mode. `/diagnostics` runs the same commands directly from the TUI.

## Telemetry

Set `telemetry` to `true` to append local JSONL events to the state directory:

```text
~/.local/state/paicode/telemetry/events.jsonl
```

Events cover run start, tool calls, compaction, and run end with token and cost totals. Prompt text, file contents, and secrets are not recorded. Telemetry is local only and disabled by default.


## Platform support

- Linux: full feature set, bubblewrap sandbox when available.
- macOS: full terminal and API feature set, direct execution fallback, no built-in sandbox.
- Windows: run inside WSL or a container. Native shell and sandbox integration are not implemented.
- CI: Linux runs the full suite, macOS runs the platform and integration subset. Release artifacts are built on Linux.

## Audit and policy inspection

```bash
pai policy
pai audit --out audit.json
pai telemetry --tail 50
```

`pai policy` prints the active permission mode, rules, and budget. `pai audit` exports sessions, agent runs, contracts, validation runs, and findings without provider keys.

## Operational references

- [Enterprise deployment](enterprise.md)
- [Local API and SDK](api.md)
- [Security policy](../SECURITY.md)
