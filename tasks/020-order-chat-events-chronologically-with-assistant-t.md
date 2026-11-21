---
id: "020"
title: "Order chat events chronologically with assistant timestamps"
type: "fix"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Order chat events chronologically with assistant timestamps

## Description
Chat event delivery was asynchronous across agent threads, so the final report could appear before tool rows and builder statuses. The assistant card also stayed above later widgets, forcing later report text above earlier tools. Funnel every multi-agent event through one ordered dispatcher, close assistant cards when a tool or system notice arrives, start a new timestamped card for later text, and fix the Markdown mount race that could leave assistant cards empty.

## Acceptance Criteria
- [x] Multi-agent events pass through one FIFO dispatcher
- [x] Tool rows cannot appear after the final report
- [x] Validator status appears before the final report
- [x] Assistant cards close before tool rows and system notices
- [x] Later assistant text starts a new card after the tool rows
- [x] Every assistant card label includes a timestamp
- [x] Assistant Markdown content survives mount and never renders empty
- [x] Test asserts tool events precede the report and validation precedes the report
- [x] Test asserts ordered cards and timestamp labels
- [x] Test asserts assistant card source is non-empty
- [x] Visual screenshot reviewed
- [x] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
