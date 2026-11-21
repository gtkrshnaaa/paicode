---
id: "005"
title: "Add slash command suggestions to the prompt"
type: "feature"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Add slash command suggestions to the prompt

## Description
Show a filtered command palette above the prompt while the user types a slash command. Typing `/` lists commands, typing more characters narrows the list, Up/Down moves the selection, Tab completes the command, and Escape dismisses the palette. Keep it monochrome and do not steal focus from the prompt.

## Acceptance Criteria
- [x] Slash command metadata has one source of truth used by help and suggestions
- [x] Suggestion palette appears for `/` prefixes and hides for arguments, newlines, or no matches
- [x] Up/Down navigation wraps, Tab completes, Escape dismisses
- [x] Palette is monochrome, capped at a readable window, and keeps prompt focus
- [x] Tests cover filtering, navigation, completion, and dismissal
- [x] Documentation updated and version bumped to 0.5.3
- [x] Scrollbars hidden while wheel and keyboard scrolling remain functional

## Context / Notes
- Target files: paicode/tui/commands.py, paicode/tui/widgets/prompt.py, paicode/tui/widgets/suggestions.py, paicode/tui/app.py
- No provider credentials in any UI or test
