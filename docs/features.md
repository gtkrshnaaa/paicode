# Features

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

Python and JSON writes run an in-process syntax check. Shell commands return real exit codes. The agent loop never asks another model whether a step passed.

## Rules and skills

Global and project `PAICODE.md` files are injected into the system prompt. Skills are discovered from `~/.config/paicode/skills` and `<project>/.paicode/skills`, listed with their descriptions, and loaded on demand through the `skill` tool.

## Persistent session state

`.pai_brain/session.md` records the last request, summary, changed files, and token totals. On the next launch, Paicode shows the previous session state. `.pai_history` keeps an append-only log.

## Long-running execution

Interactive sessions have no fixed model-turn limit. A repeated-action detector stops the loop only when the same tool call appears five times in a row. The context budget defaults to 2,500,000 characters, and tool limits allow 20,000-line reads, 20 MB files, 5,000 list and search results, and 200,000 characters of shell output.

## Usage statistics

The bottom bar tracks prompt, completion, and total tokens, request count, files read, files created, files edited, and commands executed. `/stats` shows the same data with elapsed time.

## Headless operation

`pai run` uses the same agent loop without the TUI. `--diff` prints file diffs, which makes the command usable in scripts and CI.
