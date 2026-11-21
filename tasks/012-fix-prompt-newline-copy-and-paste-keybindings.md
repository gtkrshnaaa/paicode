---
id: "012"
title: "Fix prompt newline copy and paste keybindings"
type: "fix"
status: "done"
created_at: "2026-11-21"
updated_at: "2026-11-21"
---

# [Fix] Fix prompt newline copy and paste keybindings

## Description
Make the prompt composer keyboard behavior dependable: Shift+Enter and Ctrl+J insert a newline, Ctrl+Shift+C copies the prompt selection or full prompt text, Ctrl+Shift+V pastes text without touching image attachments, and Ctrl+V keeps the image-first paste path. Cover Kitty keyboard protocol sequences, xterm modifyOtherKeys sequences, bracketed paste, and real system clipboard reads and writes.

## Acceptance Criteria
- [x] Shift+Enter inserts a newline at the cursor and replaces a selection
- [x] xterm modifyOtherKeys `shift+\r` inserts a newline
- [x] Ctrl+J inserts a newline as a legacy terminal fallback
- [x] Ctrl+Shift+C copies selected prompt text, or the full prompt when nothing is selected
- [x] Ctrl+Shift+C writes to the system clipboard through wl-copy or xclip when available
- [x] Ctrl+Shift+V pastes text only and never attaches an image
- [x] Ctrl+Shift+V replaces the current selection and places the cursor after the paste
- [x] Ctrl+V still attaches a clipboard image before considering text
- [x] Bracketed paste of text still works when the terminal handles Ctrl+Shift+V itself
- [x] Tests cover every key path and a real clipboard round trip when tools exist
- [x] Help text and documentation describe the key bindings
- [x] Version bumped to 0.8.3 and full test suite green

## Context / Notes
- Target files: 
- Dependencies: None
