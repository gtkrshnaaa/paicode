---
id: "004"
title: "Add curl and bash remote installer with README quick install"
type: "feature"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Add curl and bash remote installer with README quick install

## Description
Make `install.sh` work both from a repository checkout and from a piped `curl | bash` execution. The remote mode must download a source archive from GitHub, install into the isolated venv, and write the launcher. Add a prominent quick install command to the top of the README.

## Acceptance Criteria
- [ ] `install.sh` detects local checkout mode and remote piped mode
- [ ] Remote mode downloads a GitHub tarball with `curl`, extracts it with `tar`, and installs from the extracted source
- [ ] `--ref`, `PAICODE_REF`, `PAICODE_SOURCE_URL`, and `--remote` are supported
- [ ] Local `--dev`, `--uninstall`, and normal installation still work
- [ ] README has a quick install section near the top with the curl command and a safer two-step alternative
- [ ] Local, remote-tarball, and real GitHub curl installations are verified in a sandbox HOME
- [ ] Version bumped to 0.5.2 and changelog updated

## Context / Notes
- Target files: install.sh, README.md, paicode/__init__.py, setup.cfg, CHANGELOG.md
- Never include provider credentials in the installer or repository
- Target files: 
- Dependencies: None
