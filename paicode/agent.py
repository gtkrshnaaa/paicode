import os
from datetime import datetime
from rich.prompt import Prompt
from rich.panel import Panel
from rich.console import Group
from rich.text import Text
from rich.syntax import Syntax
from rich.box import ROUNDED
from . import llm, fs, ui

from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound

HISTORY_DIR = ".pai_history"
VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "LIST_PATH", "FINISH"]

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
                    content = fs.read_file(path_to_read)
                    if content is not None:
                        try:
                            lexer = get_lexer_for_filename(path_to_read)
                            lang = lexer.aliases[0]
                        except ClassNotFound:
                            lang = "text"
                        
                        syntax_panel = Panel(
                            Syntax(content, lang, theme="monokai", line_numbers=True),
                            title=f"Content of {path_to_read}",
                            border_style="purple",
                            expand=False
                        )
                        renderables.append(syntax_panel)
                        # FIX: Log the actual content for the AI's memory
                        log_results.append(f"Content of {path_to_read}:\n---\n{content}\n---")
                        result = f"Success: Read and displayed {path_to_read}"
                    else:
                        result = f"Error: Failed to read file: {path_to_read}"

                elif command_candidate == "TREE":
                    path_to_list = params if params else '.'
                    tree_output = fs.tree_directory(path_to_list)
                    if tree_output and "Error:" not in tree_output:
                        renderables.append(Text(tree_output, style="purple"))
                        # FIX: Log the actual tree output for the AI's memory
                        log_results.append(tree_output)
                        result = "Success: Displayed directory structure."
                    else:
                        result = tree_output or "Error: Failed to display directory structure."
                
                elif command_candidate == "LIST_PATH":
                    path_to_list = params if params else '.'
                    list_output = fs.list_path(path_to_list)
                    if list_output and "Error:" not in list_output:
                        if list_output.strip():
                            renderables.append(Text(list_output, style="purple"))
                        # FIX: Log the actual list output for the AI's memory
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
                    if command_candidate == "MKDIR": result = fs.create_directory(params)
                    elif command_candidate == "TOUCH": result = fs.create_file(params)
                    elif command_candidate == "RM": result = fs.delete_item(params)
                    elif command_candidate == "MV":
                        source, _, dest = params.partition('::')
                        result = fs.move_item(source, dest)
                
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
        return fs.write_to_file(file_path, code_content)
    else:
        return f"Error: Failed to generate content from LLM for file: {file_path}"

def start_interactive_session():
    """Starts an interactive session with the agent."""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")

    session_context = []
    
    ui.print_panel_title("Interactive Auto Mode")
    ui.print_info("Type 'exit' or 'quit' to leave.")
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold magenta]user>[/bold magenta]").strip()
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
3. `WRITE::path::description`: Writes code to a file based on a high-level description.
4. `READ::path`: Reads a file's content. The content will appear in the System Response.
5. `LIST_PATH::path`: Lists all files and directories. The list will appear in the System Response.
6. `RM::path`: Removes a file or directory.
7. `MV::source::destination`: Moves or renames a file or directory.
8. `TREE::path`: Displays a visual directory tree.
9. `FINISH::message`: Use this ONLY when the user's entire request has been fully completed.

--- THOUGHT PROCESS & RULES OF ENGAGEMENT ---
1.  **Analyze the User's Goal:** Understand the user's high-level objective, not just their literal words. What are they trying to build?

2.  **Observe and Remember:** The conversation history is your memory. The `System Response` section from the previous turn contains the **output** of your last commands (like a file list from `LIST_PATH` or content from `READ`). **You MUST analyze this output before formulating your next plan.** This is how you "see" the results of your actions.

3.  **Formulate a Proactive Plan:** Based on the user's goal AND your observations from the history, create a new step-by-step plan. Don't just wait for instructions. If the user asks a question you can answer by running a command, run it. If you need to see the project structure first, use `LIST_PATH`. If you need to know what's in a file, use `READ`.

4.  **Think Step-by-Step:** Break down complex tasks into a logical sequence of commands. Explain your reasoning with comments (lines without `::`).

5.  **Self-Correct:** If a command fails, analyze the error message in the `System Response` and create a new plan to fix the problem.

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
                border_style="purple",
                padding=(1, 2)
            )
        )
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{log_string}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")