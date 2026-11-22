---
id: "027"
title: "Post-release hardening: audit export, policy inspection, and server startup reliability"
type: "fix"
status: "in-progress"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Fix] Post-release hardening: audit export, policy inspection, and server startup reliability

## Description
Follow-up hardening after the 0.14.0 platform release. Adds a secret-free audit export, a policy inspection command, and flushed server startup output for automation. Releases the changes as 0.14.1.

## Acceptance Criteria
- [x] Audit export covers sessions, runs, contracts, validations, and findings
- [x] Audit export contains no provider keys
- [x] `pai policy` prints mode, rules, and budgets
- [x] Server startup details flush immediately
- [x] Tests cover audit export and CLI commands
- [x] Docs updated and version bumped to 0.14.1

## Context / Notes
- Target files: 
- Dependencies: None
