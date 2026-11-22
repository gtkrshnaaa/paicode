---
id: "028"
title: "Make cost-aware solo mode the default with plan, todo, and verify loop"
type: "feature"
status: "done"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Feature] Make cost-aware solo mode the default with plan, todo, and verify loop

## Description
Switch the default execution path from the 22-agent team to one cost-aware solo agent with explicit planning, a live todo list, deterministic verification, and a bounded repair pass. Keep the team available only through an explicit `/team` command or `--team` flag. Track cache-hit and cache-miss input tokens so cost reporting matches the provider bill.

## Acceptance Criteria
- [x] Solo mode is the default for the TUI and headless runs
- [x] Solo mode plans before acting and exposes a todo tool
- [x] Solo mode verifies configured diagnostics after edits and performs at most one repair pass
- [x] Team mode is opt-in through `/team` and `--team`
- [x] Output tokens per model turn are configurable and capped by default
- [x] Cache hit and cache miss tokens are recorded
- [x] Estimated cost uses real cache prices and is shown in stats
- [x] Tests cover solo planning, todo, verify, team opt-in, cache accounting, and output caps
- [x] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
