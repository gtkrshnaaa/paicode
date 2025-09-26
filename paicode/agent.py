import os
from datetime import datetime
from rich.prompt import Prompt
from rich.panel import Panel
from rich.console import Group
from rich.text import Text
from rich.syntax import Syntax
from rich.box import ROUNDED
from . import llm, workspace, ui

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
    for line in all_lines:
        cmd_candidate, _, _ = line.partition('::')
        if cmd_candidate.upper().strip() in VALID_COMMANDS:
            plan_lines.append(line)
        else:
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

    # Enforce single actionable command per inference: execute only the first command line
    if len(plan_lines) > 1:
        renderables.append(Text("\nNote: Multiple commands detected in a single step. Only the first will be executed.", style="warning"))
        plan_lines = plan_lines[:1]

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

        #
        # New 8-step flow per user request:
        # 1) Agent Response (no commands)
        # 2) Task Scheduler (high-level plan; no commands)
        # 3-7) Action steps (exactly one command per step)
        # 8) Final Summary (no commands; suggestions + confirmation question)
        #

        total_steps = 8

        # Step 1: Agent Response (no commands allowed)
        response_guidance = (
            "Provide a brief, warm, and encouraging response acknowledging the user's request. "
            "Do NOT include any actionable commands or tool calls."
        )
        response_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
{response_guidance}

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

        # Step 2: Task Scheduler (no commands; outline steps)
        scheduler_guidance = (
            "Outline a concise, numbered task plan (2-6 steps) to reach the user's goal. "
            "Each step should be an action title with a one-line rationale. Do NOT include actionable commands from VALID COMMANDS."
        )
        scheduler_prompt = f"""
You are Pai, an expert planner and developer AI.
{scheduler_guidance}

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LAST SYSTEM RESPONSE ---
{last_system_response}
--- END LAST SYSTEM RESPONSE ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---
"""
        scheduler_plan = llm.generate_text(scheduler_prompt)
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

        # Steps 3-7: Action iterations (exactly one actionable command per step)
        for action_idx in range(3, 8):
            guidance = (
                "Plan and execute the next SINGLE best action towards the user's goal. "
                "You MUST output EXACTLY ONE actionable command from VALID COMMANDS below (or FINISH::message if done). "
                "You may include 1-2 short natural language lines before the command."
            )

            action_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
You are a creative problem-solver, not just a command executor.

{guidance}

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
            plan = llm.generate_text(action_prompt)
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

        # Step 8: Final Summary
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
        summary_plan = llm.generate_text(summary_prompt)
        summary_group, summary_log = _generate_execution_renderables(summary_plan)
        ui.console.print(
            Panel(
                summary_group,
                title=f"[bold]Agent Response[/bold] (step 8/{total_steps} - final summary)",
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