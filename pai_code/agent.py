# pai_code/agent.py

import os
from datetime import datetime
from . import llm
from . import fs

HISTORY_DIR = ".pai_history"
VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "FINISH"]

def _execute_plan(plan: str) -> str:
    """
    Executes the action plan created by the LLM.
    """
    if not plan:
        return "Agent did not produce an action plan."

    all_lines = [line.strip() for line in plan.strip().split('\n') if line.strip()]
    execution_results = []
    
    print("\n--- Plan Execution Results ---")
    
    for action in all_lines:
        try:
            command_candidate, _, params = action.partition('::')
            command_candidate = command_candidate.upper().strip()
            
            if command_candidate in VALID_COMMANDS:
                result = ""
                
                if command_candidate not in ["WRITE", "READ", "TREE"]:
                    print(f"-> Action: {action}")

                if command_candidate == "WRITE":
                    file_path, _, _ = params.partition('::')
                    print(f"-> Action: Writing content to file '{file_path}'...")
                    result = handle_write(file_path, params)
                
                elif command_candidate == "READ":
                    path_to_read = params
                    print(f"-> Action: Reading file '{path_to_read}'...")
                    content = fs.read_file(path_to_read)
                    if content is not None:
                        print(f"--- FILE CONTENT: {path_to_read} ---\n{content}\n-----------------------------")
                        result = f"Success: Read {path_to_read}\n--- FILE CONTENT: {path_to_read} ---\n{content}\n-----------------------------"
                    else:
                        result = f"Error: Failed to read file: {path_to_read}"

                elif command_candidate == "TREE":
                    path_to_list = params if params else '.'
                    print(f"-> Action: Displaying directory structure for '{path_to_list}'...")
                    tree_output = fs.tree_directory(path_to_list)
                    if tree_output:
                        print(tree_output)
                        result = tree_output
                    else:
                        result = "Error: Failed to display directory structure."
                
                elif command_candidate == "FINISH":
                    result = params if params else "Task is considered complete."
                    print(f"Agent: {result}")
                    execution_results.append(result)
                    break 

                else: # Other commands: MKDIR, TOUCH, RM, MV
                    if command_candidate == "MKDIR": result = fs.create_directory(params)
                    elif command_candidate == "TOUCH": result = fs.create_file(params)
                    elif command_candidate == "RM": result = fs.delete_item(params)
                    elif command_candidate == "MV":
                        source, _, dest = params.partition('::')
                        result = fs.move_item(source, dest)
                
                if result and command_candidate not in ["READ", "TREE"]:
                      if "Success" in result or "Error" in result or "Warning" in result:
                            print(result)

                if result:
                    execution_results.append(result)

            else:
                print(f"{action}")
                execution_results.append(action)

        except Exception as e:
            msg = f"Error: An exception occurred while processing '{action}': {e}"
            print(msg)
            execution_results.append(msg)

    print("---------------------------------")
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
    print("Entering interactive auto mode. Type 'exit' or 'quit' to leave.")
    
    while True:
        try:
            user_input = input("pai> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated."); break
        if user_input.lower() in ['exit', 'quit']:
            print("Session ended."); break
        if not user_input: continue

        context_str = "\n".join(session_context)

        prompt = f"""
You are Pai, a meticulous autonomous AI agent. Your job is to assist the user with file system operations.

Available commands:
1. `MKDIR::path`
2. `TOUCH::path`
3. `WRITE::path::description`
4. `READ::path`
5. `RM::path`
6. `MV::source::destination`
7. `TREE::path`
8. `FINISH::optional closing message`

IMPORTANT RULES AND THOUGHT PROCESS:
- **Use Previous Command Results:** Pay close attention to the `System Response` part of the history. Use the output from previous commands (like `TREE`) to form your next plan. If `TREE` shows a list of files, you MUST use that list for a `READ` command if requested. Do not ask the user for information that is already available in the history.
- **One Command Per Line:** Provide one command per line in your plan.
- **Comments:** You can talk to the user. To comment, just write plain text without the command format.
- **WRITE Command:** For `WRITE`, the `description` part should ONLY contain a brief explanation, NOT the actual code.

--- PREVIOUS HISTORY ---
{context_str}
--- END OF HISTORY ---

Latest request from user:
"{user_input}"

Based on the ENTIRE history and the rules above, create the most accurate, intelligent, and communicative action plan. Do not get stuck in a loop asking for information that is already present.
"""
        
        plan = llm.generate_text(prompt)
        system_response = _execute_plan(plan)
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{system_response}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")