---
id: "008"
title: "Add rich prompt attachments, work status, interrupt, and queue"
type: "feature"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Add rich prompt attachments, work status, interrupt, and queue

## Description
Expand the prompt composer and add attachment and queue behavior to the TUI. The input must grow upward, support an explicit expanded mode, replace multiline pastes with highlighted `[pasted N lines]` markers, and attach clipboard images as highlighted `[image-N]` markers. The chat pane needs a bottom loading bar with work status, a triple-Esc stop hint, and queued prompts that run after the current task finishes.

## Acceptance Criteria
- [x] Prompt grows upward automatically and `Ctrl+E` toggles a larger compose height
- [x] Multiline paste inserts a highlighted `[pasted N lines]` marker and expands to full text on submit
- [x] Image paste through a path or `Ctrl+V` inserts a highlighted `[image-N]` marker and sends multimodal content
- [x] Chat pane bottom shows an animated work bar, current action, elapsed time, Esc hint, and queue count
- [x] Esc pressed three times in quick succession requests a cooperative stop
- [x] Prompts submitted while busy are queued, displayed, and started automatically after the current task
- [x] `/stop` and `/queue [clear]` handle interrupt and queue inspection
- [x] Tests cover paste expansion, image path attachment, queue behavior, triple-Esc stop, and provider multimodal payload
- [x] Documentation updated and version bumped to 0.6.1

## Context / Notes
- Follow-up: Ctrl+V image paste uses wl-clipboard (`wl-paste`) with xclip fallback.
- Target files: paicode/tui/widgets/prompt.py, paicode/tui/clipboard.py, paicode/tui/commands.py, README.md, docs/
- No provider credentials or user images may be written into the repository
