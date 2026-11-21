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

The dialog asks for the provider name, base URL, and API key. The key is stored with mode `0600` in `~/.config/paicode/config.json`.

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

Type a request and press Enter. The agent streams text to the right pane, executes tools, and renders every file change in the center pane. The bottom bar updates after each provider response.

Useful prompts:

```text
Find the retry logic and make it use exponential backoff.
Add tests for the parser and run them.
Read the deployment script and explain the failure modes.
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
