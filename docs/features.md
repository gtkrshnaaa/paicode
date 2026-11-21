# Features

## Multi-agent council

Paicode is multi-agent by default. Agent 1 leads a 22-agent council, agents 2 to 21 are builders, and agent 22 is the independent validator. Every model request carries the full global and project `PAICODE.md` rules, including all council proposals, reviews, builder turns, and validator turns. Rules are not truncated by the default limits and are placed first for provider prefix caching. The council produces a frozen contract with file ownership, interfaces, API shapes, database schema, DOM tree, test plan, commands, and non-goals before code is written. Only the builders assigned to work units are activated, and they write in parallel. The validator runs the integrated test matrix and routes findings back to the owning builder until green or the repair budget is exhausted. `--single-agent` bypasses the council for small tasks.

## Multi-pane terminal interface

The Textual interface keeps the project tree, AI diffs, conversation, and usage statistics visible at the same time. File changes stream into the center pane as unified diffs generated from the old and new file contents.

## Provider independence

Any OpenAI-compatible endpoint works. Configure a base URL and key from the prompt with `/connect`. The provider layer discovers models through the provider's models endpoint and stores the result for instant switching.

## Model switching

`/models` fetches the provider catalog and `/model` opens a selector. Direct selection also works: `/model deepseek-v4-pro`.

## Key rotation

A provider can hold multiple API keys. When a key returns an authentication or rate-limit error, the client marks a cooldown and retries with the next key. The active key is never printed.

## Surgical editing

The `edit` tool replaces an exact string and rejects ambiguous matches unless `replace_all` is set. The result is written atomically and returned as a unified diff. This preserves the original token-efficient editing model.

## Typed tools

The model receives JSON schemas for every tool instead of a text command protocol. Prompts, validation, and dispatch share one source of truth, so a tool cannot exist in the dispatcher while being invisible to the model.

## Deterministic verification

Python and JSON writes run an in-process syntax check. Shell commands return real exit codes, and stale Python bytecode is removed after edits. The agent loop never asks another model whether a step passed.

## Real bash harness

The `bash` tool runs real bash with pipes, redirection, multi-command scripts, package managers, compilers, test runners, formatters, and git. On Linux it uses bubblewrap when available: the workspace is the only writable host path, the real home directory is hidden, package caches are isolated, and child processes are killed on timeout or user stop. Direct execution is the fallback, with secret scrubbing and catastrophic-command guards in both modes. The capability matrix covers Python, Node, C, C++, Java, shell, Git, SQLite, JSON, HTTP and static web tasks, refactors, debugging, and optional Go, Rust, TypeScript, and Docker toolchains.

## Rules and skills

Global and project `PAICODE.md` files are injected into the system prompt. Skills are discovered from `~/.config/paicode/skills` and `<project>/.paicode/skills`, listed with their descriptions, and loaded on demand through the `skill` tool.

## Persistent sessions

Every TUI launch is a session with a stable ID, workspace path, creation time, and last-opened time. Sessions persist chat transcripts, AI diff history, model context, and usage statistics in SQLite. `pai session-lists` lists everything from outside Paicode. `/sessions` and `/session <id>` list and switch sessions inside the TUI. Reopening a session restores its workspace and diff history; a new session starts with an empty diff pane.

## Chat rendering

The chat pane uses role-labeled user and assistant cards, inset spacing, and monochrome Markdown rendering. Headings, lists, blockquotes, inline code, fenced code blocks, and tables are supported. Tool activity is compact, and session lists render as readable Markdown blocks.

## Prompt attachments and queueing

The prompt expands upward and supports a larger `Ctrl+E` compose mode. `Shift+Enter` and `Ctrl+J` insert newlines. `Ctrl+Shift+C` copies the prompt selection or the full prompt, and `Ctrl+Shift+V` pastes text only. Clipboard text and images use wl-clipboard on Wayland, with `xclip` as the X11 fallback. Multiline pastes become highlighted `[pasted N lines]` markers and expand to the full text on submit. Images from a pasted path or `Ctrl+V` become `[image-1]`, `[image-2]` markers and are sent as multimodal content.

The chat pane bottom shows an animated loading bar with the current action, elapsed time, and Esc hint. Three quick Esc presses stop after the active step. Prompts submitted while the agent works are queued and start automatically when the current task finishes.

## Guarded host exploration

The `explore` tool gives read-only access to the host filesystem outside the current workspace for host configuration, installed tools, services, logs, and other projects. Every call requires a concrete reason. Credentials, private keys, shell history, browser profiles, Paicode configuration, and pseudo-filesystems are blocked. Writes remain confined to the workspace.

## Long-running execution

Interactive sessions have no fixed model-turn limit. A repeated-action detector stops the loop only when the same tool call appears five times in a row. The context budget defaults to 2,500,000 characters, and tool limits allow 20,000-line reads, 20 MB files, 5,000 list and search results, and 200,000 characters of shell output.

## Usage statistics

The bottom bar tracks prompt, completion, and total tokens, request count, files read, files created, files edited, and commands executed. `/stats` shows the same data with elapsed time.

## Headless operation

`pai run` uses the same agent loop without the TUI. `--diff` prints file diffs, which makes the command usable in scripts and CI.
