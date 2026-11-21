---
id: "007"
title: "Polish installer output with progress and structured summary"
type: "feature"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Polish installer output with progress and structured summary

## Description
Replace the raw pip output in `install.sh` with a clean monochrome installer display: a structured header, a six-phase progress bar, an animated spinner on TTY, hidden command logs with failure tails, and a completion summary with version, paths, next steps, and elapsed time. Keep local, remote, piped, dev, uninstall, and quiet modes working.

## Acceptance Criteria
- [x] Header shows mode, platform, Python, install root, launcher, and source
- [x] Six phases render a `[####----] n/6` progress bar and spinner on TTY
- [x] Non-TTY and `--quiet` modes print clean step lines without animation
- [x] Package output is captured to per-step logs, with tail and log path on failure
- [x] Completion summary shows version, launcher, config path, next command, and elapsed time
- [x] Local, remote-tarball, piped, dev, uninstall, and quiet paths remain functional
- [x] Real curl install from GitHub verified in a sandbox
- [x] Version bumped to 0.5.6 and changelog updated

## Context / Notes
- Target files: install.sh, tests/test_installer.py, CHANGELOG.md, paicode/__init__.py, setup.cfg
- Monochrome output only: bold, dim, and ASCII progress characters
- Target files: 
- Dependencies: None
