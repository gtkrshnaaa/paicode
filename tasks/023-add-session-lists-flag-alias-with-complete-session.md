---
id: "023"
title: "Add --session-lists flag alias with complete session table"
type: "fix"
status: "in-progress"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Fix] Add --session-lists flag alias with complete session table

## Description
The session listing exists as `pai session-lists`, but `pai --session-lists` is rejected. Add root flags `--session-lists` and `--sessions` that print the complete session table: ID, workspace path, creation time, last-opened time, and title.

## Acceptance Criteria
- [ ] `pai --session-lists` prints the complete session table
- [ ] `pai --sessions` works as an alias
- [ ] Existing `pai session-lists` and `pai sessions` still work
- [ ] ID, workspace, created, last opened, and title are all present
- [ ] Empty database prints a clear "No sessions yet" message
- [ ] Tests cover the flag and subcommand forms
- [ ] Docs updated and version bumped

## Context / Notes
- Target files: 
- Dependencies: None
