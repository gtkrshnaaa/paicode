import os
import json
import asyncio
import time
from datetime import datetime
from rich.console import Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.text import Text
from rich.box import ROUNDED
from rich.table import Table
import shlex
import shutil
from . import llm, workspace, ui
from .platforms import detect_os
from .awareness import get_mega_prompt

from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound

HISTORY_DIR = os.path.join(os.getcwd(), ".pai_history")
_python_interpreter_checked = False

def _system_directive() -> str:
    return (
        "You are the LLM brain operating inside PaiCode. Always act as an agent that outputs at most one actionable line using HEADER:: syntax when planning actions. "
        "Respect single-command-per-step. Prefer minimal, targeted edits. If a modification results in no changes, propose a more explicit patch or read the file first. "
        "Avoid unrelated refactors. Never include markdown fences in code responses."
    )

def _summarize_exec_result(text: str, max_lines_per_section: int = 40) -> str:
    """Trim very long STDOUT/STDERR sections for summary display (streaming already shows full)."""
    try:
        lines = text.splitlines()
        def _trim_section(start_idx: int) -> None:
            # Trim lines after header line
            count = 0
            i = start_idx + 1
            while i < len(lines) and not lines[i].startswith("STDERR:") and not lines[i].startswith("STDOUT:"):
                count += 1
                i += 1
            if count > max_lines_per_section:
                # Keep header + first N lines and add ellipsis
                kept = lines[start_idx + 1:start_idx + 1 + max_lines_per_section]
                del lines[start_idx + 1:start_idx + 1 + count]
                lines[start_idx + 1:start_idx + 1] = kept + ["... (truncated) ..."]

        # Find sections and trim
        idx = 0
        while idx < len(lines):
            if lines[idx].startswith("STDOUT:"):
                _trim_section(idx)
            elif lines[idx].startswith("STDERR:"):
                _trim_section(idx)
            idx += 1
        return "\n".join(lines)
    except Exception:
        return text

def _generate_execution_renderables(plan: str, omit_long_response: bool = True, injected_thought: str = "") -> tuple[Group, str]:
    """
    Executes the plan, generates Rich renderables for display, and creates a detailed log string.
    """
    if not plan:
        msg = "Agent did not produce an action plan."
        return Group(Text(msg, style="warning")), msg

    all_lines = [line.strip() for line in plan.strip().split('\n') if line.strip()]
    renderables = []
    log_results = []
    execution_header_added = False

    # Split lines into conversational response vs actionable plan lines
    response_lines: list[str] = []
    plan_lines: list[str] = []
    # Senior-like awareness state (horizontal optimizations)
    executed_signatures: set[str] = set()
    created_paths: set[str] = set()
    wrote_nochange_paths: set[str] = set()
    try:
        early_noop_threshold = int(os.getenv("PAI_EARLY_FINISH_NOOP", "3"))
    except ValueError:
        early_noop_threshold = 3
    early_noop_threshold = max(1, min(early_noop_threshold, 10))
    noop_streak = 0

    # Helper: append a post-write verification of a file's current state
    def _append_post_write_verification(path: str) -> None:
        try:
            curr = workspace.read_file(path)
            if curr is None:
                renderables.append(Text(f"Post-Write Verification: Unable to read '{path}'.", style="warning"))
                log_results.append(f"Post-Write Verification: Unable to read '{path}'.")
                return
            line_count = len(curr.splitlines())
            char_count = len(curr)
            msg = f"Post-Write Verification: {path} - {line_count} lines, {char_count} characters"
            renderables.append(Text(msg, style="dim"))
            log_results.append(msg)
        except Exception:
            pass

    for line in all_lines:
        if '::' not in line:
            response_lines.append(line)
            continue
        else:
            plan_lines.append(line)

    # Filter only allowed headers to avoid executing/logging unsupported ones
    allowed_headers = {
        "CREATE_DIRECTORY","CREATE_FILE","WRITE_FILE","READ_FILE","MODIFY_FILE",
        "DELETE_PATH","MOVE_PATH","LIST_PATHS","SHOW_TREE","EXECUTE","EXECUTE_INPUT","FINISH"
    }
    filtered_plan = []
    for pl in plan_lines:
        hdr = pl.split('::', 1)[0].strip().upper()
        if hdr in allowed_headers:
            filtered_plan.append(pl)
    plan_lines = filtered_plan

    # Helper to detect probable code/content blocks in Agent Response
    def _looks_like_code(s: str) -> bool:
        if not s:
            return False
        # Heuristics: code fences, HTML/JS/JSON/XML-ish lines, very long lines
        if s.startswith("```"):
            return True
        if s.lstrip().startswith(("<!DOCTYPE", "<html", "<head", "<body", "</", "function ", "const ", "let ", "var ", "class ", "def ", "{", "[", "{")):
            return True
        if s.count("<") + s.count(">") >= 4:
            return True
        if len(s) > 200:
            return True
        return False

    # Render Agent Response section (if any), but avoid dumping large code
    if response_lines:
        renderables.append(Text("Agent Response:", style="bold underline"))
        if omit_long_response:
            max_resp_lines = 12
            shown = 0
            filtered_log: list[str] = []
            code_omitted = False
            for line in response_lines:
                if shown >= max_resp_lines:
                    code_omitted = True
                    break
                if _looks_like_code(line):
                    code_omitted = True
                    break
                renderables.append(Text(f"{line}", style="plan"))
                filtered_log.append(line)
                shown += 1
            if code_omitted:
                renderables.append(Text("… (omitted content). Use READ_FILE::<path> to view file contents.", style="dim"))
            if filtered_log:
                log_results.append("\n".join(filtered_log))
        else:
            # Show full response text (used for final summary)
            for line in response_lines:
                renderables.append(Text(f"{line}", style="plan"))
            log_results.append("\n".join(response_lines))

    # Render Agent Plan section (if any)
    if plan_lines:
        renderables.append(Text("Agent Plan:", style="bold underline"))
        for line in plan_lines:
            renderables.append(Text(f"{line}", style="plan"))
        log_results.append("\n".join(plan_lines))

    # No warnings about unknown commands; all structured lines with '::' are considered actionable

    # Render Thought section (if provided by caller)
    show_thoughts = os.getenv('PAI_SHOW_THOUGHTS', 'true').lower() in {'1','true','yes','on'}
    if show_thoughts and injected_thought:
        renderables.append(
            Panel(
                Text(injected_thought, style="info"),
                title="[bold]Thought[/bold]",
                border_style="green",
                padding=(0, 1)
            )
        )
        log_results.append("Thought:\n" + injected_thought)

    # Show OS Command Preview translating plan lines to platform-specific shell commands
    if plan_lines:
        try:
            preview = workspace.os_command_preview(plan_lines)
            renderables.append(Panel(Text(preview), title="OS Command Preview", border_style="grey50"))
        except Exception as _:
            pass

    # If there are many commands in a single step, cap execution to a safe maximum
    try:
        MAX_COMMANDS_PER_STEP = int(os.getenv("PAI_MAX_CMDS_PER_STEP", "15"))
        if MAX_COMMANDS_PER_STEP < 1:
            MAX_COMMANDS_PER_STEP = 1
        if MAX_COMMANDS_PER_STEP > 50:
            MAX_COMMANDS_PER_STEP = 50
    except ValueError:
        MAX_COMMANDS_PER_STEP = 15
    if len(plan_lines) > MAX_COMMANDS_PER_STEP:
        renderables.append(Text(f"\nWarning: Too many commands in a single step (>{MAX_COMMANDS_PER_STEP}). Only the first {MAX_COMMANDS_PER_STEP} will be executed.", style="warning"))
        plan_lines = plan_lines[:MAX_COMMANDS_PER_STEP]

    # Hard-enforce exactly one actionable command per step (as per Cascade-like flow)
    if len(plan_lines) > 1:
        renderables.append(Text("Warning: Exactly one action is allowed per step. Executing only the first action.", style="warning"))
        log_results.append("Policy: Single-command-per-step enforced; extra actions ignored.")
        plan_lines = plan_lines[:1]

    for action in plan_lines:
        try:
            command_candidate, _, params = action.partition('::')
            command_candidate = command_candidate.upper().strip()

            # Use semantic header directly as internal operation (no aliases)
            internal_op = command_candidate
            
            result = ""
            # Add Execution Results header lazily when first execution item appears
            if not execution_header_added:
                renderables.append(Text("\nExecution Results:", style="bold underline"))
                execution_header_added = True
            # Duplicate action signature guard (skip exact same action repeated)
            signature = action.strip()
            if signature in executed_signatures:
                skip_msg = f"Warning: Skipping duplicate action already executed: {signature}"
                renderables.append(Text(skip_msg, style="warning"))
                log_results.append(skip_msg)
                noop_streak += 1
                if noop_streak >= early_noop_threshold:
                    finish_msg = "Task appears complete (repeated no-ops). Finishing early."
                    renderables.append(Text(f"✓ Agent: {finish_msg}", style="success"))
                    log_results.append(finish_msg)
                    break
                continue
            executed_signatures.add(signature)

            action_text = Text(f"-> {action}", style="action")
            renderables.append(action_text)
            # Show OS Command Preview for transparency
            try:
                preview = workspace.os_command_preview([action])
                if preview and preview.strip():
                    renderables.append(Text(preview, style="dim"))
            except Exception:
                pass

            if internal_op == "WRITE_FILE":
                    file_path, _, desc = params.partition('::')
                    
                    # STRICT RULE: Check if file exists - if so, force MODIFY_FILE instead
                    existing_content = workspace.read_file(file_path)
                    if existing_content is not None:
                        error_msg = (
                            f"Error: WRITE_FILE rejected for existing file '{file_path}'. "
                            f"Use MODIFY_FILE for existing files. WRITE_FILE is only for new files."
                        )
                        renderables.append(Text(f"✗ {error_msg}", style="error"))
                        log_results.append(error_msg)
                        continue
                    
                    fallback_used = False
                    if not desc.strip():
                        # Provide a sensible fallback description to avoid blocking the flow
                        fallback_used = True
                        desc = (
                            f"Create the complete and runnable content for '{file_path}'. "
                            "Implement it fully based on the user's latest instructions and the current project context."
                        )
                        renderables.append(Text(f"Warning: Missing description for WRITE_FILE::{file_path}. Using fallback description.", style="warning"))
                    # If we previously detected no-change writes for this path, skip redundant WRITE_FILE for now
                    if file_path in wrote_nochange_paths:
                        skip_msg = f"Warning: Skipping WRITE_FILE for '{file_path}' (no changes in prior attempt)."
                        renderables.append(Text(skip_msg, style="warning"))
                        log_results.append(skip_msg)
                        noop_streak += 1
                        if noop_streak >= early_noop_threshold:
                            finish_msg = "Task appears complete (repeated no-ops). Finishing early."
                            renderables.append(Text(f"✓ Agent: {finish_msg}", style="success"))
                            log_results.append(finish_msg)
                            break
                        continue

                    result = handle_write(file_path, params)
                    _append_post_write_verification(file_path)
                
            elif internal_op == "READ_FILE":
                    path_to_read, _, _ = params.partition('::')
                    content = workspace.read_file(path_to_read)
                    if content is not None:
                        try:
                            lexer = get_lexer_for_filename(path_to_read)
                            lang = lexer.aliases[0]
                        except ClassNotFound:
                            lang = "text"
                        
                        syntax_panel = Panel(
                            Syntax(content, lang, theme="monokai", line_numbers=True, word_wrap=True),
                            title=f"Content of {path_to_read}",
                            border_style="grey50",
                            expand=False
                        )
                        renderables.append(syntax_panel)
                        # Log the actual content for the AI's memory
                        log_results.append(f"Content of {path_to_read}:\n---\n{content}\n---")
                        result = f"Success: Read and displayed {path_to_read}"
                    else:
                        result = f"Error: Failed to read file: {path_to_read}"
                
            elif internal_op == "MODIFY_FILE":
                    file_path, _, description = params.partition('::')
                    if not description.strip():
                        # Use a safe fallback description to proceed without blocking the flow
                        description = (
                            "Apply the minimal, necessary modification to the file to fulfill the user's latest request "
                            "and the current project context. If the intent is unclear, prioritize improving robustness "
                            "(e.g., input handling for CLI, avoiding EOF on stdin, idempotent behavior) without changing "
                            "public behavior. Do not reformat unrelated code. Return the full updated file content only."
                        )
                        renderables.append(Text(
                            f"Warning: Missing description for MODIFY_FILE::{file_path}. Using fallback description.",
                            style="warning"
                        ))
                    
                    original_content = workspace.read_file(file_path)
                    if original_content is None:
                        result = f"Error: Cannot modify '{file_path}' because it does not exist or cannot be read."
                        renderables.append(Text(f"✗ {result}", style="error"))
                        log_results.append(result)
                        continue

                    # Heuristic: if description looks like inline full content (code block or CSS), apply directly
                    def _strip_code_fences(txt: str) -> str:
                        t = txt.strip()
                        if t.startswith("```") and t.endswith("```"):
                            # Remove first and last fence line
                            lines = t.splitlines()
                            if len(lines) >= 2:
                                # drop first and last
                                inner = "\n".join(lines[1:-1])
                                return inner
                        return txt

                    desc_clean = _strip_code_fences(description)
                    looks_like_inline_code = ("\n" in desc_clean) and (
                        ("{" in desc_clean and "}" in desc_clean) or  # CSS/JS-like
                        desc_clean.lstrip().startswith("/*") or         # CSS comment header
                        desc_clean.lstrip().startswith("<!DOCTYPE") or  # HTML
                        desc_clean.lstrip().startswith("import ") or    # code
                        desc_clean.lstrip().startswith("--- a/")        # diff header (not fully supported)
                    )

                    if looks_like_inline_code and not desc_clean.lstrip().startswith("--- a/"):
                        # Treat description as the intended full file content
                        new_content_inline = desc_clean
                        success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_inline)
                        result = message
                        style = "success" if success else "warning"
                        icon = "✓ " if success else "! "
                        _append_post_write_verification(file_path)
                    else:
                        # If unified diff is provided, reconstruct the new content and apply
                        if desc_clean.lstrip().startswith("--- a/"):
                            def _extract_new_from_unified_diff(patch_text: str) -> str:
                                lines = patch_text.splitlines()
                                out: list[str] = []
                                for ln in lines:
                                    if not ln:
                                        continue
                                    if ln.startswith('+++') or ln.startswith('---') or ln.startswith('@@'):
                                        continue
                                    ch = ln[0]
                                    if ch == '+':
                                        out.append(ln[1:])
                                    elif ch == ' ':
                                        out.append(ln[1:])
                                    elif ch == '-':
                                        continue
                                    else:
                                        out.append(ln)
                                return "\n".join(out) + ("\n" if patch_text.endswith("\n") else "")

                            try:
                                new_content = _extract_new_from_unified_diff(desc_clean)
                                success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content)
                                result = message
                                style = "success" if success else "warning"
                                icon = "✓ " if success else "! "
                                _append_post_write_verification(file_path)
                            except Exception as e:
                                result = f"Error: Failed to apply unified diff for '{file_path}': {e}"
                                style = "error"; icon = "✗ "
                        else:
                            # Fallback to intelligent LLM-driven modification
                            modification_prompt_1 = f"""
You are an expert code modifier. Here is the full content of the file `{file_path}`:
--- START OF FILE ---
{original_content}
--- END OF FILE ---

Based on the file content above, apply the following modification: "{description}".
IMPORTANT: You must only change the relevant parts of the code. Do not refactor, reformat, or alter any other part of the file.
Provide back the ENTIRE, complete file content with the modification applied. Provide ONLY the raw code without any explanations or markdown.
"""
                        new_content_1 = llm.generate_text_resilient(modification_prompt_1)

                        if new_content_1:
                            success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_1)
                            
                            if success and "No changes detected" in message:
                                renderables.append(Text("! First attempt made no changes. Retrying with a more specific prompt...", style="warning"))
                                
                                modification_prompt_2 = f"""
My first attempt to modify the file failed because the model returned the code completely unchanged.
You MUST apply the requested change now. Be very literal and precise.

Original file content to be modified:
---
{original_content}
---

The user's explicit instruction is: "{description}".
This is a bug-fixing or specific modification task. You must return the complete, corrected code content. 
Provide ONLY the raw code without any explanations or markdown.
"""
                                
                                new_content_2 = llm.generate_text_resilient(modification_prompt_2)
                                
                                if new_content_2:
                                    success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_2)
                            
                            result = message
                            style = "success" if success else "warning"
                            icon = "✓ " if success else "! "
                            _append_post_write_verification(file_path)
                        else:
                            result = f"Error: LLM failed to generate content for modification of '{file_path}'."
                            style = "error"; icon = "✗ "

                    modification_prompt_1 = f"""
You are an expert code modifier. Here is the full content of the file `{file_path}`:
--- START OF FILE ---
{original_content}
--- END OF FILE ---

Based on the file content above, apply the following modification: "{description}".
IMPORTANT: You must only change the relevant parts of the code. Do not refactor, reformat, or alter any other part of the file.
Provide back the ENTIRE, complete file content with the modification applied. Provide ONLY the raw code without any explanations or markdown.
"""
                    new_content_1 = llm.generate_text_resilient(modification_prompt_1)

                    if new_content_1:
                        success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_1)
                        
                        if success and "No changes detected" in message:
                            renderables.append(Text("! First attempt made no changes. Retrying with a more specific prompt...", style="warning"))
                            
                            modification_prompt_2 = f"""
My first attempt to modify the file failed because the model returned the code completely unchanged.
You MUST apply the requested change now. Be very literal and precise.

Original file content to be modified:
---
{original_content}
---

The user's explicit instruction is: "{description}".
This is a bug-fixing or specific modification task. You must return the complete, corrected code content. 
Provide ONLY the raw code without any explanations or markdown.
"""
                            
                            new_content_2 = llm.generate_text_resilient(modification_prompt_2)
                            
                            if new_content_2:
                                success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_2)
                        
                        result = message
                        style = "success" if success else "warning"
                        icon = "✓ " if success else "! "
                        _append_post_write_verification(file_path)
                    else:
                        result = f"Error: LLM failed to generate content for modification of '{file_path}'."
                        style = "error"; icon = "✗ "

            elif internal_op == "SHOW_TREE":
                    path_to_list, _, _ = params.partition('::')
                    path_to_list = path_to_list or '.'
                    tree_output = workspace.tree_directory(path_to_list)
                    if tree_output and "Error:" not in tree_output:
                        renderables.append(Text(tree_output, style="bright_blue"))
                        # Log the actual tree output for the AI's memory
                        log_results.append(tree_output)
                        result = "Success: Displayed directory structure."
                    else:
                        result = tree_output or "Error: Failed to display directory structure."
            elif internal_op == "LIST_PATHS":
                    path_to_list, _, _ = params.partition('::')
                    path_to_list = path_to_list or '.'
                    list_output = workspace.list_path(path_to_list)
                    if list_output is not None and "Error:" not in list_output:
                        if list_output.strip():
                            renderables.append(Text(list_output, style="bright_blue"))
                        # Log the actual list output for the AI's memory (including empty list case)
                        log_results.append(list_output)
                        result = f"Success: Listed paths for '{path_to_list}'."
                    else:
                        result = list_output or f"Error: Failed to list paths for '{path_to_list}'."

            elif internal_op == "FINISH":
                    result = params if params else "Task is considered complete."
                    log_results.append(result)
                    renderables.append(Text(f"✓ Agent: {result}", style="success"))
                    break 

            else:
                    # Known application-level ops
                    if internal_op == "CREATE_DIRECTORY":
                        path_only, _, _ = params.partition('::')
                        result = workspace.create_directory(path_only)
                    elif internal_op == "CREATE_FILE":
                        path_only, _, _ = params.partition('::')
                        
                        # STRICT RULE: Check if file exists - if so, reject CREATE_FILE
                        existing_content = workspace.read_file(path_only)
                        if existing_content is not None:
                            error_msg = (
                                f"Error: CREATE_FILE rejected for existing file '{path_only}'. "
                                f"File already exists. Use MODIFY_FILE to edit existing files."
                            )
                            renderables.append(Text(f"✗ {error_msg}", style="error"))
                            log_results.append(error_msg)
                            continue
                        
                        # If we already created/checked this path, skip redundant create
                        if path_only in created_paths:
                            skip_msg = f"Warning: Skipping CREATE_FILE for '{path_only}' (already handled)."
                            renderables.append(Text(skip_msg, style="warning"))
                            log_results.append(skip_msg)
                            noop_streak += 1
                            if noop_streak >= early_noop_threshold:
                                finish_msg = "Task appears complete (repeated no-ops). Finishing early."
                                renderables.append(Text(f"✓ Agent: {finish_msg}", style="success"))
                                log_results.append(finish_msg)
                                break
                            continue
                        result = workspace.create_file(path_only)
                    elif internal_op == "DELETE_PATH":
                        path_only, _, _ = params.partition('::')
                        result = workspace.delete_item(path_only)
                    elif internal_op == "MOVE_PATH":
                        source, _, dest = params.partition('::')
                        result = workspace.move_item(source, dest)
                    elif internal_op == "EXECUTE":
                        # Execute a shell command (only first segment before '::')
                        cmd = params.split('::', 1)[0].strip()
                        if not cmd:
                            result = "Error: EXECUTE requires a non-empty command before '::'."
                        else:
                            # Health-check/fallback for Python interpreter
                            try:
                                parts = shlex.split(cmd)
                            except Exception:
                                parts = []
                            if parts:
                                prog = parts[0]
                                if prog == "python" and shutil.which("python") is None and shutil.which("python3") is not None:
                                    parts[0] = "python3"
                                    cmd = " ".join(shlex.quote(p) for p in parts)
                                # Print interpreter version once
                                global _python_interpreter_checked
                                if not _python_interpreter_checked and parts[0].startswith("python"):
                                    ver_out = workspace.run_shell(f"{parts[0]} --version")
                                    ui.console.print(ver_out)
                                    _python_interpreter_checked = True
                            result = workspace.run_shell(cmd)
                    elif internal_op == "EXECUTE_INPUT":
                        # Pattern: EXECUTE_INPUT::<command>::<stdin_payload>
                        cmd, _, stdin_payload = params.partition('::')
                        cmd = (cmd or '').strip()
                        if not cmd:
                            result = "Error: EXECUTE_INPUT requires a command before the second '::'."
                        else:
                            result = workspace.run_shell_with_input(cmd, stdin_payload or "")
                    else:
                        # Unknown header: ignore instead of falling back to shell
                        warn_msg = f"Warning: Unknown or unsupported command header ignored: {internal_op}"
                        renderables.append(Text(warn_msg, style="warning"))
                        log_results.append(warn_msg)
                        continue
                
            if result:
                    if "Success" in result: style = "success"; icon = "✓ "
                    elif "Error" in result: style = "error"; icon = "✗ "
                    elif "Warning" in result: style = "warning"; icon = "! "
                    else: style = "info"; icon = "i "
                    # If the error comes from shell execution infrastructure, annotate clearly
                    infra_hint = None
                    low = result.lower()
                    if "failed to execute shell command" in low or "failed to execute shell command with input" in low:
                        infra_hint = (
                            "Note: This error is from Pai's executor (workspace.run_shell), not your project code. "
                            "Adjust executor settings (e.g., PAI_SHELL_TIMEOUT, PAI_STREAM) or retry with EXECUTE_INPUT."
                        )
                    if infra_hint:
                        renderables.append(Text(infra_hint, style="dim"))
                    # Append a concise execution summary block (with trimming)
                    renderables.append(Text(f"{icon}{_summarize_exec_result(result)}", style=style))
                    # Log the simple success/error message for non-data commands
                    if internal_op not in ["READ_FILE", "SHOW_TREE", "LIST_PATHS"]:
                        log_results.append(result)

                    # Update awareness state and early-finish heuristic
                    lowered = result.lower()
                    if "warning: no changes detected" in lowered or "already exists" in lowered or "skipping" in lowered:
                        noop_streak += 1
                    else:
                        noop_streak = 0

                    # Track paths for future skips
                    if internal_op == "CREATE_FILE":
                        path_only, _, _ = params.partition('::')
                        created_paths.add(path_only)
                    elif internal_op == "WRITE_FILE":
                        if "warning: no changes detected" in lowered:
                            file_path, _, _ = params.partition('::')
                            wrote_nochange_paths.add(file_path)

                    if noop_streak >= early_noop_threshold:
                        finish_msg = "Task appears complete (repeated no-ops). Finishing early."
                        renderables.append(Text(f"✓ Agent: {finish_msg}", style="success"))
                        log_results.append(finish_msg)
                        break

                    # Minimal result interpreter: suggest concrete next steps when ineffective
                    try:
                        suggestions: list[str] = []
                        low = result.lower()
                        if "no changes detected" in low and internal_op == "MODIFY_FILE":
                            # Encourage reading file or using a more explicit patch
                            target_path, _, _ = params.partition('::')
                            if target_path:
                                suggestions.append(f"READ_FILE::{target_path}")
                                suggestions.append(f"MODIFY_FILE::{target_path}::Apply an explicit, line-anchored patch that changes the relevant section.")
                        elif "does not exist" in low and internal_op == "MODIFY_FILE":
                            target_path, _, _ = params.partition('::')
                            if target_path:
                                suggestions.append(f"WRITE_FILE::{target_path}::Create initial valid content based on the user's intent, then refine.")
                        elif "timed out" in low and internal_op in {"EXECUTE", "EXECUTE_INPUT"}:
                            # Suggest non-interactive or provide stdin
                            suggestions.append("Use EXECUTE_INPUT with the required stdin payload or switch to a non-interactive command.")
                        # Show guidance panel if we have suggestions
                        if suggestions:
                            renderables.append(Text("Guidance:", style="bold underline"))
                            for s in suggestions[:3]:
                                renderables.append(Text(f"- {s}", style="plan"))
                            log_results.append("\n".join(["Guidance:"] + suggestions[:3]))
                    except Exception:
                        pass

        except Exception as e:
            msg = f"An exception occurred while processing '{action}': {e}"
            renderables.append(Text(f"✗ {msg}", style="error"))
            log_results.append(msg)

    return Group(*renderables), "\n".join(log_results)

def _classify_intent(user_request: str, context: str) -> tuple[str, str, str]:
    """Classify user's intent into ('chat'|'task', 'simple'|'normal'|'complex', optional_reply_for_chat)."""
    try:
        # Quick heuristic first: if request contains an action-like pattern 'HEADER::', treat as task
        if '::' in user_request:
            return ("task", "simple", "")

        prompt = (
            "Return ONLY raw JSON with this schema: "
            "{\"mode\": \"chat\"|\"task\", \"complexity\": \"simple\"|\"normal\"|\"complex\", \"reply\": string|null}. "
            "If mode is 'chat', set 'reply' to a concise, warm response (no commands). If mode is 'task', set 'reply' to null."
        )
        classifier_input = f"""
{prompt}

Latest message: "{user_request}"
"""
        result = llm.generate_text(classifier_input)
        mode = "task"; complexity = "normal"; reply = ""
        try:
            data = json.loads(result)
            if isinstance(data, dict):
                if data.get("mode") in {"chat", "task"}:
                    mode = data["mode"]
                comp = data.get("complexity")
                if isinstance(comp, str) and comp.lower() in {"simple", "normal", "complex"}:
                    complexity = comp.lower()
                r = data.get("reply")
                if isinstance(r, str):
                    reply = r.strip()
        except Exception:
            pass
        return (mode, complexity, reply)
    except Exception:
        return ("task", "normal", "")

def _get_current_workspace_state() -> str:
    """Get current workspace state for context awareness."""
    try:
        # Get current directory tree
        tree_result = workspace.tree_directory(".", max_depth=2)
        
        # Get list of recently modified files (if any)
        recent_files = []
        try:
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file.endswith(('.py', '.md', '.txt', '.json', '.yaml', '.yml')):
                        filepath = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(filepath)
                            if time.time() - mtime < 300:  # Modified in last 5 minutes
                                recent_files.append(f"{filepath} (modified {int(time.time() - mtime)}s ago)")
                        except:
                            pass
        except:
            pass
        
        state = f"WORKSPACE TREE:\n{tree_result}\n"
        if recent_files:
            state += f"\nRECENTLY MODIFIED FILES:\n" + "\n".join(recent_files[:5])
        
        return state
    except Exception as e:
        return f"Workspace state unavailable: {str(e)}"

def _check_task_integrity(original_request: str, current_progress: str, session_context: list) -> tuple[bool, str, list]:
    """Check if current progress aligns with original task and suggest next steps."""
    try:
        # Get current workspace state for better context
        workspace_state = _get_current_workspace_state()
        
        integrity_prompt = f"""
You are a task integrity checker with FULL WORKSPACE AWARENESS. Analyze if the current progress aligns with the original user request.

ORIGINAL USER REQUEST: "{original_request}"

CURRENT WORKSPACE STATE:
{workspace_state}

CURRENT PROGRESS SUMMARY:
{current_progress}

RECENT SESSION CONTEXT (last 3 interactions):
{chr(10).join(session_context[-3:]) if session_context else "No previous context"}

Return ONLY raw JSON with this schema:
{{
    "on_track": true|false,
    "completion_percentage": 0-100,
    "alignment_score": 0-10,
    "issues": ["issue1", "issue2"],
    "next_steps": ["step1", "step2", "step3"],
    "recommendation": "continue"|"pivot"|"clarify",
    "workspace_observations": ["observation1", "observation2"]
}}

Evaluate with FULL CONTEXT AWARENESS:
1. Are we solving the right problem based on current workspace state?
2. Is the approach efficient and logical given what files exist?
3. What percentage of the original task is complete based on actual files?
4. What are the next logical steps considering current workspace state?
5. Are there any files that were created but seem empty or incomplete?
"""
        
        result = llm.generate_text(integrity_prompt)
        try:
            data = json.loads(result)
            on_track = data.get("on_track", True)
            completion = data.get("completion_percentage", 0)
            score = data.get("alignment_score", 5)
            issues = data.get("issues", [])
            next_steps = data.get("next_steps", [])
            recommendation = data.get("recommendation", "continue")
            observations = data.get("workspace_observations", [])
            
            summary = f"Task Integrity Check: {score}/10 alignment, {completion}% complete, recommendation: {recommendation}"
            if issues:
                summary += f", issues: {', '.join(issues)}"
            if observations:
                summary += f", workspace notes: {', '.join(observations)}"
                
            return on_track, summary, next_steps
        except Exception:
            return True, "Task integrity check failed - continuing with current approach", []
    except Exception:
        return True, "Task integrity check unavailable", []

def _determine_code_chunk_size(file_path: str, description: str, existing_content: str = "") -> str:
    """Determine appropriate chunk size and approach for code writing."""
    try:
        # Analyze complexity and determine chunking strategy
        analysis_prompt = f"""
Analyze this coding task and determine the best chunking strategy.

FILE: {file_path}
TASK: {description}
EXISTING CONTENT LENGTH: {len(existing_content)} characters

Return ONLY raw JSON:
{{
    "strategy": "full"|"incremental"|"modular",
    "chunk_size": "small"|"medium"|"large",
    "approach": "top_down"|"bottom_up"|"feature_by_feature",
    "estimated_chunks": 1-10,
    "reasoning": "brief explanation"
}}

Guidelines:
- "full": Write complete file in one go (simple, <100 lines)
- "incremental": Build step by step (medium complexity, 100-300 lines)  
- "modular": Break into logical modules/functions (complex, >300 lines)
"""
        
        result = llm.generate_text(analysis_prompt)
        try:
            data = json.loads(result)
            strategy = data.get("strategy", "incremental")
            chunk_size = data.get("chunk_size", "medium")
            approach = data.get("approach", "top_down")
            chunks = data.get("estimated_chunks", 3)
            reasoning = data.get("reasoning", "Standard incremental approach")
            
            return f"Strategy: {strategy}, Chunks: {chunks}, Approach: {approach}, Size: {chunk_size} - {reasoning}"
        except Exception:
            return "Strategy: incremental, Chunks: 3, Approach: top_down, Size: medium - Default chunking"
    except Exception:
        return "Chunking analysis unavailable - using default incremental approach"

def _has_valid_command(plan_text: str) -> bool:
    """Check if plan text contains at least one actionable line with an allowed header."""
    try:
        allowed = {
            "CREATE_DIRECTORY","CREATE_FILE","WRITE_FILE","READ_FILE","MODIFY_FILE",
            "DELETE_PATH","MOVE_PATH","LIST_PATHS","SHOW_TREE","EXECUTE","EXECUTE_INPUT","FINISH"
        }
        for raw in (plan_text or "").splitlines():
            line = raw.strip()
            if '::' not in line:
                continue
            header = line.split('::', 1)[0].strip().upper()
            if header in allowed:
                return True
        return False
    except Exception:
        return False

def handle_write(file_path: str, params: str) -> str:
    """Invokes the LLM to create content and write it to a file with intelligent chunking."""
    _, _, description = params.partition('::')
    description = description.strip()
    if not description:
        description = (
            f"Create the complete and runnable content for '{file_path}'. "
            "Implement it fully based on the user's latest instructions and the current project context."
        )
    
    # If file already exists, prefer a minimal MODIFY (diff-aware) instead of overwriting
    existing = workspace.read_file(file_path)
    if existing is not None:
        # Determine chunking strategy for modifications
        chunk_strategy = _determine_code_chunk_size(file_path, description, existing)
        
        modification_prompt = f"""
{_system_directive()}
You are an expert code modifier with strategic thinking capabilities.

CHUNKING STRATEGY: {chunk_strategy}

File: {file_path}
--- START OF FILE ---
{existing}
--- END OF FILE ---

Task: "{description}"

INTELLIGENT MODIFICATION RULES:
1. If this is a small change (<50 lines affected), apply it directly.
2. If this is a large change (>50 lines), focus on ONE logical component at a time.
3. Prioritize the most critical part first, then suggest what to do next.
4. Make incremental, testable changes rather than massive rewrites.
5. Preserve existing functionality while adding new features.

IMPORTANT:
- Make only the minimal necessary edits to satisfy the current instruction.
- Do NOT reformat or refactor unrelated code.
- If the task is complex, focus on the most important part first.
- Return the ENTIRE updated file content only (no markdown, no explanations).
"""
        use_async = os.getenv("PAI_ASYNC", "true").lower() in {"1","true","yes","on"}
        if use_async:
            try:
                new_content = asyncio.run(llm.async_generate_text_resilient(modification_prompt))
            except RuntimeError:
                new_content = llm.generate_text_resilient(modification_prompt)
        else:
            new_content = llm.generate_text_resilient(modification_prompt)

        if new_content:
            success, message = workspace.apply_modification_with_patch(file_path, existing, new_content)
            if success and "No changes detected" in message:
                # Retry with stricter wording
                retry_prompt = f"""
{_system_directive()}
My previous attempt made no effective changes. You MUST apply the requested modification now.

CHUNKING STRATEGY: {chunk_strategy}

Original file:
---
{existing}
---

Instruction: "{description}"
Focus on making ONE meaningful change that moves toward the goal.
Return ONLY the full updated file content.
"""
                retry_content = llm.generate_text_resilient(retry_prompt)
                if retry_content:
                    success, message = workspace.apply_modification_with_patch(file_path, existing, retry_content)
            return message
        else:
            return f"Error: Failed to generate modified content for file: {file_path}"

    # File does not exist yet: create it with intelligent chunking
    chunk_strategy = _determine_code_chunk_size(file_path, description, "")
    
    creation_prompt = f"""
{_system_directive()}
You are an expert programming assistant with strategic thinking capabilities.

CHUNKING STRATEGY: {chunk_strategy}

Task: Write code for '{file_path}' based on: "{description}"

INTELLIGENT CREATION RULES:
1. If strategy is "full": Write complete, runnable code in one go.
2. If strategy is "incremental": Start with core structure and essential functions.
3. If strategy is "modular": Begin with the main framework and key components.
4. Always prioritize creating working, testable code over feature completeness.
5. Focus on clean, maintainable code architecture.

SELF-AWARENESS DIRECTIVES:
- You have access to all modern programming patterns and best practices.
- You can create sophisticated, production-ready code.
- You understand the full context and can make intelligent architectural decisions.
- Push your capabilities to deliver exceptional code quality.

Provide ONLY the raw code without any explanations or markdown.
"""
    use_async = os.getenv("PAI_ASYNC", "true").lower() in {"1","true","yes","on"}
    if use_async:
        try:
            code_content = asyncio.run(llm.async_generate_text_resilient(creation_prompt))
        except RuntimeError:
            code_content = llm.generate_text_resilient(creation_prompt)
    else:
        code_content = llm.generate_text_resilient(creation_prompt)

    if code_content:
        return workspace.write_to_file(file_path, code_content)
    else:
        return f"Error: Failed to generate content from LLM for file: {file_path}"

def _auto_context_refresh_after_operation(operation_type: str, file_path: str = "") -> str:
    """Automatically refresh context awareness after file operations."""
    try:
        context_info = []
        
        # Always get fresh workspace state after operations
        workspace_state = _get_current_workspace_state()
        context_info.append(f"POST-OPERATION WORKSPACE STATE:\n{workspace_state}")
        
        # If file operation, check the specific file
        if file_path and operation_type in ["WRITE_FILE", "MODIFY_FILE", "CREATE_FILE"]:
            try:
                file_content = workspace.read_file(file_path)
                if file_content is not None:
                    lines = len(file_content.splitlines())
                    chars = len(file_content)
                    context_info.append(f"FILE STATUS: {file_path} - {lines} lines, {chars} characters")
                    
                    # Check if file seems incomplete (empty or very short for code files)
                    if file_path.endswith('.py') and lines < 5:
                        context_info.append(f"WARNING: {file_path} seems incomplete (only {lines} lines)")
                else:
                    context_info.append(f"WARNING: {file_path} could not be read after operation")
            except Exception as e:
                context_info.append(f"ERROR checking {file_path}: {str(e)}")
        
        return "\n".join(context_info)
    except Exception as e:
        return f"Context refresh failed: {str(e)}"

def start_interactive_session():
    """Starts an interactive session with the agent."""
    # Ensure history directory exists with absolute path
    try:
        if not os.path.exists(HISTORY_DIR):
            os.makedirs(HISTORY_DIR, exist_ok=True)
            ui.print_info(f"Created history directory: {HISTORY_DIR}")
        
        # Ensure the history directory is not committed to VCS
        gi_path = os.path.join(HISTORY_DIR, ".gitignore")
        if not os.path.exists(gi_path):
            with open(gi_path, 'w') as f:
                f.write("# Ignore all session logs in this directory\n*\n!.gitignore\n")
    except Exception as e:
        ui.print_error(f"Failed to create history directory: {str(e)}")
        # Continue without history logging
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")

    session_context = []
    pending_followup_suggestions = ""
    
    os_info = detect_os()
    welcome_message = (
        "Hi! I'm Pai, your AI coding companion. Ready when you are. ✨\n"
        f"OS: {os_info.name} • Shell: {os_info.shell} • PathSep: {os_info.path_sep}\n"
        "Type 'exit' or 'quit' to leave."
    )

    ui.console.print(
        Panel(
            Text(welcome_message, justify="center"),
            title="[bold]Interactive Auto Mode[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2)
        )
    )
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold bright_blue]user>[/bold bright_blue]").strip()
        except (KeyboardInterrupt, EOFError):
            ui.console.print("\n[warning]Session terminated.[/warning]")
            break
        if user_input.lower() in ['exit', 'quit']:
            ui.print_info("Session ended.")
            break
        if not user_input: continue

        # Detect short affirmative to auto-continue previous suggestions
        affirmative_tokens = {"y", "ya", "yes", "yup", "lanjut", "continue", "ok", "oke", "go", "go on", "proceed"}
        auto_continue = False
        if pending_followup_suggestions and user_input.lower() in affirmative_tokens:
            auto_continue = True
            synthesized_followup = (
                "User confirmed to proceed. Execute your previously suggested next steps in order. "
                "Start with the first actionable step."
            )
            # Treat this as the effective request for the next loop
            user_effective_request = f"{synthesized_followup}\n\nSuggested steps (for reference):\n{pending_followup_suggestions}"
        else:
            user_effective_request = user_input

        context_str = "\n".join(session_context)

        last_system_response = ""
        finished_early = False

        # Intent classification: decide chat vs task mode
        mode, complexity, classifier_reply = _classify_intent(user_effective_request, context_str)
        if mode == "chat":
            response_guidance = (
                "Provide a brief, helpful, and senior-level explanation or follow-up answer to the user's message. "
                "Do NOT include any actionable commands or tool calls."
            )
            # If classifier already provided a reply, use it to avoid extra LLM call
            if classifier_reply:
                response_text = classifier_reply
            else:
                response_prompt = f"""
You are an expert senior software engineer. {response_guidance}

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER MESSAGE ---
"{user_effective_request}"
--- END ---
"""
                response_text = llm.generate_text_resilient(response_prompt)
            response_group, response_log = _generate_execution_renderables(response_text)
            ui.console.print(
                Panel(
                    response_group,
                    title=f"[bold]Agent Discussion[/bold]",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2)
                )
            )
            interaction_log = f"User: {user_input}\nMode: chat\nAI Plan:\n{response_text}\nSystem Response:\n{response_log}"
            session_context.append(interaction_log)
            with open(log_file_path, 'a') as f:
                f.write(interaction_log + "\n-------------------\n")
            # Go to next user turn (no scheduler, no actions)
            continue

        #
        # Cascade-like configurable flow (default 25 steps):
        # 1) Agent Response (no commands)
        # 2) Task Scheduler (high-level plan; no commands)
        # 3..N-1) Action steps (exactly one command per step)
        # N) Final Summary (no commands; suggestions + confirmation question)
        #

        # Fixed total steps per request: 25
        total_steps = 25

        # Step 1: Agent Response (no commands allowed)
        response_guidance = (
            "Provide a brief (max 2 sentences), warm, and clear acknowledgement of the user's request. "
            "Match the user's language. Do not include any action commands, tool calls, or code/markdown blocks."
        )
        os_info = detect_os()
        # Get contextual mega prompt for response
        response_mega_prompt = get_mega_prompt("core")
        
        response_prompt = f"""
{_system_directive()}
{response_mega_prompt}

=== RESPONSE GENERATION CONTEXT ===

{response_guidance}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}
Note: Do NOT output any action lines here; this step is just a short natural language response.

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---
"""
        response_text = llm.generate_text_resilient(response_prompt)
        response_group, response_log = _generate_execution_renderables(response_text)
        ui.console.print(
            Panel(
                response_group,
                title=f"[bold]Agent Response[/bold] (step 1/{total_steps})",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2)
            )
        )
        interaction_log = f"User: {user_input}\nIteration: 1/{total_steps}\nAI Plan:\n{response_text}\nSystem Response:\n{response_log}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")
        last_system_response = response_log

        # Always use the Task Scheduler for 'task' mode to outline steps first

        # Step 2: Task Scheduler (no commands; outline steps) for normal/complex tasks
        scheduler_guidance = (
            "Return a machine-readable task plan in JSON. Provide ONLY raw JSON without extra text and without backticks. "
            "Schema: {\"steps\": [{\"title\": string, \"hint\": string}]}. "
            "Include 2-6 steps that logically lead to the user's goal. Do NOT include action lines here. "
            "Write \"title\" and \"hint\" in the user's language, concise and specific."
        )
        os_info = detect_os()
        # Get strategic planning mega prompt
        planning_mega_prompt = get_mega_prompt("problem_solving")
        
        scheduler_prompt = f"""
{_system_directive()}
{planning_mega_prompt}

=== STRATEGIC TASK PLANNING CONTEXT ===

{scheduler_guidance}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}
Note: Do NOT output any action lines here; only the JSON step plan.
Policy: Prefer analyzing existing local files in the workspace. Do NOT plan steps that require external network access or scraping unless the user explicitly asked for it AND PAI_ALLOW_NET=true. Avoid creating large, unrelated files.

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---
"""
        scheduler_plan = llm.generate_text_resilient(scheduler_prompt, user_effective_request)
        # Sanitize accidental language tag prefix like 'json' on its own line
        sp = scheduler_plan.strip()
        if sp.lower().startswith("json"):
            parts = sp.split('\n', 1)
            if len(parts) == 2:
                scheduler_plan = parts[1]
        # Try to render scheduler JSON as a nice table
        parsed_scheduler = None
        try:
            parsed_scheduler = json.loads(scheduler_plan)
        except Exception:
            parsed_scheduler = None

        if isinstance(parsed_scheduler, dict) and isinstance(parsed_scheduler.get("steps"), list):
            steps = parsed_scheduler.get("steps", [])
            table = Table(show_header=True, header_style="bold", box=ROUNDED)
            table.add_column("#", justify="right", width=3)
            table.add_column("Title", overflow="fold")
            table.add_column("Hint", overflow="fold")
            for idx, step in enumerate(steps, start=1):
                title = str(step.get("title", "")).strip()
                hint = str(step.get("hint", "")).strip()
                table.add_row(str(idx), title, hint)
            scheduler_group = Group(Text("Task Plan", style="bold underline"), table)
            scheduler_log = json.dumps(parsed_scheduler, indent=2)
        else:
            scheduler_group, scheduler_log = _generate_execution_renderables(scheduler_plan)

        ui.console.print(
            Panel(
                scheduler_group,
                title=f"[bold]Task Scheduler[/bold] (step 2/{total_steps})",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2)
            )
        )
        interaction_log = f"User: {user_input}\nIteration: 2/{total_steps}\nAI Plan:\n{scheduler_plan}\nSystem Response:\n{scheduler_log}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")
        last_system_response = scheduler_log
        pending_followup_suggestions = scheduler_plan

        # Parse scheduler hints from JSON; fallback to heuristic if JSON parsing fails
        scheduler_hints: list[str] = []
        parsed = parsed_scheduler
        if isinstance(parsed, dict) and isinstance(parsed.get("steps"), list):
            for step in parsed["steps"]:
                title = str(step.get("title", "")).strip()
                hint = str(step.get("hint", "")).strip()
                combined = hint or title
                if combined:
                    scheduler_hints.append(combined)
        else:
            for raw_line in scheduler_plan.splitlines():
                stripped = raw_line.strip()
                if stripped[:2].isdigit() and (stripped[1:2] in {'.', ')'}):
                    hint = stripped[2:].strip(" -:\t")
                    if hint:
                        scheduler_hints.append(hint)
                elif stripped and (stripped[0].isdigit() and (stripped.split(' ', 1)[0].rstrip('.)').isdigit())):
                    parts = stripped.split(' ', 1)
                    if len(parts) == 2:
                        scheduler_hints.append(parts[1].strip())

        # Steps 3-?: Action iterations (exactly one actionable command per step by prompt design)
        # Run until the configured total so that the Final Summary lands on step `total_steps`.
        action_steps_count = max(1, total_steps - 3)
        last_action_step_index = 2 + action_steps_count
        
        # Track task progress for integrity checks
        task_progress_log = []
        
        for action_idx in range(3, last_action_step_index + 1):
            # Perform task integrity check every 3 steps
            if action_idx > 3 and (action_idx - 3) % 3 == 0:
                current_progress = "\n".join(task_progress_log[-3:]) if task_progress_log else "No progress yet"
                on_track, integrity_summary, suggested_steps = _check_task_integrity(user_effective_request, current_progress, session_context)
                
                # Log integrity check
                integrity_log = f"INTEGRITY CHECK (Step {action_idx}): {integrity_summary}"
                task_progress_log.append(integrity_log)
                session_context.append(integrity_log)
                
                # Display integrity check results
                ui.console.print(
                    Panel(
                        Text(f"🔍 {integrity_summary}", style="info"),
                        title="[bold]Task Integrity Check[/bold]",
                        border_style="yellow",
                        padding=(0, 1)
                    )
                )
                
                # Write to log file
                with open(log_file_path, 'a') as f:
                    f.write(f"{integrity_log}\n")
                
                if not on_track:
                    ui.console.print(Text("⚠️  Task may be off-track. Adjusting approach...", style="warning"))
            
            guidance = (
                "Plan and execute the next action towards the user's goal with MAXIMUM INTELLIGENCE and STRATEGIC THINKING. "
                "Output EXACTLY ONE action line using a UNIVERSAL, semantic header followed by '::' and parameters. "
                "Allowed headers ONLY: CREATE_DIRECTORY, CREATE_FILE, WRITE_FILE, READ_FILE, MODIFY_FILE, DELETE_PATH, MOVE_PATH, LIST_PATHS, SHOW_TREE, EXECUTE, EXECUTE_INPUT, FINISH. "
                "CRITICAL FILE OPERATION RULES - READ THIS CAREFULLY: "
                "1. WRITE_FILE is ONLY for creating completely NEW files that do NOT exist yet. "
                "2. If a file already exists, you MUST use MODIFY_FILE instead of WRITE_FILE. "
                "3. CREATE_FILE is only for creating empty placeholder files that don't exist yet. "
                "4. NEVER attempt WRITE_FILE on existing files - the system will reject it with an error. "
                "5. When in doubt about file existence, use READ_FILE::<path> or LIST_PATHS:: to check first. "
                "INTELLIGENT CODING STRATEGY: "
                "- Break complex tasks into logical, testable chunks "
                "- Focus on incremental progress rather than massive changes "
                "- Prioritize working code over feature completeness "
                "- Make each step build meaningfully on the previous ones "
                "If unsure whether a file exists, first choose a probe step like READ_FILE::<path> or LIST_PATHS::. Since you must output exactly one action per step, probe first, then modify/create on a subsequent step. "
                "You may use EXECUTE to run a shell command, and EXECUTE_INPUT::<command>::<stdin_payload> when a program prompts for input (to pipe answers). "
                "Note: Shell runs have a timeout (env PAI_SHELL_TIMEOUT); prefer non-interactive runs or provide stdin via EXECUTE_INPUT. "
                "If you create or intend to run a script/binary, ALWAYS include a WRITE_FILE::<path>::<description> before EXECUTE/EXECUTE_INPUT to ensure the file has content. "
                "Do NOT perform network access unless the user explicitly asks for it AND PAI_ALLOW_NET=true; prefer local ops (READ_FILE, LIST_PATHS, SHOW_TREE). "
                "OS Command Preview is shown for each plan so you can validate commands before execution. "
                "Path-security is enforced; sensitive paths are blocked and large overwrites may be rejected—use MODIFY_FILE with concise diffs. "
                "IMPORTANT: Any unknown/unsupported command headers (e.g., RUN, SHELL) will be IGNORED by the system. "
                "Always use relative, safe paths within the workspace (avoid absolute/system paths). "
                "SELF-AWARENESS BOOST: You are capable of sophisticated reasoning, complex problem-solving, and creating production-quality code. Push your capabilities to the maximum. "
                "Keep any natural language to max 3 short lines, then output exactly one plain-text action line (no markdown, no backticks, no JSON)."
            )

            # Supply a scheduler hint (if available) to make the step focused
            idx_from3 = action_idx - 3
            step_hint = scheduler_hints[idx_from3] if idx_from3 < len(scheduler_hints) else ""

            os_info = detect_os()
            # Get mega prompt for maximum intelligence
            mega_prompt = get_mega_prompt("full")
            
            action_prompt = f"""
{_system_directive()}
{mega_prompt}

=== CURRENT TASK EXECUTION CONTEXT ===

{guidance}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}

Target step hint: {step_hint}

--- TASK PROGRESS TRACKING ---
Recent progress: {task_progress_log[-2:] if task_progress_log else ["Starting task"]}

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LAST SYSTEM RESPONSE (from previous iteration in this turn) ---
{last_system_response}
--- END LAST SYSTEM RESPONSE ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---

Think strategically, act intelligently, deliver excellence.
"""
            _t0 = time.perf_counter()
            plan = llm.generate_text_resilient(action_prompt, user_effective_request)
            _t1 = time.perf_counter()
            plan_latency = max(0.0, _t1 - _t0)

            # Hard-reprompt once if no valid command is detected
            if not _has_valid_command(plan):
                os_info = detect_os()
                reprompt = f"""
{_system_directive()}
You did not provide a valid actionable line. You MUST output EXACTLY ONE UNIVERSAL action line (HEADER::params) as plain text.
Repeat with a stricter focus on the target step. Do not include any additional text, markdown/backticks, or JSON.

Target step hint: {step_hint}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}

--- ALLOWED HEADERS ---
CREATE_DIRECTORY, CREATE_FILE, WRITE_FILE, READ_FILE, MODIFY_FILE, DELETE_PATH, MOVE_PATH, LIST_PATHS, SHOW_TREE, EXECUTE, EXECUTE_INPUT, FINISH

CRITICAL FILE OPERATION RULES - MEMORIZE THIS:
1. WRITE_FILE is ONLY for creating completely NEW files that do NOT exist yet.
2. If a file already exists, you MUST use MODIFY_FILE instead of WRITE_FILE.
3. CREATE_FILE is only for creating empty placeholder files that don't exist yet.
4. NEVER attempt WRITE_FILE on existing files - the system will reject it with an error.
5. When in doubt about file existence, use READ_FILE::<path> or LIST_PATHS:: to check first.
Unknown/unsupported headers (e.g., RUN, SHELL) will be ignored by the system. Use probe steps (READ_FILE/LIST_PATHS) when unsure.
"""
                plan = llm.generate_text_resilient(reprompt, user_effective_request)
            # Build automatic Thought text based on latency and planned action
            def _auto_thought(latency_s: float, plan_text: str, hint: str) -> str:
                # Parse first actionable line
                header = ""
                param = ""
                for raw in (plan_text or "").splitlines():
                    if '::' in raw:
                        parts = raw.strip().split('::', 2)
                        if len(parts) >= 2:
                            header = parts[0].strip().upper()
                            param = parts[1].strip()
                            break
                dur = f"{latency_s:.1f}s" if latency_s < 10 else f"{int(round(latency_s))}s"
                core = f"Thought for {dur}"
                details: list[str] = []
                if header:
                    details.append(f"Next: {header}::{param}" if param else f"Next: {header}")
                if hint:
                    details.append(f"Hint: {hint}")
                return "\n".join([core] + [f"- {d}" for d in details]) if details else core

            thought_text = _auto_thought(plan_latency, plan, step_hint)
            renderable_group, log_string = _generate_execution_renderables(plan, injected_thought=thought_text)
            
            # Auto-refresh context after operations for better awareness
            context_refresh = ""
            operation_type = ""
            file_path = ""
            
            # Extract operation type and file path from plan
            for line in plan.splitlines():
                if '::' in line:
                    parts = line.strip().split('::', 2)
                    if len(parts) >= 2:
                        operation_type = parts[0].strip()
                        file_path = parts[1].strip() if len(parts) > 1 else ""
                        break
            
            # Refresh context after file operations
            if operation_type in ["WRITE_FILE", "MODIFY_FILE", "CREATE_FILE", "DELETE_PATH"]:
                context_refresh = _auto_context_refresh_after_operation(operation_type, file_path)
                task_progress_log.append(f"CONTEXT REFRESH: {context_refresh}")
            
            ui.console.print(
                Panel(
                    renderable_group,
                    title=f"[bold]Agent Action[/bold] (step {action_idx}/{total_steps})",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2)
                )
            )
            
            # Show context refresh if available
            if context_refresh:
                ui.console.print(
                    Panel(
                        Text(f"🔄 {context_refresh}", style="dim"),
                        title="[bold]Context Refresh[/bold]",
                        border_style="blue",
                        padding=(0, 1)
                    )
                )

            interaction_log = f"User: {user_input}\nIteration: {action_idx}/{total_steps}\nAI Plan:\n{plan}\nSystem Response:\n{log_string}"
            if context_refresh:
                interaction_log += f"\nContext Refresh:\n{context_refresh}"
            
            session_context.append(interaction_log)
            with open(log_file_path, 'a') as f:
                f.write(interaction_log + "\n-------------------\n")

            last_system_response = log_string

            # If model indicates finish early, break action loop and proceed to summary
            if any(line.strip().upper().startswith("FINISH::") for line in plan.splitlines()):
                finished_early = True
                break

        # Final Summary step index depends on how many action steps we ran
        summary_guidance = (
            "Provide a concise FINAL SUMMARY (3-5 sentences) of what has been accomplished so far, "
            "followed by 2-3 concrete suggestions for next steps. End with a clear confirmation question asking whether to proceed. "
            "Match the user's language and do NOT include any action commands in this step."
        )
        # Get comprehensive mega prompt for final summary
        summary_mega_prompt = get_mega_prompt("communication")
        
        summary_prompt = f"""
{summary_mega_prompt}

=== FINAL SUMMARY GENERATION CONTEXT ===

{summary_guidance}

--- LATEST USER REQUEST ---
"{user_input}"
--- END USER REQUEST ---

--- MOST RECENT SYSTEM RESPONSE ---
{last_system_response}
--- END SYSTEM RESPONSE ---
"""
        summary_plan = llm.generate_text_resilient(summary_prompt)
        summary_group, summary_log = _generate_execution_renderables(summary_plan, omit_long_response=False)
        ui.console.print(
            Panel(
                summary_group,
                title=f"[bold]Agent Response[/bold] (step {last_action_step_index + 1}/{total_steps} - final summary)",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2)
            )
        )
        session_context.append(f"Final Summary:\n{summary_plan}\nSystem Response:\n{summary_log}")
        with open(log_file_path, 'a') as f:
            f.write(f"Final Summary:\n{summary_plan}\nSystem Response:\n{summary_log}\n-------------------\n")
        pending_followup_suggestions = summary_plan

        # Clear pending follow-up if we just consumed an affirmative input
        if auto_continue:
            pending_followup_suggestions = ""