---
id: "018"
title: "Stop rendering contract-review objections as empty chat errors"
type: "fix"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Stop rendering contract-review objections as empty chat errors

## Description
The chat pane treated every contract-review verdict of `object` as an error and rendered `Agent X (Role) object:` with an empty detail. Objections are a normal part of the council. Remove per-agent objection spam from chat, keep the audit state available in `/agents`, show one compact council review summary, and include the required changes in the stored agent status detail.

## Acceptance Criteria
- [x] `object` review verdicts no longer render as chat system errors
- [x] Only real failures or blocked states render as chat system notices
- [x] Contract objections include their required changes in the agent status detail
- [x] Council phase shows a compact objection count before lead arbitration
- [x] `/agents` still exposes review verdicts and details
- [x] Test proves object statuses produce no chat notice
- [x] Test proves failed statuses still produce a chat notice
- [x] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
