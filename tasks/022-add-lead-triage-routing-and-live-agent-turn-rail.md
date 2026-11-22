---
id: "022"
title: "Add lead triage routing and live agent turn rail"
type: "feat"
status: "in-progress"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Feat] Add lead triage routing and live agent turn rail

## Description
Agent 1 must receive every prompt first and decide whether it can answer alone, needs a read-only discussion, or must deploy the builder team. Read-only analysis, summaries, planning, and discussion stay with one agent. Any write task estimated at more than one file, scaffolding, feature work, or large refactor must go to the 22-agent team with a validator. Add a live Agent Rail on the right showing each agent's status and nested turn/action history, including council, thinking, read, create, edit, delete, list, command, explore, and skill actions.

## Acceptance Criteria
- [ ] `SmartRunner` performs an Agent 1 triage call before routing
- [ ] Triage receives the full PAICODE.md rule envelope
- [ ] Read-only analysis, explanation, summary, audit, and planning route to one read-only agent
- [ ] Discussion requests route to read-only discussion mode
- [ ] One-file small writes route to Agent 1 alone
- [ ] More than one expected file forces the 22-agent team
- [ ] Unknown-size write, scaffolding, feature, and large refactor force the team
- [ ] Triage failure defaults safely: read-only to lead, write work to team
- [ ] Team mode starts the council, builders, and validator
- [ ] `/single-agent` bypasses triage and council
- [ ] Agent Rail shows all 22 agents with status and nested turn count
- [ ] Agent Rail updates on council, thinking, read, create, edit, delete, list, command, explore, and skill actions
- [ ] Agent Rail remains readable and scrollable in the right pane
- [ ] Tests cover routing decisions, forced team rules, and rail updates
- [ ] Visual screenshot reviewed
- [ ] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
