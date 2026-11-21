---
id: "021"
title: "Add read-only discussion mode and syntax-highlighted diffs"
type: "feat"
status: "in-progress"
created_at: "2026-11-22"
updated_at: "2026-11-22"
---

# [Feat] Add read-only discussion mode and syntax-highlighted diffs

## Description
Add a `/disscus <prompt>` read-only discussion mode. The discussion runner may read files, search, explore, and run read-only shell inspection, but file tools deny writes and shell commands use a disposable overlay plus a read-only command policy. Add monochrome syntax highlighting to the diff stream and file preview, and make each diff a strongly separated block. Keep `/discuss` as an alias.

## Acceptance Criteria
- [ ] `/disscus <prompt>` starts a discussion run
- [ ] `/discuss <prompt>` works as an alias
- [ ] Discussion mode denies write, edit, mkdir, move, and delete
- [ ] Discussion shell runs on a disposable overlay
- [ ] Discussion shell rejects write commands, git mutations, package installs, and output redirection
- [ ] Discussion mode can still read files, search, list, explore, and run read-only git inspection
- [ ] Discussion mode uses the full PAICODE.md rule envelope
- [ ] Diff stream uses syntax highlighting for common languages
- [ ] File preview uses a monochrome syntax theme with line numbers
- [ ] Each diff has a strong header band and closing rule with generous spacing
- [ ] Tests cover discussion denial, read-only shell, syntax helpers, and preview theme
- [ ] Visual screenshot reviewed for diff and preview
- [ ] Full suite green, docs updated, version bumped

## Context / Notes
- Target files: 
- Dependencies: None
