---
id: "013"
title: "Build industry-grade shell sandbox and coding capability matrix"
type: "feat"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feat] Build industry-grade shell sandbox and coding capability matrix

## Description
Replace the read-only allowlisted shell with a real bash execution layer that supports pipes, redirection, arbitrary development tools, working directories, process-group cancellation, bounded output, and workspace write isolation through bubblewrap. Add an industry-grade coding capability matrix covering Python, Node, C, C++, shell, git, SQLite, static web, JSON tooling, multi-file refactors, debugging loops, and optional Go, Rust, TypeScript, and Docker toolchains. Prove the full agent loop can write code, run tests, read failures, edit, and finish.

## Acceptance Criteria
- [x] `bash` runs arbitrary commands through `bash -lc`, including pipes, redirection, env vars, and multi-command scripts
- [x] Shell working directory is project-relative, must exist, and cannot escape the workspace
- [x] Shell timeouts use process groups so child processes cannot outlive the command
- [x] Shell output is bounded with a clear truncation marker
- [x] Provider and host secrets are scrubbed from the shell environment
- [x] Bubblewrap sandbox keeps writes inside the workspace and hides the real home directory when available
- [x] Direct execution fallback is explicit and still blocks catastrophic host commands
- [x] Git init, status, diff, add, commit, and log work through the shell
- [x] Python, Node, C, C++, shell, SQLite, static web, and JSON coding tasks pass real build and test commands
- [x] Debugging matrix proves a failing test is read, fixed, and rerun green
- [x] Multi-file refactor matrix proves surgical edits across modules
- [x] Go, Rust, TypeScript, and Docker cases skip cleanly when toolchains are unavailable
- [x] A full FakeOpenAI agent session writes a project, runs tests, fixes a failure, and calls finish
- [x] Capability matrix documentation and README security model are updated
- [x] Version bumped and full suite green

## Context / Notes
- Target files: 
- Dependencies: None
