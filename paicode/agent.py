import os
import json
from datetime import datetime
from rich.prompt import Prompt
from rich.panel import Panel
from rich.console import Group
from rich.text import Text
from rich.syntax import Syntax
from rich.box import ROUNDED
from rich.table import Table
from . import llm, workspace, ui
from .platforms import detect_os

from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound

HISTORY_DIR = ".pai_history"
VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "LIST_PATH", "FINISH", "MODIFY"] 

def _generate_execution_renderables(plan: str) -> tuple[Group, str]:
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
    unknown_command_lines: list[str] = []
    for line in all_lines:
        cmd_candidate, _, _ = line.partition('::')
        if cmd_candidate.upper().strip() in VALID_COMMANDS:
            plan_lines.append(line)
        else:
            # If it looks like a command pattern but is not valid (e.g., RUN::...), collect it
            if '::' in line and cmd_candidate.upper().strip() not in VALID_COMMANDS:
                unknown_command_lines.append(line)
            response_lines.append(line)

    # Render Agent Response section (if any)
    if response_lines:
        renderables.append(Text("Agent Response:", style="bold underline"))
        for line in response_lines:
            renderables.append(Text(f"{line}", style="plan"))
        log_results.append("\n".join(response_lines))

    # Render Agent Plan section (if any)
    if plan_lines:
        renderables.append(Text("Agent Plan:", style="bold underline"))
        for line in plan_lines:
            renderables.append(Text(f"{line}", style="plan"))
        log_results.append("\n".join(plan_lines))

    # Warn about unknown pseudo-commands (e.g., RUN:: ...)
    if unknown_command_lines:
        renderables.append(Text("\nWarning: Ignored unknown commands (only VALID_COMMANDS are allowed in action steps):", style="warning"))
        for u in unknown_command_lines[:3]:
            renderables.append(Text(f"- {u}", style="warning"))
        if len(unknown_command_lines) > 3:
            renderables.append(Text(f"... and {len(unknown_command_lines) - 3} more", style="warning"))
        log_results.append("Ignored unknown commands: " + "; ".join(unknown_command_lines))

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

    for action in plan_lines:
        try:
            command_candidate, _, params = action.partition('::')
            command_candidate = command_candidate.upper().strip()
            
            if command_candidate in VALID_COMMANDS:
                result = ""
                # Add Execution Results header lazily when first execution item appears
                if not execution_header_added:
                    renderables.append(Text("\nExecution Results:", style="bold underline"))
                    execution_header_added = True
                action_text = Text(f"-> {action}", style="action")
                renderables.append(action_text)

                if command_candidate == "WRITE":
                    file_path, _, _ = params.partition('::')
                    result = handle_write(file_path, params)
                
                elif command_candidate == "READ":
                    path_to_read = params
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
                
                elif command_candidate == "MODIFY":
                    file_path, _, description = params.partition('::')
                    
                    original_content = workspace.read_file(file_path)
                    if original_content is None:
                        result = f"Error: Cannot modify '{file_path}' because it does not exist or cannot be read."
                        renderables.append(Text(f"✗ {result}", style="error"))
                        log_results.append(result)
                        continue

                    modification_prompt_1 = f"""
You are an expert code modifier. Here is the full content of the file `{file_path}`:
--- START OF FILE ---
{original_content}
--- END OF FILE ---

Based on the file content above, apply the following modification: "{description}".
IMPORTANT: You must only change the relevant parts of the code. Do not refactor, reformat, or alter any other part of the file.
Provide back the ENTIRE, complete file content with the modification applied. Provide ONLY the raw code without any explanations or markdown.
"""
                    new_content_1 = llm.generate_text(modification_prompt_1)

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
                            
                            new_content_2 = llm.generate_text(modification_prompt_2)
                            
                            if new_content_2:
                                success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_2)
                        
                        result = message
                        style = "success" if success else "warning"
                        icon = "✓ " if success else "! "
                    else:
                        result = f"Error: LLM failed to generate content for modification of '{file_path}'."
                        style = "error"; icon = "✗ "

                elif command_candidate == "TREE":
                    path_to_list = params if params else '.'
                    tree_output = workspace.tree_directory(path_to_list)
                    if tree_output and "Error:" not in tree_output:
                        renderables.append(Text(tree_output, style="bright_blue"))
                        # Log the actual tree output for the AI's memory
                        log_results.append(tree_output)
                        result = "Success: Displayed directory structure."
                    else:
                        result = tree_output or "Error: Failed to display directory structure."
                
                elif command_candidate == "LIST_PATH":
                    path_to_list = params if params else '.'
                    list_output = workspace.list_path(path_to_list)
                    if list_output and "Error:" not in list_output:
                        if list_output.strip():
                            renderables.append(Text(list_output, style="bright_blue"))
                        # Log the actual list output for the AI's memory
                        log_results.append(list_output)
                        result = f"Success: Listed paths for '{path_to_list}'."
                    else:
                        result = list_output or f"Error: Failed to list paths for '{path_to_list}'."
                
                elif command_candidate == "FINISH":
                    result = params if params else "Task is considered complete."
                    log_results.append(result)
                    renderables.append(Text(f"✓ Agent: {result}", style="success"))
                    break 

                else: # Other commands: MKDIR, TOUCH, RM, MV
                    if command_candidate == "MKDIR": result = workspace.create_directory(params)
                    elif command_candidate == "TOUCH": result = workspace.create_file(params)
                    elif command_candidate == "RM": result = workspace.delete_item(params)
                    elif command_candidate == "MV":
                        source, _, dest = params.partition('::')
                        result = workspace.move_item(source, dest)
                
                if result:
                    if "Success" in result: style = "success"; icon = "✓ "
                    elif "Error" in result: style = "error"; icon = "✗ "
                    elif "Warning" in result: style = "warning"; icon = "! "
                    else: style = "info"; icon = "i "
                    renderables.append(Text(f"{icon}{result}", style=style))
                    # Log the simple success/error message for non-data commands
                    if command_candidate not in ["READ", "TREE", "LIST_PATH"]:
                        log_results.append(result)

        except Exception as e:
            msg = f"An exception occurred while processing '{action}': {e}"
            renderables.append(Text(f"✗ {msg}", style="error"))
            log_results.append(msg)

    return Group(*renderables), "\n".join(log_results)

def _classify_intent(user_request: str, context: str) -> tuple[str, str, str]:
    """Classify user's intent into ('chat'|'task', 'simple'|'normal'|'complex', optional_reply_for_chat)."""
    try:
        # Quick heuristic first: if request contains a known command pattern, treat as task
        upper_req = user_request.upper()
        if any(cmd + "::" in upper_req for cmd in VALID_COMMANDS):
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

def _has_valid_command(plan_text: str) -> bool:
    """Check if plan text contains at least one VALID_COMMANDS line."""
    try:
        for line in (plan_text or "").splitlines():
            cmd_candidate, _, _ = line.partition('::')
            if cmd_candidate.upper().strip() in VALID_COMMANDS:
                return True
        return False
    except Exception:
        return False

def handle_write(file_path: str, params: str) -> str:
    """Invokes the LLM to create content and write it to a file."""
    _, _, description = params.partition('::')
    
    prompt = f"You are an expert programming assistant. Write the complete code for the file '{file_path}' based on the following description: \"{description}\". Provide ONLY the raw code without any explanations or markdown."
    
    code_content = llm.generate_text(prompt)
    
    if code_content:
        return workspace.write_to_file(file_path, code_content)
    else:
        return f"Error: Failed to generate content from LLM for file: {file_path}"

def start_interactive_session():
    """Starts an interactive session with the agent."""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")

    session_context = []
    pending_followup_suggestions = ""
    
    welcome_message = (
        "Welcome! I'm Pai, your agentic AI coding companion. Let's build something amazing together. ✨\n"
        "[info]Type 'exit' or 'quit' to leave.[/info]"
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
        # New 8-step flow per user request:
        # 1) Agent Response (no commands)
        # 2) Task Scheduler (high-level plan; no commands)
        # 3-7) Action steps (exactly one command per step)
        # 8) Final Summary (no commands; suggestions + confirmation question)
        #

        # Allow configuring total steps via environment, default to 25 (minimum 6)
        try:
            total_steps = int(os.getenv("PAI_MAX_STEPS", "25"))
            if total_steps < 6:
                total_steps = 8
        except ValueError:
            total_steps = 8

        # Step 1: Agent Response (no commands allowed)
        response_guidance = (
            "Provide a brief, warm, and encouraging response acknowledging the user's request. "
            "Do NOT include any actionable commands or tool calls."
        )
        os_info = detect_os()
        response_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
{response_guidance}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}
Note: You must output only application-level VALID COMMANDS (not shell). The system will translate them to OS commands.

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---
"""
        response_text = llm.generate_text(response_prompt)
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
            "Return a machine-readable task plan in JSON. Provide ONLY raw JSON without any extra text. "
            "Schema: {\"steps\": [{\"title\": string, \"hint\": string}]}. "
            "Include 2-6 steps that logically lead to the user's goal. Do NOT include any commands from VALID_COMMANDS. "
            "Steps should describe meaningful sub-goals (each may require executing multiple file operations)."
        )
        os_info = detect_os()
        scheduler_prompt = f"""
You are Pai, an expert planner and developer AI.
{scheduler_guidance}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}
Note: You must output only application-level VALID COMMANDS later in action steps; here produce only JSON steps.

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---
"""
        scheduler_plan = llm.generate_text_resilient(scheduler_prompt)
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

        # Steps 3-?: Action iterations (one or more actionable commands per step when appropriate)
        # Cap the number of action steps to at most 20 and also to the number of hints
        action_steps_count = min(20, max(1, total_steps - 3))
        if scheduler_hints:
            action_steps_count = min(action_steps_count, len(scheduler_hints))
        last_action_step_index = 2 + action_steps_count
        for action_idx in range(3, last_action_step_index + 1):
            guidance = (
                "Plan and execute the next actions towards the user's goal. "
                "You MAY output MULTIPLE actionable commands (each on its own line) from VALID COMMANDS below when it is efficient and safe. "
                "If the step requires several related file operations (e.g., delete multiple files, create several files), group them in this step. "
                "Do NOT output any other command type (e.g., RUN). Keep natural language to max 3 short lines followed by 1..N command lines."
            )

            # Supply a scheduler hint (if available) to make the step focused
            idx_from3 = action_idx - 3
            step_hint = scheduler_hints[idx_from3] if idx_from3 < len(scheduler_hints) else ""

            os_info = detect_os()
            action_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
You are a creative problem-solver, not just a command executor.

{guidance}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}
Note: Output only VALID COMMANDS; the system will render corresponding OS commands.

Target step hint: {step_hint}

--- VALID COMMANDS ---
1. MKDIR::path
2. TOUCH::path
3. WRITE::path::description
4. MODIFY::path::description
5. READ::path
6. LIST_PATH::path
7. RM::path
8. MV::source::destination
9. TREE::path
10. FINISH::message

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LAST SYSTEM RESPONSE (from previous iteration in this turn) ---
{last_system_response}
--- END LAST SYSTEM RESPONSE ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---

Reply now.
"""
            plan = llm.generate_text_resilient(action_prompt)

            # Hard-reprompt once if no valid command is detected
            if not _has_valid_command(plan):
                os_info = detect_os()
                reprompt = f"""
You did not provide any valid actionable command. You MUST output one or more lines with commands from VALID COMMANDS.
Repeat with a stricter focus on the target step. Keep it concise and do not include any other command types.

Target step hint: {step_hint}

--- OS CONTEXT ---
system_os: {os_info.name}
shell: {os_info.shell}
path_separator: {os_info.path_sep}

--- VALID COMMANDS ---
1. MKDIR::path
2. TOUCH::path
3. WRITE::path::description
4. MODIFY::path::description
5. READ::path
6. LIST_PATH::path
7. RM::path
8. MV::source::destination
9. TREE::path
10. FINISH::message
"""
                plan = llm.generate_text_resilient(reprompt)
            renderable_group, log_string = _generate_execution_renderables(plan)
            ui.console.print(
                Panel(
                    renderable_group,
                    title=f"[bold]Agent Action[/bold] (step {action_idx}/{total_steps})",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2)
                )
            )

            interaction_log = f"User: {user_input}\nIteration: {action_idx}/{total_steps}\nAI Plan:\n{plan}\nSystem Response:\n{log_string}"
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
            "Provide a concise FINAL SUMMARY of what has been accomplished so far, "
            "followed by 2-3 concrete suggestions for next steps. End with a clear confirmation question asking the user "
            "whether you should proceed with those suggestions. Do NOT include any actionable commands in this step."
        )
        summary_prompt = f"""
You are Pai. {summary_guidance}

--- LATEST USER REQUEST ---
"{user_input}"
--- END USER REQUEST ---

--- MOST RECENT SYSTEM RESPONSE ---
{last_system_response}
--- END SYSTEM RESPONSE ---
"""
        summary_plan = llm.generate_text_resilient(summary_prompt)
        summary_group, summary_log = _generate_execution_renderables(summary_plan)
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