---
id: "010"
title: "Move sessions and providers to SQLite with reset-db seeder"
type: "feature"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Move sessions and providers to SQLite with reset-db seeder

## Description
Replace JSON session files and JSON provider configuration with one SQLite database. Sessions, transcripts, diffs, messages, stats, providers, keys, models, and seeded provider presets live in the database. Add `pai --reset-db` that backs up the current database, drops every table, runs migrations, and seeds provider base URLs. Remove workspace-root session artifacts from the agent loop.

## Acceptance Criteria
- [x] SQLite database with migrations at the Paicode state root
- [x] Sessions, transcript entries, diffs, messages, and stats stored in tables
- [x] Providers, keys, models, and active provider stored in tables
- [x] Legacy JSON provider config and JSON session files migrate into the database
- [x] No `.pai_brain` or `.pai_history` writes from the agent loop
- [x] `pai --reset-db` backs up, drops, migrates, and seeds presets
- [x] Seeder includes DeepSeek, OpenCode, OpenAI, OpenRouter, Google, Groq, Mistral, xAI, Together, Fireworks, Perplexity, Cerebras, Moonshot, Zhipu, DashScope, MiniMax, NVIDIA, Hyperbolic, Novita, DeepInfra, Ollama, LM Studio, and custom
- [x] Auto-migrate and auto-seed on normal startup
- [x] Tests cover schema, seeding, reset backup, provider migration, session migration, and store behavior
- [x] Documentation updated and version bumped to 0.8.0

## Context / Notes
- Database default: `$XDG_STATE_HOME/paicode/paicode.db` or `~/.local/state/paicode/paicode.db`
- `PAICODE_STATE_DIR` overrides the state root for tests
- Seeder stores base URLs only, never API keys
- `--reset-db` is destructive; it creates a timestamped backup first
- Target files: 
- Dependencies: None
