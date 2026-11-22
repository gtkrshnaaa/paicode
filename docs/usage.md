# Usage

## Start the interface

```bash
pai
pai --path /path/to/project
```

The current directory is the project root unless `--path` or `PAICODE_ROOT` is set.

## Connect a provider

Use `/connect` without arguments to open the provider dialog. A preset name prefills the base URL:

```text
/connect deepseek
/connect opencode
/connect custom https://gateway.example.com/v1
```

The dialog asks for the provider name, base URL, and API key. The provider and key are stored with mode `0600` in the Paicode SQLite database at `~/.local/state/paicode/paicode.db`.

Use `/key` to add another key to the active provider. Use `/baseurl` to change the endpoint without re-entering keys.

## Select a model

```text
/models
/model
```

`/models` refreshes the provider catalog. `/model` opens the selector when a catalog is cached. A direct model name skips the dialog:

```text
/model deepseek-flash
```

## Send a task

Type a request and press Enter. Agent 1 first triages the request, then streams the result, executes tools, and renders every file change in the center pane. The rightmost Agent Rail shows all 22 agents and their nested actions. The chat uses bordered user and timestamped assistant cards with a labelled turn divider between requests. Assistant text, tool rows, notices, and later reports stay in chronological order. The diff pane gives each change its own labelled header band with path, additions, removals, and timestamp, monochrome syntax highlighting, and a closing rule. Clicking a file opens a syntax-highlighted read-only preview. The bottom bar updates after each provider response.

Useful prompts:

```text
Find the retry logic and make it use exponential backoff.
Add tests for the parser and run them.
Read the deployment script and explain the failure modes.
```

## Smart routing and council

Agent 1 triages every request before any work starts:

- Read-only analysis, explanation, summary, audit, and planning use one read-only agent.
- A small edit touching exactly one file may use Agent 1 alone.
- Any write touching more than one file, scaffolding, a new feature, a migration, or a large refactor uses the 22-agent team.

When the team is selected:

- Agent 1 leads the council and owns the frozen contract.
- Agents 2 to 21 are builders.
- Agent 22 validates tests and contract conformance.

The council submits 22 proposals in parallel, the lead freezes file ownership and interfaces, and all 22 agents review the contract. Only builders with assigned files activate, and they build in parallel. Agent 22 tests the integrated workspace and sends structured findings to the owning builder. Repair repeats until green, three strikes, or five rounds. The lead closes every run with a report covering the summary, delivered files, validation result, defects, and next steps.

The rightmost Agent Rail shows every agent, its status, and its nested turn history with timestamps for council, thinking, read, create, edit, delete, list, command, explore, and skill actions.

Every model request carries the full global and project `PAICODE.md` rules. This includes single-agent turns, all council calls, builder turns, and validator turns. Rules are never silently truncated by the default limits and are placed first for provider prefix caching.

```text
/agents
/contract
/bugs
```

Read-only discussion mode:

```text
/disscus compare the two authentication designs
/discuss explain the tradeoffs in the current module layout
```

Discussion mode can read, search, explore, and run read-only shell inspection. It cannot write files, build artifacts, install packages, mutate git, or redirect shell output.

Use `--single-agent` when a task is too small to justify the council:

```bash
pai --single-agent
pai run --single-agent "Rename this variable"
```

Concurrency controls:

```text
PAICODE_AGENT_CONCURRENCY=22
PAICODE_VALIDATION_ROUNDS=5
PAICODE_AGENT_STRIKES=3
```

## Rules

`/rules` lists the loaded rule files. `/init` creates a project `PAICODE.md` template.

Global rules live at `~/.config/paicode/PAICODE.md`. Project rules live at `<project>/PAICODE.md`. When the project file is absent, `AGENTS.md` is used as a fallback.

## Skills

`/skills` lists installed skills. `/skill <name>` prints one. The agent also sees the catalog and can load a skill itself when the description matches the task.

Global skills: `~/.config/paicode/skills/<name>/SKILL.md`.

Project skills: `<project>/.paicode/skills/<name>/SKILL.md`.

A skill file starts with YAML frontmatter:

```markdown
---
name: api-review
description: Review API handlers for input validation and error propagation.
---

# API Review
...
```

## Sessions

Every `pai` launch creates a new session for the current workspace. The chat transcript, AI diff history, model context, usage statistics, provider configuration, and keys are stored in the Paicode SQLite database at `~/.local/state/paicode/paicode.db`.

```bash
pai session-lists
pai --session s-7f3a9c2d
pai --s-7f3a9c2d
```

`pai session-lists` shows the session ID, workspace path, creation timestamp, last-opened timestamp, and title. Opening a session switches to its workspace and restores its chat and diff history.

Inside Paicode, `/sessions` lists all sessions with the current one marked. `/session <id>` switches, and `/session new` creates a fresh session in the current workspace. `/session` alone shows the current ID, workspace, creation time, last-opened time, and title.

## Database reset

`pai --reset-db` performs a fresh database migration:

```bash
pai --reset-db
```

It backs up the current database to a timestamped `.bak-*` file, drops all tables, runs migrations, and seeds provider presets. The seeded order starts with DeepSeek, OpenCode, OpenAI, OpenRouter, and Google, followed by other OpenAI-compatible providers. API keys are removed by the reset; they remain available in the backup file.

## Prompt composer

The prompt expands upward with its content. `Ctrl+E` toggles a larger compose area, and `Shift+Enter` inserts a newline. `Ctrl+J` also inserts a newline and is the fallback for terminals that cannot report `Shift+Enter`.

`Ctrl+Shift+C` copies the prompt selection, or the full prompt when nothing is selected. `Ctrl+Shift+V` pastes clipboard text only. Copy uses `wl-copy` on Wayland and `xclip` on X11 when available; paste uses `wl-paste` or `xclip`. Both also use the terminal clipboard as a fallback. `Ctrl+V` keeps the image-first behavior.

Multiline paste is replaced with a highlighted `[pasted N lines]` marker. The full text is restored when submitted; the chat history keeps the marker.

Paste an image path or press `Ctrl+V` to attach an image from the clipboard. Clipboard images use `wl-paste` from wl-clipboard on Wayland, with `xclip` as the X11 fallback. Images appear as `[image-1]`, `[image-2]`, and are sent as multimodal content. Use a vision-capable model such as `deepseek-flash`.

While the agent works, the bottom of the chat pane shows a moving loading bar, the current action, elapsed time, and the queue count. Press `Esc` once to stop immediately. Active provider streams are aborted and sandboxed shell process groups are killed. A prompt submitted while the agent is busy is queued and starts automatically after the current task. `/queue` lists queued prompts, `/queue clear` removes them, and `/stop` requests a stop.

## Host exploration

Inside the workspace, Paicode uses `read`, `list`, `glob`, and `grep`. Outside the workspace, it can use the read-only `explore` tool when the task needs host context, installed tools, services, logs, or another project.

```text
Inspect /etc/os-release and summarize the distribution.
Check the nginx configuration under /etc/nginx.
Find the installed Node version and the active systemd failures.
```

The agent must state a concrete reason before exploring. File tool writes remain confined to the workspace, and sandboxed shell writes are confined as well. Credentials, private keys, shell history, browser profiles, Paicode configuration, and pseudo-filesystems are denied.

## Shell and build tasks

The `bash` tool runs real bash in the workspace. Use it for package managers, compilers, test runners, linters, formatters, multi-step scripts, pipelines, redirection, and git.

```text
pytest -q
npm test
go test ./...
cargo test --quiet
cmake -S . -B build && cmake --build build --parallel 2
git status --short && git diff --check
```

On Linux, commands run inside a bubblewrap sandbox when it is available. The workspace is writable, the rest of the filesystem is read-only, the real home directory is hidden, and package caches live in an isolated directory. If bubblewrap is unavailable, Paicode falls back to direct execution with secret scrubbing and catastrophic-command guards.

Environment controls:

```text
PAICODE_SHELL_SANDBOX=auto|direct|required
PAICODE_SANDBOX_CACHE=/path/to/cache
PAICODE_SANDBOX_NETWORK=0|1
PAICODE_SANDBOX_DOCKER=0|1
```

`pai doctor` reports whether the shell is sandboxed or direct.

## Long-running tasks

The interactive session has no model-turn cap. The loop stops when the model calls `finish`, returns no tool calls, or repeats the same tool call five times consecutively.

The context budget defaults to 2,500,000 characters and can be changed with `PAICODE_CONTEXT_CHARS`. A positive `--max-steps` value in headless mode sets an explicit ceiling; `0` keeps the run unlimited.

## Headless commands

```bash
pai run "Add a health check endpoint"
pai run --diff "Refactor the parser"
pai --path ../service run "Run the tests and fix failures"
pai models
pai doctor
pai config show
```

`pai doctor` prints the version, project root, config path, provider status, available tools, rules, and skills.

## Slash command suggestions

Typing `/` opens a filtered command palette above the prompt. Up and Down move the selection, Tab completes the highlighted command, Escape dismisses the palette, and Enter accepts a partial command or runs an exact one. The palette stays monochrome and keeps focus in the prompt.

## Slash command reference

```text
/help
/connect [preset] [base_url]
/key [value]
/baseurl [url]
/provider [name]
/models
/model [name]
/rules
/skills
/skill <name>
/stats
/limits
/config
/init
/refresh
/clear
/new
/exit
```

## Keyboard shortcuts

- `Ctrl+L` clears the chat and diff panes.
- `Ctrl+R` refreshes the file explorer.
- `F1` shows help.
- `Ctrl+C` exits the application.
