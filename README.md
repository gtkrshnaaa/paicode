# Paicode

Paicode is a terminal coding agent with a multi-pane Textual interface and an OpenAI-compatible provider layer. It reads, searches, edits, and runs project commands through a typed tool registry. It works with DeepSeek, OpenCode Console, OpenAI, OpenRouter, Google's OpenAI-compatible endpoint, or any custom base URL.

## Install

Requirements: Python 3.10 or newer, and `curl` for the pip bootstrap fallback.

```bash
git clone https://github.com/gtkrshnaaa/paicode.git
cd paicode
./install.sh
```

The installer creates an isolated environment at `~/.local/share/paicode/venv`, installs the package, and writes the launcher to `~/.local/bin/pai`. It does not edit your shell profile. If `~/.local/bin` is not on your `PATH`, the installer prints the export line to add.

Run Paicode from any project directory:

```bash
cd /path/to/project
pai
```

For development inside the repository:

```bash
./install.sh --dev
.venv/bin/pai
```

## First run

Start the TUI and connect a provider from the prompt:

```text
/connect deepseek
```

Enter the base URL and API key in the dialog. Paicode stores the provider in `~/.config/paicode/config.json` with mode `0600`. Then fetch and select a model:

```text
/models
/model deepseek-flash
```

The interface has four regions:

- Left: project file explorer. Select a file to preview it.
- Center: AI diff stream. Every create, write, and surgical edit is rendered as a unified diff.
- Right: chat, streaming assistant text, and tool activity.
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
| `/config` | Show redacted provider configuration. |
| `/init` | Create a project `PAICODE.md` template. |
| `/refresh` | Reload rules, skills, and the file tree. |
| `/clear` | Clear chat and diff panes. |
| `/new` | Start a fresh session. |
| `/exit` | Quit Paicode. |

Provider presets: `deepseek`, `opencode`, `openai`, `openrouter`, `google`, and `custom`. Any OpenAI-compatible base URL works.

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

Configuration lives in `~/.config/paicode/config.json`. Override the location with `PAICODE_CONFIG_DIR`. Override the project root with `PAICODE_ROOT`.

Each provider stores its base URL, API keys, selected model, cached model list, and optional models URL. Multiple keys are rotated automatically when a provider returns an authentication or rate-limit error.

## Security model

- File tools resolve every path inside the project root with `commonpath`, reject symlink escapes, and deny sensitive entries such as `.env`, `.git`, and `.ssh`.
- `bash` has no shell. Commands are split with `shlex`, validated against an allowlist, and rejected if they contain shell operators, absolute paths, or parent traversal. Provider secrets are removed from the subprocess environment.
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
