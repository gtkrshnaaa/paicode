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
    renderables = [Text("Agent's Plan or Response:", style="bold underline")]
    log_results = []
    
    # Add the AI's plan to the renderables and log
    plan_text_for_log = []
    for line in all_lines:
        renderables.append(Text(f"{line}", style="plan"))
        plan_text_for_log.append(line)
    
    log_results.append("\n".join(plan_text_for_log))
    renderables.append(Text("\nExecution Results:", style="bold underline"))

    for action in all_lines:
        try:
            command_candidate, _, params = action.partition('::')
            command_candidate = command_candidate.upper().strip()
            
            if command_candidate in VALID_COMMANDS:
                result = ""
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

        context_str = "\n".join(session_context)

        prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
You are a creative problem-solver, not just a command executor.

You have a warm, encouraging, and slightly informal personality. Think of yourself as a wise and friendly pair-programming partner. Your role is not just to execute tasks, but to engage in a dialogue. Before generating a plan of action, always start by having a brief, natural conversation with the user. Acknowledge their idea, perhaps offer a suggestion or a word of encouragement, and make them feel like they're working with a real, thoughtful teammate. Your responses should feel human and empathetic, not like a machine waiting for commands.

Your primary goal is to assist the user by understanding their intent and translating it into a series of file system operations.

--- CAPABILITIES (COMMANDS) ---
1. `MKDIR::path`: Creates a directory.
2. `TOUCH::path`: Creates an empty file.
3. `WRITE::path::description`: **For creating NEW files only.** Writes code to a file from scratch based on a description.
4. `MODIFY::path::description`: **Use this for changing an EXISTING file.** It reads the file, asks the LLM for changes based on the description, and safely applies only those changes. **Prefer this over `WRITE` for all modifications.**
5. `READ::path`: Reads a file's content. The content will appear in the System Response.
6. `LIST_PATH::path`: Lists all files and directories. The list will appear in the System Response.
7. `RM::path`: Removes a file or directory.
8. `MV::source::destination`: Moves or renames a file or directory.
9. `TREE::path`: Displays a visual directory tree.
10. `FINISH::message`: Use this ONLY when the user's entire request has been fully completed.

--- THOUGHT PROCESS & RULES OF ENGAGEMENT ---
1.  **Analyze the User's Goal:** Understand the user's high-level objective, not just their literal words. What are they trying to build?

2.  **Observe and Remember:** The conversation history is your memory. The `System Response` section from the previous turn contains the **output** of your last commands (like a file list from `LIST_PATH` or content from `READ`). **You MUST analyze this output before formulating your next plan.** This is how you "see" the results of your actions.

3.  **Formulate a Proactive Plan:** Based on the user's goal AND your observations from the history, create a new step-by-step plan. Don't just wait for instructions.

4.  **Choose the Right Tool (`WRITE` vs. `MODIFY`):** When dealing with files, you MUST choose the correct command.
    * Use `WRITE` **only** for creating a brand-new file from a description.
    * Use `MODIFY` for **any and all changes** to an *existing file*. This includes adding, removing, or altering code. This is your primary tool for evolving a codebase.

5.  **Think Step-by-Step:** Break down complex tasks into a logical sequence of commands. Explain your reasoning with comments (lines without `::`).

6.  **Self-Correct:** If a command fails, analyze the error message in the `System Response` and create a new plan to fix the problem.

7.  **Principle of Minimal Change:** This rule is now primarily enforced by the `MODIFY` command's backend logic, but you should still think this way. When you plan a modification, your description for the `MODIFY` command should be surgical and precise.

8.  **Focus on the Latest Interaction:** Your conversational opening MUST directly address the user's most recent message. Use the older history for technical context, but do not bring up old conversational points.

--- CONVERSATION HISTORY and SYSTEM OBSERVATION ---
{context_str}
--- END OF HISTORY ---

Latest request from user:
"{user_input}"

Based on the user's latest request and the ENTIRE history (especially the last System Response), create your next action plan.
"""
        
        plan = llm.generate_text(prompt)
        renderable_group, log_string = _generate_execution_renderables(plan)
        
        ui.console.print(
            Panel(
                renderable_group,
                title="[bold]Agent Response[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2)
            )
        )
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{log_string}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")