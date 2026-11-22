---
id: "024"
title: "Collapse builder roster and enforce universal parallel work units"
type: "refactor"
status: "in-progress"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Refactor] Collapse builder roster and enforce universal parallel work units

## Description
Collapse agents 2 to 21 into one universal Builder role with no specialties. The lead assigns one file or one cohesive sub-feature flow per builder, one work unit per builder, up to 20 builders. Keep the council, parallel dispatch, shared-board ownership, and independent validator. Add paste-position metadata, enforce unique builder ownership, audit unowned changed files, and update the Agent Rail to show only Lead, Builder, and Validator roles.

## Acceptance Criteria
- [ ] Roster has exactly three role types: Lead, Builder, Validator
- [ ] Agents 2 to 21 are identical universal builders with no specialty
- [ ] Builder proposal, contract review, and build prompts contain no specialty language
- [ ] Contract validation rejects duplicate builder owners
- [ ] Contract validation enforces one work unit per builder
- [ ] Contract supports depends_on, integration_order, and integration_note
- [ ] Lead synthesis assigns distinct builders and at most 20 work units
- [ ] All active builders still start together and validator waits for all
- [ ] Validator audits changed files against ownership and shared files
- [ ] Unowned changed files produce a finding
- [ ] Agent Rail shows LEAD, BUILDER, and VALIDATOR labels only
- [ ] Tests cover roster, prompts, ownership, unique builders, validator audit, and rail labels
- [ ] Live or deterministic team test still passes
- [ ] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
