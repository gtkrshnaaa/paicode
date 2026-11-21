---
id: "019"
title: "Guarantee simultaneous builder start and validator gating"
type: "fix"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Guarantee simultaneous builder start and validator gating

## Description
Builders must be dispatched together from the frozen contract, not handed off one by one. The work phase must announce all active builders at once, emit running status for each builder, batch the diff report after the build, and start the validator only after every builder has finished. Prove it with an eight-builder barrier test and a validator-after-all assertion.

## Acceptance Criteria
- [ ] All active builders are submitted to the executor before any waits for completion
- [ ] Build phase reports active/total equal to the full active builder count
- [ ] Each builder emits a running status with its owned files at start
- [ ] Builder diffs are flushed together after the build, not one at a time as builders finish
- [ ] Chat announces that all builders started together
- [ ] Chat announces that all builders finished before validation
- [ ] Validator cannot start before every builder has finished
- [ ] Eight-builder barrier test passes
- [ ] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
