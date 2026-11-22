---
id: "023"
title: "Add --session-lists flag alias with complete session table"
type: "fix"
status: "done"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Fix] Add --session-lists flag alias with complete session table

## Description
The session listing exists as `pai session-lists`, but `pai --session-lists` is rejected. Add root flags `--session-lists` and `--sessions` that print the complete session table: ID, workspace path, creation time, last-opened time, and title.

## Acceptance Criteria
- [x] `pai --session-lists` prints the complete session table
- [x] `pai --sessions` works as an alias
- [x] Existing `pai session-lists` and `pai sessions` still work
- [x] ID, workspace, created, last opened, and title are all present
- [x] Empty database prints a clear "No sessions yet" message
- [x] Tests cover the flag and subcommand forms
- [x] Docs updated and version bumped

## Context / Notes
- Target files: 
- Dependencies: None
