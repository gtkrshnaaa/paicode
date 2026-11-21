---
id: "014"
title: "Make Paicode multi-agent by default with 22-agent council and validator"
type: "feat"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feat] Make Paicode multi-agent by default with 22-agent council and validator

## Description
Make Paicode multi-agent by default. Agent 1 is the lead, agents 2 to 21 are builders, agent 22 is the independent validator. All 22 discuss a feature first and freeze a build contract. Only needed builders work, and they work in parallel. The validator runs tests, files strict bug tickets to the owning builder, and repeats until green. Persist the council, contract, ownership, tasks, findings, and strikes in SQLite. Keep `--single-agent` as an escape hatch.

## Acceptance Criteria
- [x] Multi-agent is the default for TUI and headless runs
- [x] `--single-agent` still works
- [x] Agent roster defines exactly 22 roles
- [x] All 22 agents submit council proposals in parallel
- [x] Lead synthesizes a typed build contract with file ownership and interfaces
- [x] All 22 agents review the contract before it is frozen
- [x] Contract validation rejects duplicate owners, missing owners, and more than 20 work units
- [x] Only builders needed by the contract are activated
- [x] Active builders start concurrently and the barrier test proves it
- [x] Per-agent write allowlists reject unowned file edits
- [x] Shared files and build artifacts are protected from conflicting writes
- [x] Agent 22 runs full validation and produces structured findings
- [x] Findings are routed to the owning builder with strict accountability language
- [x] Builder repair loop reruns validation until green or the round limit
- [x] Three strikes and five validation rounds are enforceable
- [x] Cancellation stops all agents and sandboxed shell process groups
- [x] Provider requests use a shared concurrency gate and key cooldown
- [x] Agent runs, contracts, ownership, findings, strikes, and events persist in SQLite
- [x] TUI shows phase status and `/agents` lists the 22 agent states
- [x] Headless mode shows council, build, validation, and sign-off phases
- [x] Deterministic 22-agent fake-provider end-to-end test passes
- [x] Live DeepSeek multi-agent smoke test passes with the configured provider
- [x] Documentation updated and version bumped

## Context / Notes
- Target files: 
- Dependencies: None
