---
id: "025"
title: "Prevent TUI crash when clicking stale markdown table cells"
type: "fix"
status: "done"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Fix] Prevent TUI crash when clicking stale markdown table cells

## Description
Textual 8.2.8 crashes on mouse down when the compositor returns a markdown table cell that was detached during a markdown refresh. `Screen._forward_event` reads `container.region` where `container` is the cell's `parent`, which is `None`. This happens while chat markdown streams or re-renders a table on the default screen.

## Acceptance Criteria
- [x] Stale markdown table cell mouse down no longer raises AttributeError
- [x] The default TUI screen uses a guarded screen class
- [x] The guard only handles the detached-widget selection error and logs it
- [x] Unrelated AttributeError still propagates
- [x] Normal text selection still starts for mounted widgets
- [x] Regression test reproduces the detached cell crash first
- [x] Full suite green, version bumped, docs updated

## Context / Notes
- Target files: 
- Dependencies: None
