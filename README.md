# Paicode

Paicode is a multi-agent terminal coding harness with a 22-agent council, a parallel builder team, and an independent validator. It reads, searches, edits, and runs real bash commands through a typed tool registry. It works with DeepSeek, OpenCode Console, OpenAI, OpenRouter, Google's OpenAI-compatible endpoint, or any custom base URL.

Every feature request starts with a lead-driven council. All 22 agents review the request, the lead freezes a contract with file ownership and interfaces, only the needed builders work in parallel, and agent 22 validates the integrated result. `--single-agent` remains available for small tasks.

## Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/gtkrshnaaa/paicode/main/install.sh | bash
```

This downloads the latest `main`, creates an isolated environment at `~/.local/share/paicode/venv`, and writes the launcher to `~/.local/bin/pai`. It does not edit your shell profile. The installer shows a structured header, a six-phase progress bar, and a completion summary. Package manager output stays hidden unless a step fails. Use `--quiet` to disable the spinner.

For a reproducible install, pin a tag or commit:

```bash
curl -fsSL https://raw.githubusercontent.com/gtkrshnaaa/paicode/main/install.sh | bash -s -- --ref <tag>
```

Prefer to inspect the script first:

```bash
curl -fsSLO https://raw.githubusercontent.com/gtkrshnaaa/paicode/main/install.sh
less install.sh
bash install.sh
```

Remove Paicode while keeping provider configuration:

```bash
curl -fsSL https://raw.githubusercontent.com/gtkrshnaaa/paicode/main/install.sh | bash -s -- --uninstall
```

## Install

Requirements: Python 3.10 or newer. Remote installs need `curl` and `tar`.

### From source

```bash
git clone https://github.com/gtkrshnaaa/paicode.git
cd paicode
./install.sh
```

### Development

```bash
./install.sh --dev
.venv/bin/pai
```

The installer creates an isolated environment, installs the package, and writes the launcher. If `~/.local/bin` is not on your `PATH`, the installer prints the export line to add.

Run Paicode from any project directory:

```bash
cd /path/to/project
pai
```

## First run

Start the TUI and connect a provider from the prompt:

```text
/connect deepseek
```

Enter the base URL and API key in the dialog. Paicode stores the provider, key, and session data in a SQLite database with mode `0600`. Then fetch and select a model:

```text
/models
/model deepseek-flash
```

The interface has four regions:

- Left: project file explorer. Select a file to preview it.
- Center: AI diff history for the current session. Every create, write, and surgical edit is rendered as a unified diff. The history is restored when the same session is reopened; a new session starts empty.
- Right: chat with role-labeled user and assistant cards, rendered Markdown, and compact tool activity.
- Bottom: token usage, request count, file counters, command count, provider, and model.

## Slash commands

| Command | Purpose |
| :--- | :--- |
| `/connect [preset]` | Configure a provider, base URL, and API key. |
| `/key [value]` | Add an API key to the active provider. |
| `/baseurl [url]` | Change the active provider base URL. |
| `/provider [name]` | List providers or switch the active one. |
| `/models` | Fetch models from the active provider. |
| `/model [name]` | Select a model. |
| `/rules` | Show loaded `PAICODE.md` files. |
| `/skills` | List installed skills. |
| `/skill <name>` | Print a skill. |
| `/stats` | Show session statistics. |
| `/limits` | Show step and context limits. |
| `/sessions` | List every session with workspace and timestamps. |
| `/session [id or new]` | Show the current session, switch sessions, or start a new one. |
| `/agents` | Show the 22-agent council state. |
| `/contract` | Show the frozen build contract. |
| `/bugs` | Show current validation findings. |
| `/stop` | Stop the current task after the active step. |
| `/queue [clear]` | Show or clear queued prompts. |
| `/config` | Show redacted provider configuration. |
| `/init` | Create a project `PAICODE.md` template. |
| `/refresh` | Reload rules, skills, and the file tree. |
| `/clear` | Clear chat and diff panes. |
| `/new` | Start a fresh session. |
| `/exit` | Quit Paicode. |

Provider presets: `deepseek`, `opencode`, `openai`, `openrouter`, `google`, and `custom`. Any OpenAI-compatible base URL works.

Typing `/` in the prompt opens a filtered command palette. Type more characters to narrow it, use Up and Down to move, Tab to complete, and Escape to dismiss. Enter accepts a partial command or runs an exact one.

## Multi-agent council

Agent 1 is the lead and contract owner. Agents 2 to 21 are builders with frontend, backend, database, auth, test, integration, accessibility, performance, DevOps, documentation, data, quality, and observability roles. Agent 22 is the independent validator.

The council runs in three stages:

1. All 22 agents submit proposals in parallel.
2. The lead synthesizes a contract with work units, file ownership, interfaces, API shapes, database schema, DOM tree, test plan, commands, and non-goals.
3. All 22 agents review the contract. The lead resolves objections and freezes it.

Only builders with assigned work units are activated. Active builders start together, not in sequence. Each builder may edit only its owned files. Agent 22 then runs the full test and acceptance matrix, files structured findings against the owning builder, and repeats the repair loop until green, three strikes, or five validation rounds. The lead always closes with a user-facing report covering the summary, delivered files, validation result, defects, and next steps. If the report model fails or the run is stopped, a deterministic report is emitted instead.

Every model request, from a single prompt to all 22 council calls, builder turns, and validator turns, carries the full global and project `PAICODE.md` rule envelope. Rules are never silently truncated and are placed first for provider prefix caching.

The full design is in [docs/multi-agent-architecture.md](docs/multi-agent-architecture.md).

```bash
pai                                  # multi-agent TUI
pai run "build the feature"          # multi-agent headless
pai --single-agent                   # single-agent TUI
pai run --single-agent "small task"  # single-agent headless
```

Concurrency and loop controls:

```text
PAICODE_AGENT_CONCURRENCY=22
PAICODE_VALIDATION_ROUNDS=5
PAICODE_AGENT_STRIKES=3
```

## Sessions

Every `pai` launch creates a new session for the current workspace. Sessions persist their chat transcript, AI diff history, model context, and usage statistics in the Paicode SQLite database.

List every session from anywhere:

```bash
pai session-lists
```

Each row includes the session ID, workspace path, creation timestamp, last-opened timestamp, and title.

Open a session and its workspace directly:

```bash
pai --session s-7f3a9c2d
pai --s-7f3a9c2d
```

Inside the TUI, `/sessions` lists all sessions with the current session marked. `/session <id>` switches to another session and restores its workspace, chat, and diff history. `/session new` starts a fresh session in the current workspace. `/session` with no argument shows the current session details.

## Chat rendering

Assistant replies render Markdown headings, lists, blockquotes, inline code, fenced code blocks, and tables. User messages use a bordered `YOU` card, assistant messages use a bordered `PAI` card, and tool activity stays on compact single-line rows. Every turn after the first starts with a labelled `TURN 02` divider and timestamp. The AI diff stream gives every change its own `DIFF 01` separator with path, additions, removals, and timestamp. `/sessions` and session details render as Markdown blocks that wrap cleanly in the chat pane.

## Prompt composer

The prompt expands upward as it fills and can be toggled to a larger compose area with `Ctrl+E`. `Shift+Enter` inserts a newline. `Ctrl+J` inserts a newline as well, which helps in terminals that cannot report `Shift+Enter`.

`Ctrl+Shift+C` copies the prompt selection, or the full prompt when nothing is selected. `Ctrl+Shift+V` pastes clipboard text only. Copy uses `wl-copy` on Wayland and `xclip` on X11 when available; paste uses `wl-paste` or `xclip`. Both also use the terminal clipboard as a fallback. `Ctrl+V` remains the image-first paste shortcut.

Multiline pastes become a highlighted `[pasted N lines]` marker. The full text is restored when the prompt is submitted, while the chat history keeps the compact marker.

Attach an image by pasting a path to a PNG, JPEG, WebP, or GIF file, or press `Ctrl+V` to read an image from the system clipboard. Clipboard images use `wl-paste` from wl-clipboard on Wayland, with `xclip` as the X11 fallback. Images become `[image-1]`, `[image-2]`, and are sent as multimodal content to vision-capable models.

While Paicode works, the bottom of the chat pane shows an animated loading bar, the current action, elapsed time, and the Esc hint. Press `Esc` three times in quick succession to stop after the current step. Prompts submitted while Paicode is busy are queued and start automatically when the current task finishes. Use `/queue` to inspect them or `/queue clear` to remove them.

## Rules and skills

Paicode follows the OpenCode placement convention.

Global:

- `~/.config/paicode/PAICODE.md`
- `~/.config/paicode/skills/<name>/SKILL.md`

Project:

- `<project>/PAICODE.md`
- `<project>/.paicode/skills/<name>/SKILL.md`

If `PAICODE.md` is absent, Paicode falls back to `AGENTS.md`. Skill files use YAML frontmatter with `name` and `description`. The system prompt lists available skills, and the agent loads one on demand with the `skill` tool.

The agenticway repository contains a Paicode edition with the full rules and skill set:

```bash
cd agenticway
./paicode/en/install-instruction.sh --global
```

Use `--workspace /path/to/project` to install project rules and skills instead. See `agenticway/paicode/en/README.md`.

## Long-running tasks

Paicode has no fixed model-turn limit. The loop stops when the model finishes, returns no tool calls, or repeats the same tool call five times in a row. A positive `--max-steps` value in headless mode sets an explicit ceiling.

Context compaction defaults to 2,500,000 characters. Override it with `PAICODE_CONTEXT_CHARS`. Tool limits are deliberately generous: 20,000 lines per read request, 20 MB files, 5,000 list and search results, and 200,000 characters of shell output.

## Headless mode

For scripts and CI:

```bash
pai run "Add a health check endpoint and run the tests"
pai run --single-agent "Rename this variable"
pai run --diff "Refactor the parser"
pai models
pai doctor
pai --path /path/to/project run "Summarize this repository"
```

## Configuration

Providers, keys, sessions, transcripts, diffs, and stats live in `~/.local/state/paicode/paicode.db` or `$XDG_STATE_HOME/paicode/paicode.db`. Override the state directory with `PAICODE_STATE_DIR` or the exact database path with `PAICODE_DB_PATH`. Override the project root with `PAICODE_ROOT`.

Reset the database with a fresh migration and provider seed:

```bash
pai --reset-db
```

The reset creates a timestamped backup of the existing database, drops every table, runs migrations, and seeds provider base URLs. API keys are database data, so a reset removes them; the backup preserves the previous state. The seeder includes DeepSeek, OpenCode, OpenAI, OpenRouter, Google, Groq, Mistral, xAI, Together, Fireworks, Perplexity, Cerebras, SambaNova, Moonshot, Zhipu, DashScope, MiniMax, NVIDIA, Hyperbolic, Novita, DeepInfra, GitHub Models, Ollama, LM Studio, and a custom entry.

Each provider stores its base URL, API keys, selected model, cached model list, and optional models URL. Multiple keys are rotated automatically when a provider returns an authentication or rate-limit error.

## Coding harness

`bash` is a real bash shell with pipes, redirection, multi-command scripts, package managers, compilers, test runners, formatters, and git. On Linux, commands run inside a bubblewrap sandbox when it is available: the workspace is writable, the rest of the filesystem is read-only, the real home directory is hidden, package caches are isolated, and child processes are killed on timeout or stop.

The deterministic capability matrix covers Python, Node, C, C++, Java, shell, Git, SQLite, JSON tooling, HTTP and static web tasks, multi-file refactors, debugging loops, and the full agent write-test-fix-finish cycle. Go, Rust, TypeScript, and Docker cases skip cleanly when their toolchains are unavailable. See [docs/capability-matrix.md](docs/capability-matrix.md).

## Security model

- Workspace writes are confined to the project root with `commonpath`, symlink resolution, and a sensitive-name denylist.
- `explore` provides read-only host filesystem inspection outside the workspace. It requires a concrete reason and blocks credentials, private keys, shell history, browser profiles, Paicode configuration, and pseudo-filesystems such as `/proc`, `/sys`, and `/dev`.
- `bash` runs real bash. With bubblewrap, the workspace is the only writable host path, the home directory is hidden, and the cache is isolated. Without bubblewrap, Paicode falls back to direct execution. Both modes remove provider secrets, SSH agent sockets, and sensitive environment variables, and reject catastrophic host commands, privilege escalation, raw device writes, filesystem creation, package publishing, and privileged containers.
- The independent validator uses read-only file tools and a disposable overlayfs workspace for shell commands. Validation tests can write build artifacts, but those writes are discarded and production source cannot be modified.
- Shell commands use their own process group and are terminated on timeout or user stop. Output is bounded at 200,000 characters with a truncation marker.
- Config writes are atomic and protected by a file lock.
- The agent is instructed not to commit or push unless the user asks. Shell git access is otherwise unrestricted so real coding workflows remain possible.

## Development

```bash
./install.sh --dev
.venv/bin/pytest -q
make matrix
```

The full suite covers path security, surgical edits, provider configuration, rule and skill discovery, OpenAI-compatible SSE streaming, the agent loop, the Textual layout, shell execution and sandboxing, and the real coding capability matrix.

## License

MIT. See `LICENSE`.
