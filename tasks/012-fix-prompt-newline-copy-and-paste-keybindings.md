---
id: "012"
title: "Fix prompt newline copy and paste keybindings"
type: "fix"
status: "in-progress"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Fix prompt newline copy and paste keybindings

## Description
Make the prompt composer keyboard behavior dependable: Shift+Enter and Ctrl+J insert a newline, Ctrl+Shift+C copies the prompt selection or full prompt text, Ctrl+Shift+V pastes text without touching image attachments, and Ctrl+V keeps the image-first paste path. Cover Kitty keyboard protocol sequences, xterm modifyOtherKeys sequences, bracketed paste, and real system clipboard reads and writes.

## Acceptance Criteria
- [ ] Shift+Enter inserts a newline at the cursor and replaces a selection
- [ ] xterm modifyOtherKeys `shift+\r` inserts a newline
- [ ] Ctrl+J inserts a newline as a legacy terminal fallback
- [ ] Ctrl+Shift+C copies selected prompt text, or the full prompt when nothing is selected
- [ ] Ctrl+Shift+C writes to the system clipboard through wl-copy or xclip when available
- [ ] Ctrl+Shift+V pastes text only and never attaches an image
- [ ] Ctrl+Shift+V replaces the current selection and places the cursor after the paste
- [ ] Ctrl+V still attaches a clipboard image before considering text
- [ ] Bracketed paste of text still works when the terminal handles Ctrl+Shift+V itself
- [ ] Tests cover every key path and a real clipboard round trip when tools exist
- [ ] Help text and documentation describe the key bindings
- [ ] Version bumped to 0.8.3 and full test suite green

## Context / Notes
- Target files: 
- Dependencies: None
