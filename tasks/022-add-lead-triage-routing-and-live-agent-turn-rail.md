---
id: "022"
title: "Add lead triage routing and live agent turn rail"
type: "feat"
status: "done"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Feat] Add lead triage routing and live agent turn rail

## Description
Agent 1 must receive every prompt first and decide whether it can answer alone, needs a read-only discussion, or must deploy the builder team. Read-only analysis, summaries, planning, and discussion stay with one agent. Any write task estimated at more than one file, scaffolding, feature work, or large refactor must go to the 22-agent team with a validator. Add a live Agent Rail on the right showing each agent's status and nested turn/action history, including council, thinking, read, create, edit, delete, list, command, explore, and skill actions.

## Acceptance Criteria
- [x] `SmartRunner` performs an Agent 1 triage call before routing
- [x] Triage receives the full PAICODE.md rule envelope
- [x] Read-only analysis, explanation, summary, audit, and planning route to one read-only agent
- [x] Discussion requests route to read-only discussion mode
- [x] One-file small writes route to Agent 1 alone
- [x] More than one expected file forces the 22-agent team
- [x] Unknown-size write, scaffolding, feature, and large refactor force the team
- [x] Triage failure defaults safely: read-only to lead, write work to team
- [x] Team mode starts the council, builders, and validator
- [x] `/single-agent` bypasses triage and council
- [x] Agent Rail shows all 22 agents with status and nested turn count
- [x] Agent Rail updates on council, thinking, read, create, edit, delete, list, command, explore, and skill actions
- [x] Agent Rail remains readable and scrollable in the right pane
- [x] Tests cover routing decisions, forced team rules, and rail updates
- [x] Visual screenshot reviewed
- [x] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
