# paicode/agent.py

import os
from datetime import datetime
from rich.prompt import Prompt
from . import llm, fs, ui

HISTORY_DIR = ".pai_history"
VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "FINISH"]

def _execute_plan(plan: str) -> str:
    """
    Executes the action plan created by the LLM with rich TUI feedback.
    """
    if not plan:
        return "Agent did not produce an action plan."

    all_lines = [line.strip() for line in plan.strip().split('\n') if line.strip()]
    execution_results = []
    
    ui.print_rule("Plan Execution Results")
    
    for action in all_lines:
        try:
            command_candidate, _, params = action.partition('::')
            command_candidate = command_candidate.upper().strip()
            
            if command_candidate in VALID_COMMANDS:
                result = ""
                
                ui.print_action(action)

                if command_candidate == "WRITE":
                    file_path, _, _ = params.partition('::')
                    result = handle_write(file_path, params)
                
                elif command_candidate == "READ":
                    path_to_read = params
                    content = fs.read_file(path_to_read)
                    if content is not None:
                        ui.display_panel(content, f"Content of {path_to_read}", language="python")
                        result = f"Success: Read {path_to_read}"
                    else:
                        result = f"Error: Failed to read file: {path_to_read}"

                elif command_candidate == "TREE":
                    path_to_list = params if params else '.'
                    tree_output = fs.tree_directory(path_to_list)
                    if tree_output:
                        ui.console.print(f"[cyan]{tree_output}[/cyan]")
                        result = "Success: Displayed directory structure."
                    else:
                        result = "Error: Failed to display directory structure."
                
                elif command_candidate == "FINISH":
                    result = params if params else "Task is considered complete."
                    ui.print_success(f"Agent: {result}")
                    execution_results.append(result)
                    break 

                else: # Other commands: MKDIR, TOUCH, RM, MV
                    if command_candidate == "MKDIR": result = fs.create_directory(params)
                    elif command_candidate == "TOUCH": result = fs.create_file(params)
                    elif command_candidate == "RM": result = fs.delete_item(params)
                    elif command_candidate == "MV":
                        source, _, dest = params.partition('::')
                        result = fs.move_item(source, dest)
                
                if result:
                    if "Success" in result: ui.print_success(result)
                    elif "Error" in result: ui.print_error(result)
                    elif "Warning" in result: ui.print_warning(result)
                    else: ui.print_info(result)
                
                if result:
                    execution_results.append(result)

            else:
                # This handles comments or explanations from the agent's plan
                ui.print_info(action)
                execution_results.append(action)

        except Exception as e:
            msg = f"An exception occurred while processing '{action}': {e}"
            ui.print_error(msg)
            execution_results.append(msg)

    ui.print_rule("Execution Complete") 
    return "\n".join(execution_results) if execution_results else "Execution finished with no result."

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
    ui.print_rule("Interactive Auto Mode")
    ui.print_info("Type 'exit' or 'quit' to leave.")
    
    while True:
        try:
            user_input = Prompt.ask("[bold magenta]pai>[/bold magenta]").strip()
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
7. `TREE::path` - List directory structure.
8. `FINISH::message` - Use this when the user's request is fully completed.

Thought Process:
1.  **Analyze the Goal:** What does the user want to build or achieve?
2.  **Plan the Structure:** What files and folders are needed? (e.g., `src/`, `main.py`, `utils.py`).
3.  **Create the Plan:** Formulate a step-by-step plan using the available commands. Start with `MKDIR` and `TOUCH`, then use `WRITE` to add code.
4.  **Communicate:** Use comments (lines without `::`) to explain your plan to the user.

--- PREVIOUS HISTORY ---
{context_str}
--- END OF HISTORY ---

Latest request from user:
"{user_input}"

Based on the user's request and the entire history, create a clear, step-by-step action plan to accomplish the software development task. Be proactive and take initiative.
"""
        
        plan = llm.generate_text(prompt)
        system_response = _execute_plan(plan)
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{system_response}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")