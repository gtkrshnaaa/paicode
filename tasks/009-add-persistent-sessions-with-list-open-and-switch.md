---
id: "009"
title: "Add persistent sessions with list, open, and switch"
type: "feature"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Add persistent sessions with list, open, and switch

## Description
Persist every Paicode TUI run as a named session with a stable ID, workspace path, created timestamp, and last-opened timestamp. A normal `pai` launch creates a new session. `pai session-lists` shows every session from outside Paicode. `pai --session <id>` or `pai --<id>` opens that session and its workspace. Inside the TUI, `/sessions` lists sessions and `/session <id>` switches to one, restoring its chat transcript and AI diff history.

## Acceptance Criteria
- [ ] Session store persists id, workspace, created_at, last_opened_at, title, transcript, diffs, messages, and stats
- [ ] `pai session-lists` shows complete session info sorted by last opened
- [ ] `pai --session <id>` and `pai --s-xxxx` open the session workspace and data
- [ ] Normal `pai` starts a new session for the current workspace
- [ ] TUI `/sessions` lists sessions and `/session <id>` switches, restoring transcript and diffs
- [ ] `/session new` starts a fresh session in the current workspace
- [ ] Diff history survives close and reopen only when the same session is reopened
- [ ] Switching sessions updates workspace root, explorer, rules, skills, stats, and topbar
- [ ] Tests cover store, CLI listing/opening, TUI switching, transcript and diff restoration
- [ ] Documentation updated and version bumped to 0.7.0

## Context / Notes
- State root: `$XDG_STATE_HOME/paicode/sessions` or `~/.local/state/paicode/sessions`
- `PAICODE_STATE_DIR` overrides the state root for tests
- Never store provider credentials in session files
- Target files: 
- Dependencies: None
