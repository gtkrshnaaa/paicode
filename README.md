# Paicode

Paicode is a terminal coding agent with a multi-pane Textual interface and an OpenAI-compatible provider layer. It reads, searches, edits, and runs project commands through a typed tool registry. It works with DeepSeek, OpenCode Console, OpenAI, OpenRouter, Google's OpenAI-compatible endpoint, or any custom base URL.

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

Assistant replies render Markdown headings, lists, blockquotes, inline code, fenced code blocks, and tables. User messages use a `You` card, assistant messages use a `Pai` card, and tool activity stays on compact single-line rows. `/sessions` and session details render as Markdown blocks that wrap cleanly in the chat pane.

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

## Security model

- Workspace writes are confined to the project root with `commonpath`, symlink resolution, and a sensitive-name denylist.
- `explore` provides read-only host filesystem inspection outside the workspace. It requires a concrete reason and blocks credentials, private keys, shell history, browser profiles, Paicode configuration, and pseudo-filesystems such as `/proc`, `/sys`, and `/dev`.
- `bash` has no shell. Commands are split with `shlex`, validated against an allowlist, and rejected if they contain shell operators, absolute paths, or parent traversal. Read-only host commands are available for OS and service inspection. Provider secrets are removed from the subprocess environment.
- Config writes are atomic and protected by a file lock.
- The agent never commits or pushes. Git access is limited to read-only commands.

## Development

```bash
./install.sh --dev
.venv/bin/pytest -q
```

The test suite covers path security, surgical edits, provider configuration, rule and skill discovery, shell policy, OpenAI-compatible SSE streaming, the agent loop, and the Textual layout.

## License

MIT. See `LICENSE`.
