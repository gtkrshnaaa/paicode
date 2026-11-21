---
id: "009"
title: "Add persistent sessions with list, open, and switch"
type: "feature"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Add persistent sessions with list, open, and switch

## Description
Persist every Paicode TUI run as a named session with a stable ID, workspace path, created timestamp, and last-opened timestamp. A normal `pai` launch creates a new session. `pai session-lists` shows every session from outside Paicode. `pai --session <id>` or `pai --<id>` opens that session and its workspace. Inside the TUI, `/sessions` lists sessions and `/session <id>` switches to one, restoring its chat transcript and AI diff history.

## Acceptance Criteria
- [x] Session store persists id, workspace, created_at, last_opened_at, title, transcript, diffs, messages, and stats
- [x] `pai session-lists` shows complete session info sorted by last opened
- [x] `pai --session <id>` and `pai --s-xxxx` open the session workspace and data
- [x] Normal `pai` starts a new session for the current workspace
- [x] TUI `/sessions` lists sessions and `/session <id>` switches, restoring transcript and diffs
- [x] `/session new` starts a fresh session in the current workspace
- [x] Diff history survives close and reopen only when the same session is reopened
- [x] Switching sessions updates workspace root, explorer, rules, skills, stats, and topbar
- [x] Tests cover store, CLI listing/opening, TUI switching, transcript and diff restoration
- [x] Documentation updated and version bumped to 0.7.0

## Context / Notes
- State root: `$XDG_STATE_HOME/paicode/sessions` or `~/.local/state/paicode/sessions`
- `PAICODE_STATE_DIR` overrides the state root for tests
- Never store provider credentials in session files
- Target files: 
- Dependencies: None
