---
id: "006"
title: "Add guarded read-only OS exploration"
type: "feature"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Add guarded read-only OS exploration

## Description
Allow Paicode to inspect the host filesystem outside the current workspace for host context, installed tools, services, logs, and other projects, while keeping every write operation confined to the workspace. Exploration must require a concrete reason, block credentials and pseudo-filesystems, and make the current workspace and exploration purpose explicit in the system prompt and tool output.

## Acceptance Criteria
- [ ] New read-only `explore` tool with path, required reason, optional pattern, and limit
- [ ] Sensitive paths, private keys, credential stores, shell history, and pseudo-filesystems are denied
- [ ] Writes, edits, deletes, and moves outside the workspace remain impossible
- [ ] System prompt states cwd, project root, home, platform, and the OS exploration policy
- [ ] Read-only host commands such as uname, df, free, ps, lscpu, lsblk, systemctl status, and journalctl are allowlisted
- [ ] `/limits` and TUI welcome text explain workspace writes versus read-only host exploration
- [ ] Tests cover allowed exploration, blocked secrets, reason enforcement, and write confinement
- [ ] Real DeepSeek run inspects /etc/os-release through the new tool
- [ ] Version bumped to 0.5.5 and documentation updated

## Context / Notes
- Target files: paicode/core/paths.py, paicode/tools/explore.py, paicode/tools/schemas.py, paicode/tools/registry.py, paicode/tools/shell.py, paicode/agent/prompts.py
- Never expose provider credentials or private keys
- Target files: 
- Dependencies: None
