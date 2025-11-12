#!/usr/bin/env python

import os
import json
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.box import ROUNDED
from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound

try:
    from prompt_toolkit import PromptSession
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from . import llm, workspace, ui

# History directory
HISTORY_DIR = os.path.expanduser("~/.config/pai-code/history")

# Valid commands for execution
VALID_COMMANDS = {
    "READ", "WRITE", "MODIFY", "TREE", "LIST_PATH", 
    "MKDIR", "TOUCH", "RM", "MV", "FINISH"
}

# Global interrupt handling
_interrupt_requested = False
_interrupt_lock = threading.Lock()

def request_interrupt():
    global _interrupt_requested
    with _interrupt_lock:
        _interrupt_requested = True

def check_interrupt():
    global _interrupt_requested
    with _interrupt_lock:
        if _interrupt_requested:
            _interrupt_requested = False
            return True
        return False

def reset_interrupt():
    global _interrupt_requested
    with _interrupt_lock:
        _interrupt_requested = False

def start_interactive_session():
    """Start the revolutionary single-shot intelligent session."""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")
    
    session_context = []
    
    welcome_message = (
        "Welcome! I'm Pai, your agentic AI coding companion. ✨\n"
        "Now powered by Single-Shot Intelligence for maximum efficiency.\n"
        "[info]Type 'exit' or 'quit' to leave.[/info]\n"
        "[info]Each request uses exactly 2 API calls for optimal performance.[/info]"
    )

    ui.console.print(
        Panel(
            Text(welcome_message, justify="center"),
            title="[bold]Interactive Auto Mode[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    # Setup prompt session with better input handling
    if PROMPT_TOOLKIT_AVAILABLE:
        prompt_session = PromptSession()
    
    # Setup signal handler for graceful interrupt
    def signal_handler(signum, frame):
        if check_interrupt():
            # Second Ctrl+C → Exit
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
                user_input = ui.Prompt.ask("\n[bold bright_blue]user>[/bold bright_blue]").strip()
        except (EOFError, KeyboardInterrupt):
            ui.console.print("\n[warning]Session terminated.[/warning]")
            break
            
        if user_input.lower() in ['exit', 'quit']:
            ui.print_info("Session ended.")
            break
        
        if not user_input:
            continue

        # Classify user intent: conversation vs task
        intent = classify_user_intent(user_input)
        
        if intent == "conversation":
            # Simple conversation mode
            success = execute_conversation_mode(user_input, session_context)
        else:
            # Task execution mode (planning + execution)
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

def classify_user_intent(user_input: str) -> str:
    """
    Use AI intelligence to classify user intent as either 'conversation' or 'task'.
    Let the AI decide based on context and understanding.
    
    Returns:
        str: 'conversation' for casual chat, 'task' for work requests
    """
    
    classification_prompt = f"""
You are an intelligent intent classifier. Analyze the user's message and determine if they want:

1. CONVERSATION: Casual chat, greetings, questions about you, general discussion, or just talking
2. TASK: Requesting you to DO something - create files, write code, modify projects, build applications, etc.

USER MESSAGE: "{user_input}"

ANALYSIS GUIDELINES:
- If user is greeting, asking about you, or just chatting → CONVERSATION
- If user wants you to create, modify, build, fix, or do any work → TASK
- If user is asking "how to" without wanting you to do it → CONVERSATION  
- If user is asking you to actually do something → TASK
- Use your intelligence to understand the intent behind the words

OUTPUT: Respond with exactly one word: "conversation" or "task"
"""
    
    response = llm.generate_text(classification_prompt, "intent classification")
    
    if response:
        intent = response.strip().lower()
        if intent in ["conversation", "task"]:
            return intent
    
    # Fallback: if AI response is unclear, default to conversation for safety
    return "conversation"

def execute_conversation_mode(user_input: str, context: list) -> bool:
    """
    Handle casual conversation with the user.
    Simple, friendly responses without task execution.
    """
    
    # Build context for conversation
    context_str = ""
    if context:
        recent_context = context[-2:]  # Last 2 interactions
        context_str = "Recent conversation:\n"
        for item in recent_context:
            context_str += f"User: {item['user_request']}\n"
    
    conversation_prompt = f"""
You are Pai, a friendly and helpful AI coding companion. The user is having a casual conversation with you.

CONVERSATION CONTEXT:
{context_str}

USER MESSAGE: "{user_input}"

RESPONSE GUIDELINES:
1. Be friendly, helpful, and conversational
2. Keep responses concise (1-3 sentences max)
3. If asked about your capabilities, mention you can help with coding tasks
4. If user seems to want to start a task, gently suggest they can ask you to create/modify files
5. Be natural and engaging, but professional
6. Use a warm, approachable tone

Respond naturally to the user's message:
"""
    
    response = llm.generate_text(conversation_prompt, "conversation")
    
    if response:
        # Display conversation response with clean UI
        ui.console.print(
            Panel(
                Text(response.strip(), style="bright_white"),
                title="[bold]Pai[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        return True
    else:
        ui.print_error("Sorry, I couldn't process your message right now.")
        return False

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
            Text("Deep Analysis & Planning", style="bold", justify="center"),
            title="[bold]Call 1/2: Intelligence Planning[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    planning_result = execute_planning_call(user_request, context)
    if not planning_result:
        ui.print_error("✗ Planning phase failed. Cannot proceed.")
        return False
    
    # === CALL 2: EXECUTION PHASE ===
    ui.console.print(
        Panel(
            Text("Intelligent Execution", style="bold", justify="center"),
            title="[bold]Call 2/2: Smart Execution[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    execution_success = execute_execution_call(user_request, planning_result, context)
    
    # Show final status with original Paicode styling
    if execution_success:
        ui.console.print(
            Panel(
                Text("Single-Shot Intelligence: SUCCESS", style="bold green", justify="center"),
                title="[bold]Mission Accomplished[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
    else:
        ui.console.print(
            Panel(
                Text("Single-Shot Intelligence: PARTIAL SUCCESS", style="bold yellow", justify="center"),
                title="[bold]Mission Status[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
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
            context_str += f"- {item['timestamp']}: {item['user_request']} ({'✅' if item['success'] else '❌'})\n"
    
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
        
        # Display planning results with original Paicode styling
        display_planning_results(planning_data)
        
        return planning_data
        
    except json.JSONDecodeError as e:
        ui.print_error(f"✗ Failed to parse planning response: {e}")
        ui.print_info("Raw response:")
        ui.console.print(planning_response[:500] + "..." if len(planning_response) > 500 else planning_response)
        return None

def display_planning_results(planning_data: dict):
    """Display the planning results in original Paicode style."""
    
    # Analysis section
    analysis = planning_data.get("analysis", {})
    ui.console.print("\n[bold]Deep Analysis Results:[/bold]")
    ui.console.print(f"   Intent: {analysis.get('user_intent', 'Unknown')}")
    ui.console.print(f"   Files to read: {len(analysis.get('files_to_read', []))}")
    ui.console.print(f"   Files to create: {len(analysis.get('files_to_create', []))}")
    ui.console.print(f"   Files to modify: {len(analysis.get('files_to_modify', []))}")
    
    # Execution plan
    execution_plan = planning_data.get("execution_plan", {})
    steps = execution_plan.get("steps", [])
    ui.console.print(f"\n[bold]Execution Plan: {len(steps)} steps[/bold]")
    
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
    ui.console.print(f"   Complexity: {complexity}")
    ui.console.print(f"   Estimated time: {intelligence.get('estimated_time', 'unknown')}")

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
    
    # Show execution summary with original styling
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
                    border_style="grey50",
                    expand=False
                )
                ui.console.print(syntax_panel)
                return True
            return False
        
        elif command == "WRITE":
            if not param2:
                ui.print_error("✗ WRITE command requires description")
                return False
            return handle_write_command(param1, param2)
        
        elif command == "MODIFY":
            if not param2:
                ui.print_error("✗ MODIFY command requires description")
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
                    border_style="grey50"
                )
            )
            return True
        
        return False
        
    except Exception as e:
        ui.print_error(f"✗ Command execution error: {e}")
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
        ui.print_error(f"✗ Cannot modify '{filepath}' - file not found")
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
