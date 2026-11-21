---
id: "002"
title: "v0.5.0 TUI and provider overhaul"
type: "feature"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] v0.5.0 TUI and provider overhaul

## Description
Replace the Gemini-only text-command loop with an OpenAI-compatible provider layer and a Textual multi-pane TUI. Preserve the core insights: surgical edits, resumable task state, multi-key resilience, and capability-aware tools.

## Acceptance Criteria
- [ ] OpenAI-compatible provider layer with base URL, API key, dynamic model discovery, and streaming tool calls
- [ ] Slash commands inside the TUI: /help, /connect, /key, /baseurl, /provider, /models, /model, /rules, /skills, /skill, /stats, /clear, /exit
- [ ] Textual TUI: file explorer left, AI diff stream center, chat right, token/file statistics bottom
- [ ] PAICODE.md and project/global skill discovery following the OpenCode layout
- [ ] Agenticway paicode edition with rules, skills, and installer in en/ and id_en/
- [ ] Root install.sh installs a launcher to ~/.local/bin and works from any directory
- [ ] Unit tests, TUI tests, and a local OpenAI-compatible SSE integration test pass
- [ ] Live DeepSeek end-to-end run verified with a real file edit
- [ ] Documentation updated and version bumped to 0.5.0

## Context / Notes
- Target files: paicode/ package, install.sh, docs/, tests/
- Dependencies: openai, textual, pytest, pytest-asyncio
- Preserve: surgical search/replace, .pai_brain task state, provider key rotation, capability probing
