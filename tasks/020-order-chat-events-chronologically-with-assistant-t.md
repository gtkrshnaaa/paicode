---
id: "020"
title: "Order chat events chronologically with assistant timestamps"
type: "fix"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Order chat events chronologically with assistant timestamps

## Description
Chat event delivery was asynchronous across agent threads, so the final report could appear before tool rows and builder statuses. The assistant card also stayed above later widgets, forcing later report text above earlier tools. Funnel every multi-agent event through one ordered dispatcher, close assistant cards when a tool or system notice arrives, start a new timestamped card for later text, and fix the Markdown mount race that could leave assistant cards empty.

## Acceptance Criteria
- [ ] Multi-agent events pass through one FIFO dispatcher
- [ ] Tool rows cannot appear after the final report
- [ ] Validator status appears before the final report
- [ ] Assistant cards close before tool rows and system notices
- [ ] Later assistant text starts a new card after the tool rows
- [ ] Every assistant card label includes a timestamp
- [ ] Assistant Markdown content survives mount and never renders empty
- [ ] Test asserts tool events precede the report and validation precedes the report
- [ ] Test asserts ordered cards and timestamp labels
- [ ] Test asserts assistant card source is non-empty
- [ ] Visual screenshot reviewed
- [ ] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
