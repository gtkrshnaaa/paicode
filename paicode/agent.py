import os
import json
import signal
import threading
from datetime import datetime
from rich.prompt import Prompt
from rich.panel import Panel
from rich.console import Group
from rich.text import Text
from rich.syntax import Syntax
from rich.box import ROUNDED
from rich.table import Table
from . import llm, workspace, ui

from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound

# Try to import prompt_toolkit for better input experience
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

HISTORY_DIR = ".pai_history"
VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "LIST_PATH", "FINISH", "MODIFY"]

# Global flag for interrupt handling
_interrupt_requested = False
_interrupt_lock = threading.Lock()

def request_interrupt():
    """Request interruption of current AI response."""
    global _interrupt_requested
    with _interrupt_lock:
        _interrupt_requested = True

def check_interrupt():
    """Check if interrupt was requested and reset flag."""
    global _interrupt_requested
    with _interrupt_lock:
        if _interrupt_requested:
            _interrupt_requested = False
            return True
        return False

def reset_interrupt():
    """Reset interrupt flag."""
    global _interrupt_requested
    with _interrupt_lock:
        _interrupt_requested = False 

def _generate_execution_renderables(plan: str) -> tuple[Group, str]:
    """
    Executes the plan, generates Rich renderables for display, and creates a detailed log string.
    """
    if not plan:
        msg = "Agent did not produce an action plan."
        return Group(Text(msg, style="warning")), msg

    # Additional cleanup: remove any markdown artifacts that slipped through
    plan = plan.strip()
    # Remove code block markers
    if plan.startswith('```'):
        lines = plan.split('\n')
        # Remove first line if it's a code block marker
        if lines[0].startswith('```'):
            lines = lines[1:]
        # Remove last line if it's a closing marker
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        plan = '\n'.join(lines)
    
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
You are an expert code modifier with deep understanding of software engineering best practices.

CURRENT FILE: `{file_path}`
--- START OF FILE ---
{original_content}
--- END OF FILE ---

MODIFICATION REQUEST: "{description}"

CRITICAL INSTRUCTIONS:
1. Analyze the current code structure carefully
2. Identify EXACTLY what needs to change to fulfill the request
3. Make ONLY the necessary changes - do not refactor unrelated code
4. Preserve existing code style, formatting, and conventions
5. Ensure the modification is correct and complete
6. Consider edge cases and potential bugs
7. Maintain backward compatibility unless explicitly asked to break it

SAFETY CONSTRAINTS - VERY IMPORTANT:
- HARD LIMIT: Maximum 500 changed lines per modification
- BEST PRACTICE: Even though limit is 500, prefer smaller focused modifications (100-200 lines)
- Think like a senior developer: make surgical, targeted changes
- Focus on ONE specific area at a time (e.g., one section, one function, one feature)
- Example of EXCELLENT incremental approach (like Cascade):
  * Modification 1: Update function signature and add type hints (30 lines)
  * Modification 2: Add input validation logic (50 lines)
  * Modification 3: Enhance error handling (40 lines)
  * Modification 4: Add comprehensive docstrings (30 lines)
- Example: If adding CSS, do it in logical sections:
  * Part 1: Add basic layout styles (body, container, main structure)
  * Part 2: Add form element styles (inputs, labels, form-group)
  * Part 3: Add button and interactive styles (hover, focus, active states)
- NEVER try to apply all changes at once if they can be logically separated
- Quality over quantity: smaller, focused changes are easier to verify and safer

OUTPUT REQUIREMENTS:
- Provide the ENTIRE, complete file content with modifications applied
- Output ONLY raw code without explanations, markdown, or comments about changes
- Do NOT use markdown code blocks (no ```)
- Do NOT include language tags or diff format
- Do NOT show before/after comparisons
- Start directly with the complete modified file content
- Ensure the code is syntactically correct and will run without errors

Example of CORRECT output:
<!DOCTYPE html>
<html>
... (complete file with modifications)

Example of WRONG output (DO NOT DO THIS):
```html
<!DOCTYPE html>
...
```

OR

```diff
- old line
+ new line
```

Think carefully before modifying. Quality over speed.
"""
                    new_content_1 = llm.generate_text(modification_prompt_1)

                    if new_content_1:
                        success, message = workspace.apply_modification_with_patch(file_path, original_content, new_content_1)
                        
                        # Check if modification was rejected due to size
                        if not success and "exceeds" in message.lower():
                            renderables.append(Text(f"! Modification rejected: too large. {message}", style="warning"))
                            renderables.append(Text("! Think like Cascade: Break into focused, surgical modifications.", style="warning"))
                            renderables.append(Text("! Ideal: 100-200 lines (very focused), Acceptable: 200-500 lines (one area)", style="info"))
                            result = f"Error: {message}\nSuggestion: Use Cascade-style approach - split into focused modifications targeting one specific area at a time."
                            renderables.append(Text(f"✗ {result}", style="error"))
                            log_results.append(result)
                            continue
                        
                        if success and "No changes detected" in message:
                            renderables.append(Text("! First attempt made no changes. Retrying with a more specific prompt...", style="warning"))
                            
                            modification_prompt_2 = f"""
CRITICAL: First attempt returned unchanged code. You MUST make the requested modification now.

FILE: `{file_path}`
ORIGINAL CONTENT:
---
{original_content}
---

EXPLICIT INSTRUCTION: "{description}"

WHAT WENT WRONG:
The previous attempt returned the code unchanged. This means you need to:
1. Re-read the instruction more carefully
2. Identify the EXACT location that needs modification
3. Make the specific change requested
4. Ensure the change is actually applied

REQUIREMENTS:
- This is a critical modification - it MUST be applied
- Be very literal and precise about the change
- Return the COMPLETE file with the modification applied
- Output ONLY raw code without explanations or markdown
- Maximum 120 changed lines

DO NOT return the code unchanged again. Make the modification.
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
                        log_results.append(f"TREE result for '{path_to_list}':\n{tree_output}")
                        result = f"Success: Displayed directory structure for '{path_to_list}'."
                    else:
                        result = tree_output or f"Error: Failed to display directory structure for '{path_to_list}'."
                
                elif command_candidate == "LIST_PATH":
                    path_to_list = params if params else '.'
                    list_output = workspace.list_path(path_to_list)
                    if list_output is not None and "Error:" not in list_output:
                        # Always display the output, even if empty (shows directory is empty)
                        if list_output.strip():
                            renderables.append(Text(list_output, style="bright_blue"))
                        else:
                            renderables.append(Text(f"Directory '{path_to_list}' is empty or contains only hidden/sensitive files.", style="dim"))
                        # Log the actual list output for the AI's memory
                        log_results.append(f"LIST_PATH result for '{path_to_list}':\n{list_output}")
                        result = f"Success: Listed paths for '{path_to_list}'. Found {len(list_output.splitlines()) if list_output.strip() else 0} items."
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
            "You are an intent classifier for a coding assistant. Analyze the user's message and classify it.\n\n"
            "CLASSIFICATION CRITERIA:\n"
            "- 'chat' mode: Questions, greetings, clarifications, discussions (no file operations needed)\n"
            "- 'task' mode: Requests to create, modify, read, or manage files/code\n\n"
            "COMPLEXITY LEVELS:\n"
            "- 'simple': Single file operation or basic task (1-2 steps)\n"
            "- 'normal': Multiple related operations or moderate complexity (3-5 steps)\n"
            "- 'complex': Large-scale changes, architecture work, or many dependencies (6+ steps)\n\n"
            "Return ONLY raw JSON with this schema:\n"
            "{\"mode\": \"chat\"|\"task\", \"complexity\": \"simple\"|\"normal\"|\"complex\", \"reply\": string|null}\n\n"
            "If mode is 'chat', provide a helpful reply. If mode is 'task', set 'reply' to null."
        )
        classifier_input = f"""
{prompt}

User's message: "{user_request}"

Context from conversation:
{context[-500:] if context else "No prior context"}

Classify accurately based on the actual intent.
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
    
    if not description.strip():
        return f"Error: No description provided for file: {file_path}"
    
    # Infer file type and provide context
    file_ext = os.path.splitext(file_path)[1].lower()
    lang_hints = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.md': 'Markdown',
        '.txt': 'Plain Text'
    }
    language = lang_hints.get(file_ext, 'code')
    
    prompt = f"""You are an expert programming assistant with deep knowledge of software engineering best practices.

TARGET FILE: {file_path}
LANGUAGE: {language}
DESCRIPTION: {description}

CRITICAL REQUIREMENTS:
1. Write complete, production-quality code
2. Follow {language} best practices and conventions
3. Include appropriate error handling
4. Add clear, concise comments for complex logic
5. Use meaningful variable and function names
6. Ensure code is syntactically correct and will run without errors
7. Consider edge cases and potential issues
8. Make the code maintainable and readable

CRITICAL OUTPUT FORMAT:
- Output ONLY the raw code, nothing else
- Do NOT use markdown code blocks (no ```)
- Do NOT include language tags (no "html", "python", etc. on first line)
- Do NOT add explanations before or after the code
- Start directly with the code content
- Ensure proper indentation and formatting

Example of CORRECT output for HTML:
<!DOCTYPE html>
<html>
...

Example of WRONG output (DO NOT DO THIS):
```html
<!DOCTYPE html>
...
```

Write high-quality code that you would be proud to ship.
"""
    
    code_content = llm.generate_text(prompt)
    
    if code_content and code_content.strip():
        return workspace.write_to_file(file_path, code_content)
    else:
        return f"Error: Failed to generate content from LLM for file: {file_path}"

def _compress_context(context: list[str], max_items: int = 10) -> str:
    """Compress context to keep only the most recent and relevant items."""
    if len(context) <= max_items:
        return "\n".join(context)
    
    # Keep first 2 items (initial context) and last max_items-2 items (recent context)
    compressed = context[:2] + ["... [earlier context omitted for brevity] ..."] + context[-(max_items-2):]
    return "\n".join(compressed)

def _clean_markdown_formatting(text: str) -> str:
    """Remove markdown formatting artifacts from text."""
    if not text:
        return text
    
    # Remove markdown bullet points at line start
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Remove markdown list markers (*, -, +) at the start
        if stripped.startswith('* '):
            stripped = stripped[2:]
        elif stripped.startswith('- '):
            stripped = stripped[2:]
        elif stripped.startswith('+ '):
            stripped = stripped[2:]
        # Remove bold markers but keep content
        stripped = stripped.replace('**', '')
        cleaned_lines.append(stripped)
    
    return '\n'.join(cleaned_lines)

def start_interactive_session():
    """Start the revolutionary single-shot intelligent session."""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")
    
    session_context = []
    
    welcome_message = (
        "Welcome to Paicode Single-Shot Intelligence!\n"
        "Revolutionary 2-call architecture: Maximum intelligence, minimal API usage.\n"
        "[info]Type 'exit' or 'quit' to leave.[/info]\n"
        "[info]Each request uses exactly 2 API calls for optimal efficiency.[/info]"
    )

    ui.console.print(
        Panel(
            Text(welcome_message, justify="center"),
            title="[bold]Single-Shot Intelligence Mode[/bold]",
            box=ROUNDED,
            border_style="blue",
            padding=(1, 2)
        )
    )
    
    # Setup prompt session with better input handling
    if PROMPT_TOOLKIT_AVAILABLE:
        prompt_session = PromptSession()
    
    # Setup signal handler for graceful interrupt
    def signal_handler(signum, frame):
        if check_interrupt():
            # Second Ctrl+C, actually exit
            ui.console.print("\n[warning]Session terminated.[/warning]")
            os._exit(0)
        else:
            # First Ctrl+C, just interrupt AI response
            request_interrupt()
            ui.console.print("\n[yellow]⚠ Interrupt requested. AI will stop after current step.[/yellow]")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        try:
            if PROMPT_TOOLKIT_AVAILABLE:
                user_input = prompt_session.prompt("\nuser> ").strip()
            else:
                user_input = Prompt.ask("\n[bold bright_blue]user>[/bold bright_blue]").strip()
        except (EOFError, KeyboardInterrupt):
            ui.console.print("\n[warning]Session terminated.[/warning]")
            break
            
        if user_input.lower() in ['exit', 'quit']:
            ui.print_info("Session ended.")
            break
        
        if not user_input:
            continue

        # Execute single-shot intelligence
        success = execute_single_shot_intelligence(user_input, session_context)
        
        # Add to session context for future reference
        session_context.append({
            "timestamp": datetime.now().isoformat(),
            "user_request": user_input,
            "success": success
        })
        
        # Keep context manageable (last 5 interactions)
        if len(session_context) > 5:
            session_context = session_context[-5:]

def execute_single_shot_intelligence(user_request: str, context: list) -> bool:
    """
    Execute the revolutionary 2-call single-shot intelligence system.
    
    Call 1: PLANNING - Deep analysis and comprehensive planning
    Call 2: EXECUTION - Intelligent execution with adaptation
    
    Returns:
        bool: Success status
    """
    
    # === CALL 1: PLANNING PHASE ===
    ui.console.print(
        Panel(
            Text("Deep Analysis & Planning", style="bold"),
            title="[bold blue]Call 1/2: Intelligence Planning[/bold blue]",
            box=ROUNDED,
            border_style="blue"
        )
    )
    
    planning_result = execute_planning_call(user_request, context)
    if not planning_result:
        ui.print_error("Planning phase failed. Cannot proceed.")
        return False
    
    # === CALL 2: EXECUTION PHASE ===
    ui.console.print(
        Panel(
            Text("⚡ Intelligent Execution", style="bold"),
            title="[bold green]Call 2/2: Smart Execution[/bold green]",
            box=ROUNDED,
            border_style="green"
        )
    )
    
    execution_success = execute_execution_call(user_request, planning_result, context)
    
    # Show final status
    if execution_success:
        ui.console.print(
            Panel(
                Text("Single-Shot Intelligence: SUCCESS", style="bold green"),
                title="[bold]Mission Accomplished[/bold]",
                box=ROUNDED,
                border_style="green"
            )
        )
    else:
        ui.console.print(
            Panel(
                Text("Single-Shot Intelligence: PARTIAL SUCCESS", style="bold yellow"),
                title="[bold]Mission Status[/bold]",
                box=ROUNDED,
                border_style="yellow"
            )
        )
    
    return execution_success

def execute_planning_call(user_request: str, context: list) -> dict | None:
    """
    CALL 1: Execute deep planning and analysis.
    This call focuses on understanding, analyzing, and creating a comprehensive plan.
    """
    
    # Build context string
    context_str = ""
    if context:
        context_str = "Previous interactions:\n"
        for item in context[-3:]:  # Last 3 interactions
            context_str += f"- {item['timestamp']}: {item['user_request']} ({'s' if item['success'] else 'e'})\n"
    
    # Get current directory context
    current_files = workspace.list_path('.')
    current_tree = workspace.tree_directory('.')
    
    planning_prompt = f"""
You are a SENIOR SOFTWARE ARCHITECT with deep expertise in all programming languages and development practices.

Your task: Create a COMPREHENSIVE INTELLIGENT PLAN for the user's request using MAXIMUM INTELLIGENCE in this single call.

USER REQUEST: "{user_request}"

CURRENT CONTEXT:
{context_str}

CURRENT DIRECTORY STRUCTURE:
{current_tree}

CURRENT FILES:
{current_files}

YOUR MISSION (CRITICAL - This is your ONLY planning opportunity):

1. DEEP ANALYSIS:
   - What EXACTLY does the user want to achieve?
   - What are ALL the technical requirements?
   - What files/directories need to be created/modified?
   - What are potential edge cases and challenges?
   - What is the optimal technical approach?

2. COMPREHENSIVE PLANNING:
   - Break down into logical, executable steps
   - Consider dependencies between steps
   - Plan for error handling and edge cases
   - Identify required file operations (READ, WRITE, MODIFY, etc.)
   - Consider best practices and code quality

3. INTELLIGENT PREPARATION:
   - What information needs to be gathered first?
   - What existing code needs to be analyzed?
   - What are the success criteria?
   - How to verify the solution works?

4. EXECUTION STRATEGY:
   - Sequence of operations for maximum efficiency
   - Fallback strategies if something fails
   - How to adapt if unexpected situations arise

CRITICAL OUTPUT FORMAT:
Return a JSON object with this EXACT structure:

{{
  "analysis": {{
    "user_intent": "Clear description of what user wants",
    "technical_requirements": ["req1", "req2", "req3"],
    "files_to_read": ["file1", "file2"],
    "files_to_create": ["file1", "file2"],
    "files_to_modify": ["file1", "file2"],
    "edge_cases": ["case1", "case2"],
    "success_criteria": ["criteria1", "criteria2"]
  }},
  "execution_plan": {{
    "steps": [
      {{
        "step_number": 1,
        "action": "READ",
        "target": "filename",
        "purpose": "why this step is needed",
        "expected_outcome": "what we expect to find/achieve"
      }},
      {{
        "step_number": 2,
        "action": "WRITE",
        "target": "filename",
        "purpose": "why this step is needed",
        "expected_outcome": "what we expect to achieve"
      }}
    ],
    "fallback_strategies": ["strategy1", "strategy2"],
    "verification_steps": ["how to verify success"]
  }},
  "intelligence_notes": {{
    "complexity_assessment": "simple|moderate|complex",
    "estimated_time": "time estimate",
    "key_challenges": ["challenge1", "challenge2"],
    "recommendations": ["rec1", "rec2"]
  }}
}}

REMEMBER: This is your ONLY chance to plan. Make it COMPREHENSIVE and INTELLIGENT.
Use your MAXIMUM INTELLIGENCE - think like the world's best software architect.

Output ONLY the JSON object, no additional text.
"""
    
    planning_response = llm.generate_text(planning_prompt, "deep planning")
    
    if not planning_response:
        return None
    
    try:
        # Parse JSON response
        planning_data = json.loads(planning_response)
        
        # Display planning results
        display_planning_results(planning_data)
        
        return planning_data
        
    except json.JSONDecodeError as e:
        ui.print_error(f"Failed to parse planning response: {e}")
        ui.print_info("Raw response:")
        ui.console.print(planning_response[:500] + "..." if len(planning_response) > 500 else planning_response)
        return None

def display_planning_results(planning_data: dict):
    """Display the planning results in a beautiful format."""
    
    # Analysis section
    analysis = planning_data.get("analysis", {})
    ui.console.print("\n[bold]Deep Analysis Results:[/bold]")
    ui.console.print(f"Intent: {analysis.get('user_intent', 'Unknown')}")
    ui.console.print(f"Files to read: {len(analysis.get('files_to_read', []))}")
    ui.console.print(f"Files to create: {len(analysis.get('files_to_create', []))}")
    ui.console.print(f"Files to modify: {len(analysis.get('files_to_modify', []))}")
    
    # Execution plan
    execution_plan = planning_data.get("execution_plan", {})
    steps = execution_plan.get("steps", [])
    ui.console.print(f"\n⚡ [bold]Execution Plan: {len(steps)} steps[/bold]")
    
    for i, step in enumerate(steps[:3], 1):  # Show first 3 steps
        action = step.get("action", "Unknown")
        target = step.get("target", "Unknown")
        purpose = step.get("purpose", "No purpose specified")
        ui.console.print(f"   {i}. {action} {target} - {purpose}")
    
    if len(steps) > 3:
        ui.console.print(f"   ... and {len(steps) - 3} more steps")
    
    # Intelligence notes
    intelligence = planning_data.get("intelligence_notes", {})
    complexity = intelligence.get("complexity_assessment", "unknown")
    ui.console.print(f"\n[bold]Intelligence Assessment:[/bold]")
    ui.console.print(f"Complexity: {complexity}")
    ui.console.print(f"Estimated time: {intelligence.get('estimated_time', 'unknown')}")

def execute_execution_call(user_request: str, planning_data: dict, context: list) -> bool:
    """
    CALL 2: Execute the planned actions with intelligent adaptation.
    This call focuses on executing the plan while adapting to real-world conditions.
    """
    
    execution_prompt = f"""
You are a SENIOR SOFTWARE ENGINEER executing a carefully planned solution.

ORIGINAL USER REQUEST: "{user_request}"

COMPREHENSIVE PLAN (from previous analysis):
{json.dumps(planning_data, indent=2)}

YOUR MISSION: Execute this plan with MAXIMUM INTELLIGENCE and ADAPTABILITY.

EXECUTION GUIDELINES:

1. INTELLIGENT EXECUTION:
   - Follow the plan but adapt to real conditions
   - If a file doesn't exist as expected, handle gracefully
   - If code structure is different than expected, adapt
   - Make intelligent decisions based on what you discover

2. AVAILABLE COMMANDS:
   - READ::filepath - Read and analyze files
   - WRITE::filepath::description - Create new files with content
   - MODIFY::filepath::description - Modify existing files
   - TREE::path - Show directory structure
   - LIST_PATH::path - List files in directory
   - MKDIR::path - Create directories
   - TOUCH::filepath - Create empty files
   - RM::path - Remove files/directories
   - MV::source::destination - Move files
   - FINISH::message - Complete the task

3. EXECUTION STRATEGY:
   - Start with information gathering (READ, TREE, LIST_PATH)
   - Execute planned actions in logical order
   - Verify each step before proceeding
   - Adapt plan if you discover unexpected conditions
   - Always end with FINISH when complete

4. QUALITY STANDARDS:
   - Write production-quality code
   - Follow best practices for the language/framework
   - Include proper error handling
   - Add meaningful comments where appropriate
   - Ensure code is readable and maintainable

5. INTELLIGENT ADAPTATION:
   - If planned file doesn't exist, check alternatives
   - If code structure is different, adapt accordingly
   - If you encounter errors, troubleshoot intelligently
   - Make smart decisions based on real conditions

OUTPUT FORMAT:
Provide a sequence of commands, one per line, following this format:
COMMAND::parameter1::parameter2

Example:
READ::package.json
TREE::.
WRITE::src/app.js::Create main application file with Express server setup
MODIFY::package.json::Add new dependencies for the project
FINISH::Successfully created the web application with all required components

CRITICAL: Execute the plan intelligently. Adapt as needed. Deliver a complete solution.

Begin execution now:
"""
    
    execution_response = llm.generate_text(execution_prompt, "intelligent execution")
    
    if not execution_response:
        return False
    
    # Execute the commands
    return execute_command_sequence(execution_response)

def execute_command_sequence(command_sequence: str) -> bool:
    """Execute a sequence of commands from the AI."""
    
    commands = [line.strip() for line in command_sequence.split('\n') if line.strip()]
    total_commands = len(commands)
    successful_commands = 0
    
    ui.console.print(f"\n[bold]Executing {total_commands} intelligent actions...[/bold]")
    
    for i, command_line in enumerate(commands, 1):
        if not command_line or '::' not in command_line:
            continue
        
        # Parse command
        parts = command_line.split('::', 2)
        if len(parts) < 2:
            continue
        
        command = parts[0].upper().strip()
        param1 = parts[1].strip() if len(parts) > 1 else ""
        param2 = parts[2].strip() if len(parts) > 2 else ""
        
        if command not in VALID_COMMANDS:
            ui.print_warning(f"Unknown command: {command}")
            continue
        
        # Display current action
        ui.console.print(f"\n[{i}/{total_commands}] {command} {param1}")
        
        # Execute command
        success = execute_single_command(command, param1, param2)
        
        if success:
            successful_commands += 1
            ui.console.print("   Success")
        else:
            ui.console.print("   Failed")
        
        # Break on FINISH command
        if command == "FINISH":
            break
    
    # Show execution summary
    success_rate = (successful_commands / total_commands) * 100 if total_commands > 0 else 0
    ui.console.print(f"\n[bold]Execution Summary:[/bold]")
    ui.console.print(f"   Successful: {successful_commands}/{total_commands} ({success_rate:.1f}%)")
    
    return success_rate >= 80  # Consider successful if 80%+ commands succeeded

def execute_single_command(command: str, param1: str, param2: str) -> bool:
    """Execute a single command and return success status."""
    
    try:
        if command == "READ":
            content = workspace.read_file(param1)
            if content is not None:
                # Display file content with syntax highlighting
                try:
                    lexer = get_lexer_for_filename(param1)
                    lang = lexer.aliases[0]
                except ClassNotFound:
                    lang = "text"
                
                # Show first 20 lines for brevity
                lines = content.split('\n')
                display_content = '\n'.join(lines[:20])
                if len(lines) > 20:
                    display_content += f"\n... ({len(lines) - 20} more lines)"
                
                syntax_panel = Panel(
                    Syntax(display_content, lang, theme="monokai", line_numbers=True),
                    title=f"{param1}",
                    border_style="blue",
                    expand=False
                )
                ui.console.print(syntax_panel)
                return True
            return False
        
        elif command == "WRITE":
            if not param2:
                ui.print_error("WRITE command requires description")
                return False
            return handle_write_command(param1, param2)
        
        elif command == "MODIFY":
            if not param2:
                ui.print_error("MODIFY command requires description")
                return False
            return handle_modify_command(param1, param2)
        
        elif command == "TREE":
            path = param1 if param1 else '.'
            tree_output = workspace.tree_directory(path)
            if tree_output and "Error:" not in tree_output:
                ui.console.print(Text(tree_output, style="bright_blue"))
                return True
            return False
        
        elif command == "LIST_PATH":
            path = param1 if param1 else '.'
            list_output = workspace.list_path(path)
            if list_output is not None and "Error:" not in list_output:
                if list_output.strip():
                    ui.console.print(Text(list_output, style="bright_blue"))
                else:
                    ui.console.print(Text(f"Directory '{path}' is empty", style="dim"))
                return True
            return False
        
        elif command == "MKDIR":
            result = workspace.create_directory(param1)
            ui.console.print(Text(result, style="green" if "Success" in result else "red"))
            return "Success" in result
        
        elif command == "TOUCH":
            result = workspace.create_file(param1)
            ui.console.print(Text(result, style="green" if "Success" in result else "red"))
            return "Success" in result
        
        elif command == "RM":
            result = workspace.delete_item(param1)
            ui.console.print(Text(result, style="green" if "Success" in result else "red"))
            return "Success" in result
        
        elif command == "MV":
            result = workspace.move_item(param1, param2)
            ui.console.print(Text(result, style="green" if "Success" in result else "red"))
            return "Success" in result
        
        elif command == "FINISH":
            message = param1 if param1 else "Task completed successfully"
            ui.console.print(
                Panel(
                    Text(f"{message}", style="bold green"),
                    title="[bold]Task Completed[/bold]",
                    border_style="green"
                )
            )
            return True
        
        return False
        
    except Exception as e:
        ui.print_error(f"Command execution error: {e}")
        return False

def handle_write_command(filepath: str, description: str) -> bool:
    """Handle WRITE command with intelligent content generation."""
    
    # Generate content based on file type and description
    content_prompt = f"""
Generate high-quality content for a file based on the description.

FILE PATH: {filepath}
DESCRIPTION: {description}

REQUIREMENTS:
1. Analyze the file extension to determine the appropriate language/format
2. Create production-quality, well-structured content
3. Include appropriate comments and documentation
4. Follow best practices for the detected language/format
5. Make the code/content immediately usable

OUTPUT: Return ONLY the file content, no explanations or markdown formatting.
"""
    
    content = llm.generate_text(content_prompt, "content generation")
    
    if not content:
        return False
    
    # Write the file
    result = workspace.write_file(filepath, content)
    ui.console.print(Text(result, style="green" if "Success" in result else "red"))
    
    return "Success" in result

def handle_modify_command(filepath: str, description: str) -> bool:
    """Handle MODIFY command with intelligent code modification."""
    
    # Read existing content
    existing_content = workspace.read_file(filepath)
    if existing_content is None:
        ui.print_error(f"Cannot modify '{filepath}' - file not found")
        return False
    
    # Generate modification
    modify_prompt = f"""
You are an expert code modifier. Modify the existing code based on the description.

FILE PATH: {filepath}
CURRENT CONTENT:
---
{existing_content}
---

MODIFICATION REQUEST: {description}

REQUIREMENTS:
1. Preserve the existing code structure and style
2. Make only the necessary changes described
3. Maintain code quality and best practices
4. Ensure the modified code is syntactically correct
5. Add appropriate comments for new functionality

OUTPUT: Return ONLY the complete modified file content, no explanations.
"""
    
    modified_content = llm.generate_text(modify_prompt, "code modification")
    
    if not modified_content:
        return False
    
    # Write the modified file
    result = workspace.write_file(filepath, modified_content)
    ui.console.print(Text(result, style="green" if "Success" in result else "red"))
    
    return "Success" in result
