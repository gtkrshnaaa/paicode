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
    """Starts an interactive session with the agent."""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")

    session_context = []
    pending_followup_suggestions = ""
    
    welcome_message = (
        "Welcome! I'm Pai, your agentic AI coding companion. Let's build something amazing together. ✨\n"
        "[info]Type 'exit' or 'quit' to leave.[/info]\n"
        "[info]Press Ctrl+C once during AI response to interrupt (keeps session alive).[/info]\n"
        "[info]Press Ctrl+C twice to exit completely.[/info]"
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
        reset_interrupt()  # Reset interrupt flag at start of each loop
        try:
            if PROMPT_TOOLKIT_AVAILABLE:
                # Use prompt_toolkit for better multiline editing
                user_input = prompt_session.prompt("\nuser> ").strip()
            else:
                # Fallback to rich Prompt
                user_input = Prompt.ask("\n[bold bright_blue]user>[/bold bright_blue]").strip()
        except (EOFError, KeyboardInterrupt):
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

        # Compress context to avoid token overflow
        context_str = _compress_context(session_context, max_items=12)

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
                response_text = llm.generate_text(response_prompt)
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

        # Track actual steps executed (for proper numbering)
        current_step = 0
        max_steps = 8  # Maximum steps to show user the limit
        
        # Step 1: Agent Response (no commands allowed)
        current_step += 1
        response_guidance = (
            "Provide a VERY brief (1-2 sentences max) acknowledgment of the user's request. "
            "Show understanding but be concise. "
            "If the request is ambiguous, state your assumption in one sentence. "
            "Do NOT include any actionable commands or tool calls. "
            "Keep it short and professional."
        )
        response_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI with deep understanding of:
- Software architecture and design patterns
- Best practices for clean, maintainable code
- Common pitfalls and how to avoid them
- Context from previous interactions

{response_guidance}

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---

Analyze the request carefully. If anything is unclear, state your assumptions.
"""
        # Show interrupt hint before AI starts working
        ui.console.print("[dim]💡 Tip: Press Ctrl+C to interrupt AI response[/dim]")
        
        response_text = llm.generate_text(response_prompt)
        response_group, response_log = _generate_execution_renderables(response_text)
        ui.console.print(
            Panel(
                response_group,
                title=f"[bold]Agent Response[/bold] (step {current_step}/{max_steps})",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2)
            )
        )
        interaction_log = f"User: {user_input}\nIteration: {current_step}\nAI Plan:\n{response_text}\nSystem Response:\n{response_log}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")
        last_system_response = response_log

        # Always use the Task Scheduler for 'task' mode to outline steps first

        # Step 2: Task Scheduler (no commands; outline steps) for normal/complex tasks
        current_step += 1
        scheduler_guidance = (
            "Return a machine-readable task plan in JSON. Provide ONLY raw JSON without any extra text. "
            "Schema: {\"steps\": [{\"title\": string, \"hint\": string}]}. "
            "Include 2-6 steps that logically lead to the user's goal. Do NOT include any commands from VALID_COMMANDS. "
            "Steps should describe meaningful sub-goals (each may require executing multiple file operations). "
            "Think like a senior developer: consider dependencies, order of operations, and potential issues. "
            "Each step should be atomic and verifiable. "
            "IMPORTANT: If a task involves large modifications (e.g., adding extensive CSS/HTML), break it into smaller incremental steps. "
            "Example: Instead of 'Add all CSS styling', break into 'Add basic layout CSS', 'Add form styling CSS', 'Add interactive CSS'."
        )
        scheduler_prompt = f"""
You are Pai, an expert planner and developer AI with strong analytical skills.

Your task planning should:
1. Break down complex tasks into logical, sequential steps
2. Consider dependencies between steps
3. Anticipate potential issues and plan accordingly
4. Ensure each step has a clear, verifiable outcome
5. Follow software engineering best practices
6. Think like Cascade: make focused, surgical modifications
7. BEST PRACTICE: Keep each step focused on one specific area (100-200 lines ideal)
8. Maximum 500 lines per modification, but prefer smaller when possible

Example of EXCELLENT planning (Cascade-style, incremental and focused):
- Step 1: Create basic HTML structure (semantic elements only)
- Step 2: Add core layout CSS (body, container, flexbox centering)
- Step 3: Add form structure CSS (form-group, spacing, alignment)
- Step 4: Add input field styling (borders, padding, focus states)
- Step 5: Add button styling (colors, hover effects, transitions)

Example of GOOD planning (efficient but still focused):
- Step 1: Create HTML structure with basic inline comments
- Step 2: Add layout and form container CSS together
- Step 3: Add all form element styling (inputs, labels, buttons)

Example of ACCEPTABLE planning (uses higher limit but less ideal):
- Step 1: Create complete HTML structure
- Step 2: Add all CSS styling in one go (up to 500 lines)

Example of BAD planning (too monolithic):
- Step 1: Create everything at once (HTML + all CSS + JavaScript)

{scheduler_guidance}

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---
"""
        scheduler_plan = llm.generate_text(scheduler_prompt)
        # Sanitize accidental language tag prefix like 'json' on its own line
        sp = scheduler_plan.strip()
        
        # Remove common prefixes that might appear before JSON
        prefixes_to_remove = ['json', 'JSON', 'on', 'ON']
        for prefix in prefixes_to_remove:
            if sp.lower().startswith(prefix.lower()):
                parts = sp.split('\n', 1)
                if len(parts) == 2:
                    sp = parts[1].strip()
                    break
        
        # Try to extract JSON if it's wrapped in text
        if not sp.startswith('{'):
            # Find first { and last }
            start_idx = sp.find('{')
            end_idx = sp.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                sp = sp[start_idx:end_idx+1]
        
        scheduler_plan = sp
        
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
                title=f"[bold]Task Scheduler[/bold] (step {current_step}/{max_steps})",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2)
            )
        )
        interaction_log = f"User: {user_input}\nIteration: {current_step}\nAI Plan:\n{scheduler_plan}\nSystem Response:\n{scheduler_log}"
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

        # Steps 3+: Action iterations (one or more actionable commands per step when appropriate)
        # Cap the number of action steps to at most 5 and also to the number of hints
        action_steps_count = min(5, max(1, len(scheduler_hints) if scheduler_hints else 3))
        
        for action_iteration in range(action_steps_count):
            current_step += 1
            
            # Check for interrupt before each step
            if check_interrupt():
                ui.console.print("\n[yellow]⚠ AI response interrupted by user. Stopping execution.[/yellow]")
                session_context.append(f"[SYSTEM] AI response interrupted at step {current_step}")
                break
            
            guidance = (
                "Execute the next actions towards the user's goal. "
                "You MAY output MULTIPLE actionable commands (each on its own line) from VALID COMMANDS below when efficient and safe. "
                "If the step requires several related file operations, group them in this step. "
                "For MODIFY, keep each modification under 120 changed lines; split larger changes across iterations. "
                "Do NOT output any other command type (e.g., RUN). "
                "Keep explanations to 1-2 lines max, then output commands directly."
            )

            # Supply a scheduler hint (if available) to make the step focused
            step_hint = scheduler_hints[action_iteration] if action_iteration < len(scheduler_hints) else ""
            
            # Thinking phase (pre-execution): produce a concise internal reasoning summary (no commands)
            thinking_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
You are a creative problem-solver with deep technical expertise, not just a command executor.

Before taking any action, think step-by-step about the best approach. Consider:
1. What is the exact goal of this step?
2. What files/directories need to be checked or modified?
3. What are potential edge cases or issues?
4. What is the minimal, safest set of actions needed?
5. How will I verify success?
6. CRITICAL: Can this modification be focused on one specific area (like Cascade does)?
7. If modifying a file, estimate the size:
   - Small (30-100 lines): Perfect, very focused
   - Medium (100-200 lines): Good, still focused
   - Large (200-500 lines): Acceptable but consider if it can be split
   - Very Large (>500 lines): MUST split into multiple modifications

CRITICAL OUTPUT FORMAT:
- Output ONLY plain text bullet points, NO markdown
- Do NOT use markdown formatting (no *, **, -, etc.)
- Use simple numbered list or plain text
- Keep it concise: 3-6 points
- Focus strictly on the target step hint
- Think like Cascade: surgical, focused, one area at a time
- Explicitly state estimated modification size and approach

Target step hint: {step_hint}

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LAST SYSTEM RESPONSE ---
{last_system_response}
--- END LAST SYSTEM RESPONSE ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---

Think carefully and methodically.
"""
            thinking_text = llm.generate_text(thinking_prompt)
            # Clean markdown formatting from thinking output
            thinking_text = _clean_markdown_formatting(thinking_text)
            # Render concise thinking summary (no commands expected)
            thinking_group, thinking_log = _generate_execution_renderables(thinking_text)
            ui.console.print(
                Panel(
                    thinking_group,
                    title=f"[bold]Thinking[/bold] (pre-execution for step {current_step}/{max_steps})",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2)
                )
            )
            session_context.append(f"Pre-Execution Thinking (step {current_step}):\n{thinking_text}")

            action_prompt = f"""
You are Pai, an expert, proactive, and autonomous software developer AI.
You are a creative problem-solver with deep technical expertise, not just a command executor.

CRITICAL RULES FOR HIGH-QUALITY OUTPUT:
1. Always READ files before MODIFY to understand current state
2. Use TREE or LIST_PATH to explore structure before creating files
3. For WRITE commands, provide detailed, complete descriptions
4. For MODIFY commands, be specific about what to change and why
5. Verify your actions make sense given the context
6. If uncertain, READ first to gather information
7. Use descriptive file/directory names following conventions
8. Consider error cases and edge conditions

CRITICAL OUTPUT FORMAT RULES:
- Output ONLY plain text commands, NO markdown code blocks
- Do NOT wrap commands in ```command``` or ```language``` blocks
- Do NOT include language tags like "html", "json", "diff" on separate lines
- Keep explanations brief (max 2 lines) before commands
- Commands must be on their own lines in format: COMMAND::params

{guidance}

Target step hint: {step_hint}

--- YOUR THINKING SUMMARY (use as guidance; do not echo back) ---
{thinking_text}
--- END THINKING SUMMARY ---
--- VALID COMMANDS ---
1. MKDIR::path - Create directory (use forward slashes, no spaces in names)
2. TOUCH::path - Create empty file
3. WRITE::path::description - Write new file with detailed description of content
   CRITICAL: description is REQUIRED and must be detailed (minimum 10 words)
   Example: WRITE::index.html::Create a login page with username and password fields, styled with gray colors
   WRONG: WRITE::index.html (missing description - will cause error!)
4. MODIFY::path::description - Modify existing file with detailed description of changes
   CRITICAL: description is REQUIRED and must be specific about what to change
   Example: MODIFY::index.html::Add responsive CSS media queries for mobile devices
   WRONG: MODIFY::index.html (missing description - will cause error!)
5. READ::path - Read file content (ALWAYS do this before MODIFY)
6. LIST_PATH::path - List all files/dirs recursively
7. RM::path - Delete file or directory
8. MV::source::destination - Move/rename file or directory
9. TREE::path - Show directory tree structure
10. FINISH::message - Mark task complete with summary

CRITICAL COMMAND RULES (MUST FOLLOW):
- WRITE and MODIFY MUST have detailed descriptions after second ::
- Description must be specific and clear (minimum 10 words)
- Never use WRITE::path or MODIFY::path without description
- If you forget description, you will get ERROR: "No description provided for file"
- Always READ before MODIFY to understand current state
--- END VALID COMMANDS ---

--- CONVERSATION HISTORY (all previous turns) ---
{context_str}
--- END HISTORY ---

--- LAST SYSTEM RESPONSE (from previous iteration in this turn) ---
{last_system_response}
--- END LAST SYSTEM RESPONSE ---

--- LATEST USER REQUEST ---
"{user_effective_request}"
--- END USER REQUEST ---

Execute the target step with precision and care. Double-check your commands before outputting.
"""
            plan = llm.generate_text(action_prompt)

            # Hard-reprompt once if no valid command is detected
            if not _has_valid_command(plan):
                reprompt = f"""
You did not provide any valid actionable command. You MUST output one or more lines with commands from VALID COMMANDS.
Repeat with a stricter focus on the target step. Keep it concise and do not include any other command types.

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
"""
                plan = llm.generate_text(reprompt)
            renderable_group, log_string = _generate_execution_renderables(plan)
            ui.console.print(
                Panel(
                    renderable_group,
                    title=f"[bold]Agent Action[/bold] (step {current_step}/{max_steps})",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2)
                )
            )

            interaction_log = f"User: {user_input}\nIteration: {current_step}\nAI Plan:\n{plan}\nSystem Response:\n{log_string}"
            session_context.append(interaction_log)
            with open(log_file_path, 'a') as f:
                f.write(interaction_log + "\n-------------------\n")

            last_system_response = log_string

            # Integrity check (post-execution): verify alignment with the step hint and task
            integrity_prompt = f"""
You are a senior code reviewer and integrity auditor AI. Evaluate whether the last executed actions align with the target step and user request.

Your evaluation should check:
1. Did the actions address the target step correctly?
2. Were the actions safe and appropriate?
3. Are there any obvious errors or issues?
4. Did the agent follow best practices?
5. Is the output complete and correct?

CRITICAL OUTPUT FORMAT:
- Return ONLY raw JSON, no markdown code blocks
- Do NOT wrap in ```json or ``` markers
- Start directly with {{ and end with }}
- No explanations before or after JSON

JSON Schema:
{{"passed": true|false, "reasons": [string..], "next_fix": [string..], "quality_score": 1-10 }}

Where:
- passed: true if actions correctly addressed the step, false otherwise
- reasons: list of specific reasons for the verdict (ALWAYS provide at least 1 reason)
- next_fix: list of specific fixes needed if failed, or improvements if passed
- quality_score: 1-10 rating of execution quality (10 = perfect)

Context:
- Target step hint: {step_hint}
- Latest system response (results of actions):
{last_system_response}
- Latest user request: "{user_effective_request}"

Be thorough and critical. High standards lead to better code.
Output ONLY the JSON object.
"""
            integrity_json = llm.generate_text(integrity_prompt)
            # Best-effort parse
            verdict = {"passed": False, "reasons": [], "next_fix": [], "quality_score": 0}
            try:
                parsed = json.loads(integrity_json)
                if isinstance(parsed, dict):
                    verdict["passed"] = bool(parsed.get("passed", False))
                    r = parsed.get("reasons")
                    if isinstance(r, list): verdict["reasons"] = [str(x) for x in r]
                    f = parsed.get("next_fix")
                    if isinstance(f, list): verdict["next_fix"] = [str(x) for x in f]
                    q = parsed.get("quality_score")
                    if isinstance(q, (int, float)): verdict["quality_score"] = int(q)
            except Exception:
                pass

            table = Table(show_header=True, header_style="bold", box=ROUNDED)
            table.add_column("Integrity", justify="left", style="bold")
            table.add_column("Details", overflow="fold")
            status_text = "PASS" if verdict["passed"] else "FAIL"
            if verdict["quality_score"] > 0:
                status_text += f" (Quality: {verdict['quality_score']}/10)"
            table.add_row("Status", status_text)
            
            # Always show reasons and fixes if available
            if verdict["reasons"] and len(verdict["reasons"]) > 0:
                reasons_text = "\n".join(verdict["reasons"])
                table.add_row("Reasons", reasons_text)
            else:
                # If no reasons provided but status is FAIL, add default message
                if not verdict["passed"]:
                    table.add_row("Reasons", "Integrity check failed. Review the action results above.")
            
            if verdict["next_fix"] and len(verdict["next_fix"]) > 0:
                fix_label = "Improvements" if verdict["passed"] else "Required Fixes"
                fixes_text = "\n".join(verdict["next_fix"])
                table.add_row(fix_label, fixes_text)
            integrity_group = Group(Text("Integrity Check", style="bold underline"), table)
            ui.console.print(
                Panel(
                    integrity_group,
                    title=f"[bold]Integrity[/bold] (post-execution step {current_step}/{max_steps})",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2)
                )
            )
            session_context.append(f"Integrity Check (step {current_step}): {json.dumps(verdict)}")

            # If model indicates finish early, break action loop and proceed to summary
            if any(line.strip().upper().startswith("FINISH::") for line in plan.splitlines()):
                finished_early = True
                break

        # Final Summary step
        current_step += 1
        summary_guidance = (
            "Provide a concise FINAL SUMMARY of what has been accomplished so far, "
            "followed by 2-3 concrete, actionable suggestions for next steps. "
            "End with a clear confirmation question asking the user whether you should proceed with those suggestions. "
            "Do NOT include any actionable commands in this step."
        )
        summary_prompt = f"""
You are Pai, an expert software developer AI providing a comprehensive summary.

TASK: Summarize the work completed and suggest next steps.

SUMMARY REQUIREMENTS:
1. List what was successfully accomplished (be specific)
2. Mention any issues encountered and how they were resolved
3. Provide 2-3 concrete, logical next steps that build on what was done
4. Make suggestions actionable and prioritized
5. End with a clear question asking if the user wants to proceed

TONE: Professional, clear, and helpful. Show understanding of the bigger picture.

--- ORIGINAL USER REQUEST ---
"{user_input}"
--- END USER REQUEST ---

--- MOST RECENT SYSTEM RESPONSE ---
{last_system_response}
--- END SYSTEM RESPONSE ---

Provide a summary that demonstrates deep understanding of what was accomplished and what should come next.
"""
        summary_plan = llm.generate_text(summary_prompt)
        summary_group, summary_log = _generate_execution_renderables(summary_plan)
        ui.console.print(
            Panel(
                summary_group,
                title=f"[bold]Agent Response[/bold] (step {current_step}/{max_steps} - final summary)",
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