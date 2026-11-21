---
id: "017"
title: "Make the lead report results after every multi-agent run"
type: "fix"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Make the lead report results after every multi-agent run

## Description
The lead must always summarize the work after the builders and validator finish. The report should stream into the chat as the lead's message, include what was delivered, files changed, validation result, defects fixed or unresolved, and next steps. If the model report fails or the run is stopped, emit a deterministic report instead of silence.

## Acceptance Criteria
- [x] Lead report runs after validation success
- [x] Lead report runs after validation failure, strike limit, or partial build
- [x] Lead report runs with the mandatory PAICODE.md rule envelope
- [x] Stopped runs emit a deterministic lead report without extra model calls
- [x] Report includes delivered work, files, validation result, findings, and next steps
- [x] Report streams as assistant text in the TUI
- [x] Report prints in headless output before the finished footer
- [x] Model report failure falls back to a deterministic summary
- [x] Fake-provider multi-agent test asserts a visible lead report
- [x] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
