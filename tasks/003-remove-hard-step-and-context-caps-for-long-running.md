---
id: "003"
title: "Remove hard step and context caps for long-running tasks"
type: "feature"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Feature] Remove hard step and context caps for long-running tasks

## Description
Long-running DeepSeek tasks are currently cut off at 12 model turns and compacted at 180,000 characters. Make the default step count unlimited, raise the context and tool budgets to very generous values, add repeated-action detection instead of a fixed step cap, and expose the context budget through an environment variable.

## Acceptance Criteria
- [x] Agent loop has no fixed step limit by default and `--max-steps 0` means unlimited
- [x] Repeated identical tool calls are detected and stop the loop with a clear error
- [x] Context budget defaults to 2,500,000 characters with `PAICODE_CONTEXT_CHARS` override
- [x] Tool read, list, glob, grep, shell output, and message limits are raised
- [x] Tests cover a 15-turn unlimited run, large context retention, and loop detection
- [x] Documentation and changelog updated to 0.5.1

## Context / Notes
- Target files: paicode/agent/loop.py, paicode/cli.py, paicode/tools/, paicode/core/paths.py
- No API key or provider credential may be written to the repository.
