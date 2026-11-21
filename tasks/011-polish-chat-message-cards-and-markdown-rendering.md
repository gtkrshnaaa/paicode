---
id: "011"
title: "Polish chat message cards and Markdown rendering"
type: "refactor"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Refactor] Polish chat message cards and Markdown rendering

## Description
Give the chat pane a deliberate visual hierarchy: role-labeled user and assistant cards, compact tool rows, readable system notices, and real Markdown rendering for assistant and command output. Render session lists as Markdown blocks instead of a wide fixed table, increase chat width and padding, and keep everything monochrome.

## Acceptance Criteria
- [x] User messages have a You label, card background, and left border
- [x] Assistant messages have a Pai label, card container, and rendered Markdown
- [x] Markdown headings, lists, code fences, inline code, blockquotes, and tables render cleanly
- [x] Tool rows stay one line and ellipsize long detail
- [x] `/sessions` and current-session details render as Markdown
- [x] Chat pane width and padding give the content room without wasting space
- [x] Tests cover Markdown/system/assistant widget creation
- [x] Visual screenshot reviewed
- [x] Documentation updated and version bumped to 0.8.2

## Context / Notes
- Target files: paicode/tui/widgets/chat.py, paicode/tui/app.py, paicode/tui/actions.py, paicode/sessions/format.py
- Monochrome styling only, no colored code highlighting
- Target files: 
- Dependencies: None
