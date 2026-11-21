---
id: "015"
title: "Inject PAICODE global rules into every model request"
type: "feat"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feat] Inject PAICODE global rules into every model request

## Description
Every model request in both single-agent and multi-agent mode must carry the full global PAICODE.md rules. This includes council proposals, lead synthesis, contract review, arbitration, builder turns, validator turns, and every single-agent turn. Rules must not be silently truncated by the default limits. Add an audit test that inspects every fake-provider request and a live smoke run through the installed package.

## Acceptance Criteria
- [x] Global and project PAICODE.md rules are rendered without the previous 100,000 character truncation
- [x] Per-file rule loading limit is raised so normal global rules are not truncated
- [x] Single-agent system prompt contains global rules
- [x] Council proposal prompts contain global rules
- [x] Lead synthesis and arbitration prompts contain global rules
- [x] Contract review prompts contain global rules
- [x] Builder system prompts contain global rules
- [x] Validator system prompt contains global rules
- [x] Every fake-provider request in a 22-agent run contains a unique global rule marker
- [x] A test counts requests against requests carrying the marker
- [x] TUI and headless both pass loaded rules into MultiAgentRunner
- [x] Performance and bottleneck notes added to docs
- [x] Live DeepSeek run confirms rules are present and the feature still completes
- [x] Full suite green and version bumped

## Context / Notes
- Target files: 
- Dependencies: None
