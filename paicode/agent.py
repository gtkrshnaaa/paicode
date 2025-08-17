# paicode/agent.py

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
    Executes the plan and generates a list of Rich renderables for display.
    Does NOT print directly to the console.
    Returns a tuple of (Group_of_renderables, log_string).
    """
    if not plan:
        msg = "Agent did not produce an action plan."
        return Group(Text(msg, style="warning")), msg

    all_lines = [line.strip() for line in plan.strip().split('\n') if line.strip()]
    renderables = [Text("Agent's Plan:", style="bold underline")]
    log_results = []
    
    # First, add the entire plan to the renderables
    for line in all_lines:
        renderables.append(Text(f"{line}", style="plan"))
        log_results.append(line)
    
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
                            border_style="cyan",
                            expand=False
                        )
                        renderables.append(syntax_panel)
                        result = f"Success: Read and displayed {path_to_read}"
                    else:
                        result = f"Error: Failed to read file: {path_to_read}"


                elif command_candidate == "TREE":
                    path_to_list = params if params else '.'
                    tree_output = fs.tree_directory(path_to_list)
                    if tree_output:
                        renderables.append(Text(tree_output, style="cyan"))
                        result = "Success: Displayed directory structure."
                    else:
                        result = "Error: Failed to display directory structure."
                
                elif command_candidate == "LIST_PATH":
                    path_to_list = params if params else '.'
                    list_output = fs.list_path(path_to_list)
                    if list_output and "Error:" not in list_output:
                        if list_output.strip():
                            renderables.append(Text(list_output, style="cyan"))
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
            user_input = Prompt.ask("\n[bold magenta]pai>[/bold magenta]").strip()
        except (KeyboardInterrupt, EOFError):
            ui.console.print("\n[warning]Session terminated.[/warning]")
            break
        if user_input.lower() in ['exit', 'quit']:
            ui.print_info("Session ended.")
            break
        if not user_input: continue

        context_str = "\n".join(session_context)

        prompt = f"""
You are Pai, an expert and autonomous software developer AI.
Your goal is to help the user build and manage software projects.
You operate by creating a plan of file system commands.

Your capabilities:
- You can understand high-level user requests (e.g., "create a BMI calculator program").
- You MUST break down these requests into a sequence of file system commands.
- You can write code by using the `WRITE` command.
- You can and should create entire project structures, write code, and manage files autonomously.
- You are not just a file operator; you are a DEVELOPER. Your output should be a plan to build software.

Available commands:
1. `MKDIR::path` - Create a directory.
2. `TOUCH::path` - Create an empty file.
3. `WRITE::path::description` - Write code to a file based on a description. The LLM will generate the code.
4. `READ::path` - Read a file's content.
5. `RM::path` - Remove a file or directory.
6. `MV::source::destination` - Move or rename.
7. `TREE::path` - List directory structure visually (for humans).
8. `LIST_PATH::path` - List all file/dir paths recursively. Use this to get a machine-readable list to understand the project structure.
9. `FINISH::message` - Use this when the user's request is fully completed.

Thought Process:
1.  **Analyze the Goal:** What does the user want to build or achieve?
2.  **Explore (if needed):** Use `LIST_PATH` to see the current file structure if you are unsure.
3.  **Plan the Structure:** What files and folders are needed? (e.g., `src/`, `main.py`, `utils.py`).
4.  **Create the Plan:** Formulate a step-by-step plan using the available commands. Start with `MKDIR` and `TOUCH`, then use `WRITE` to add code.
5.  **Communicate:** Use comments (lines without `::`) to explain your plan to the user.

--- PREVIOUS HISTORY ---
{context_str}
--- END OF HISTORY ---

Latest request from user:
"{user_input}"

Based on the user's request and the entire history, create a clear, step-by-step action plan to accomplish the software development task. Be proactive and take initiative.
"""
        
        plan = llm.generate_text(prompt)
        renderable_group, log_string = _generate_execution_renderables(plan)
        
        # Now, print everything inside a single panel
        ui.console.print(
            Panel(
                renderable_group,
                title="[bold]Agent Response[/bold]",
                box=ROUNDED,
                border_style="cyan",
                padding=(1, 2)
            )
        )
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{log_string}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")