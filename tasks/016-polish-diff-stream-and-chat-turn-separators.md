---
id: "016"
title: "Polish diff stream and chat turn separators"
type: "refactor"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Refactor] Polish diff stream and chat turn separators

## Description
Make the diff stream and chat pane look deliberate instead of appended. Add a labelled separator between every diff with path, counts, and timestamp. Add a labelled turn divider before every new user turn. Refine cards, role labels, tool rows, spacing, and monochrome surfaces. Keep the Textual layout responsive and verify with real screenshots.

## Acceptance Criteria
- [x] Every diff starts with a labelled separator showing index, path, additions, removals, and timestamp
- [x] Diff line styles distinguish additions, removals, hunks, and context without color noise
- [x] Chat mounts a turn divider before every user turn after the first
- [x] Turn divider includes turn number and time and spans the available width
- [x] User and assistant cards have clean monochrome borders, labels, and spacing
- [x] Tool rows remain compact and readable
- [x] System notices are visually distinct but quiet
- [x] Restored sessions rebuild dividers and cards correctly
- [x] Diff and chat widget tests cover separators and labels
- [x] Visual screenshots reviewed in the real Textual layout
- [x] Documentation updated and version bumped

## Context / Notes
- Target files: 
- Dependencies: None
