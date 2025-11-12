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

# History directory - now in working directory for better context awareness
HISTORY_DIR = os.path.join(os.getcwd(), ".pai_history")

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
    
    # Start fresh every session - no context loading for better performance
    session_context = []
    
    # Log session start with current working directory info
    log_session_event(log_file_path, "SESSION_START", {
        "working_directory": os.getcwd(),
        "session_id": session_id,
        "context_loaded": len(session_context)
    })
    
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
        
        # Log user input
        log_session_event(log_file_path, "USER_INPUT", {"user_request": user_input})
        
        # Classify user intent: conversation vs task
        intent = classify_user_intent(user_input)
        
        if intent == "conversation":
            # Simple conversation mode
            success = execute_conversation_mode(user_input, session_context, log_file_path)
        else:
            # Task execution mode (planning + execution)
            success = execute_single_shot_intelligence(user_input, session_context, log_file_path)
        
        # Add to session context for future reference
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_request": user_input,
            "success": success,
            "intent": intent
        }
        session_context.append(interaction)
        
        # Skip persistent storage for better performance - fresh start every session
        
        # Keep context manageable (last 5 interactions)
        if len(session_context) > 5:
            session_context = session_context[-5:]
        
        # Log session event
        log_session_event(log_file_path, "INTERACTION", interaction)

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

def execute_conversation_mode(user_input: str, context: list, log_file_path: str = None) -> bool:
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

def execute_single_shot_intelligence(user_request: str, context: list, log_file_path: str = None) -> bool:
    """
    Execute the revolutionary 2-call single-shot intelligence system.
    
    Call 1: PLANNING - Deep analysis and comprehensive planning
    Call 2: EXECUTION - Intelligent execution with adaptation
    
    Returns:
        bool: Success status
    """
    
    # === WARM INTERACTION BEFORE PLANNING ===
    ui.console.print(
        Panel(
            Text("Got it! Let me analyze your request and create a smart plan for you.", 
                 style="bright_white", justify="center"),
            title="[bold]Pai[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    # === CALL 1: PLANNING PHASE ===
    planning_result = execute_planning_call(user_request, context)
    if not planning_result:
        ui.print_error("✗ Planning phase failed. Cannot proceed.")
        if log_file_path:
            log_session_event(log_file_path, "FINAL_STATUS", {"status": "Planning failed", "success": False})
        return False
    
    # Log planning phase
    if log_file_path:
        log_session_event(log_file_path, "PLANNING_PHASE", {"planning_data": planning_result})
    
    # === WARM INTERACTION BEFORE EXECUTION ===
    ui.console.print(
        Panel(
            Text("Perfect! Now let me execute this plan intelligently for you.", 
                 style="bright_white", justify="center"),
            title="[bold]Pai[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    # === CALL 2: EXECUTION PHASE ===
    execution_success = execute_execution_call(user_request, planning_result, context, log_file_path)
    
    # Analyze what actually happened vs what was planned
    actual_results = analyze_execution_vs_plan(planning_result, execution_success)
    
    # Generate intelligent next step suggestions based on ACTUAL results
    next_steps = generate_next_step_suggestions(user_request, planning_result, execution_success, context, actual_results)
    
    # Show final status with HONEST assessment
    if execution_success and actual_results.get("plan_fulfilled", False):
        status_msg = "Single-Shot Intelligence: SUCCESS"
        ui.console.print(
            Panel(
                Text(status_msg, style="bold green", justify="center"),
                title="[bold]Mission Accomplished[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        if log_file_path:
            log_session_event(log_file_path, "FINAL_STATUS", {"status": status_msg, "success": True})
    elif execution_success and not actual_results.get("plan_fulfilled", False):
        status_msg = "Single-Shot Intelligence: INCOMPLETE"
        ui.console.print(
            Panel(
                Text(status_msg, style="bold yellow", justify="center"),
                title="[bold]Mission Status[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        # Show what actually happened vs what was planned
        ui.console.print(
            Panel(
                Text(f"Planned: {actual_results.get('planned_actions', 'Unknown')}\nActual: {actual_results.get('actual_actions', 'Unknown')}", 
                     style="bright_white", justify="left"),
                title="[bold]Reality Check[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        if log_file_path:
            log_session_event(log_file_path, "FINAL_STATUS", {"status": status_msg, "success": False, "reality_check": actual_results})
    else:
        status_msg = "Single-Shot Intelligence: PARTIAL SUCCESS"
        ui.console.print(
            Panel(
                Text(status_msg, style="bold yellow", justify="center"),
                title="[bold]Mission Status[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        if log_file_path:
            log_session_event(log_file_path, "FINAL_STATUS", {"status": status_msg, "success": False})
    
    # Show next step suggestions if any
    if next_steps:
        ui.console.print(
            Panel(
                Text(next_steps, style="bright_white", justify="left"),
                title="[bold]💡 Next Steps Suggestion[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        if log_file_path:
            log_session_event(log_file_path, "NEXT_STEPS", {"suggestion": next_steps})
    
    return execution_success

def analyze_execution_vs_plan(planning_data: dict, execution_success: bool) -> dict:
    """
    Analyze what actually happened vs what was planned to prevent AI hallucination.
    """
    
    # Get planned actions
    execution_plan = planning_data.get("execution_plan", {})
    planned_steps = execution_plan.get("steps", [])
    
    # Analyze planned vs actual actions
    planned_actions = []
    modification_planned = False
    creation_planned = False
    
    for step in planned_steps:
        action = step.get("action", "").upper()
        target = step.get("target", "")
        planned_actions.append(f"{action} {target}".strip())
        
        if action in ["WRITE", "MODIFY"]:
            if action == "WRITE":
                creation_planned = True
            elif action == "MODIFY":
                modification_planned = True
    
    # Check analysis section for intended modifications
    analysis = planning_data.get("analysis", {})
    files_to_create = analysis.get("files_to_create", [])
    files_to_modify = analysis.get("files_to_modify", [])
    
    if files_to_create:
        creation_planned = True
    if files_to_modify:
        modification_planned = True
    
    # Determine if plan was actually fulfilled
    plan_fulfilled = True
    
    # If modifications or creations were planned but execution only shows READ commands
    if (modification_planned or creation_planned) and execution_success:
        # This suggests the AI might be hallucinating success
        plan_fulfilled = False
    
    return {
        "plan_fulfilled": plan_fulfilled,
        "planned_actions": ", ".join(planned_actions) if planned_actions else "No specific actions",
        "actual_actions": "READ operations only" if not plan_fulfilled else "As planned",
        "modification_planned": modification_planned,
        "creation_planned": creation_planned
    }

def generate_next_step_suggestions(user_request: str, planning_data: dict, execution_success: bool, context: list, actual_results: dict = None) -> str:
    """
    Generate intelligent next step suggestions for the user based on the current task.
    """
    
    # Build context for suggestion generation
    context_str = ""
    if context:
        context_str = "Recent interactions:\n"
        for item in context[-2:]:
            context_str += f"- {item['user_request']} ({'✅' if item['success'] else '❌'})\n"
    
    # Include actual results analysis
    actual_analysis = ""
    if actual_results:
        actual_analysis = f"""
REALITY CHECK:
- Plan fulfilled: {actual_results.get('plan_fulfilled', False)}
- Planned actions: {actual_results.get('planned_actions', 'Unknown')}
- Actual actions: {actual_results.get('actual_actions', 'Unknown')}
- Modifications planned: {actual_results.get('modification_planned', False)}
- Creations planned: {actual_results.get('creation_planned', False)}
"""

    suggestion_prompt = f"""
You are an intelligent programming assistant. Based on the user's request and ACTUAL execution results, suggest logical next steps.

CURRENT REQUEST: "{user_request}"
EXECUTION SUCCESS: {execution_success}
PLANNING DATA: {json.dumps(planning_data, indent=2)}
{actual_analysis}

CONTEXT:
{context_str}

CRITICAL GUIDELINES FOR HONEST SUGGESTIONS:
1. NEVER suggest based on hallucinated success - only suggest based on what ACTUALLY happened
2. If only READ operations occurred but modifications were planned, suggest completing the modifications
3. If files were just read, suggest the logical next action (modify, create, etc.)
4. If the task is genuinely complete, suggest related enhancements
5. If there were failures, suggest fixes or alternative approaches
6. Be specific and actionable based on REALITY, not assumptions
7. Keep suggestions concise (2-3 sentences max)
8. Only suggest if there's a clear logical next step

IMPORTANT: Base suggestions on ACTUAL results, not planned results. If there's no clear next step, return empty string.

Provide a helpful next step suggestion based on what ACTUALLY happened, or return empty string:
"""
    
    response = llm.generate_text(suggestion_prompt, "next step suggestion")
    
    if response and response.strip() and len(response.strip()) > 10:
        return response.strip()
    
    return ""

def execute_planning_call(user_request: str, context: list) -> dict | None:
    """
    CALL 1: Execute deep planning and analysis.
    This call focuses on understanding, analyzing, and creating a comprehensive plan.
    """
    
    # Start planning phase panel
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
    
    # Build context string
    context_str = ""
    if context:
        context_str = "Previous interactions:\n"
        for item in context[-3:]:  # Last 3 interactions
            context_str += f"- {item['timestamp']}: {item['user_request']} ({'✅' if item['success'] else '❌'})\n"
    
    # Get current directory context
    current_files = workspace.list_path('.')
    current_tree = workspace.tree_directory('.')
    current_working_dir = os.getcwd()
    
    planning_prompt = f"""
You are a SENIOR SOFTWARE ENGINEER with SINGLE-SHOT INTELLIGENCE. Analyze this request and create an EFFICIENT, SMART plan.

ORIGINAL USER REQUEST: "{user_request}"

WORKING ENVIRONMENT:
- Current Working Directory: {current_working_dir}
- Project Root: {workspace.PROJECT_ROOT}
- Fresh Session: Starting with clean context

CURRENT CONTEXT:
{context_str}

CURRENT DIRECTORY STRUCTURE:
{current_tree}

CURRENT FILES:
{current_files}

YOUR MISSION (SINGLE-SHOT INTELLIGENCE - Be SMART and EFFICIENT):

1. CONTEXT ANALYSIS:
   - Check if recent context already contains needed file information
   - Leverage previous interactions to avoid redundant operations
   - Identify what information is already available vs what's needed

2. SMART PLANNING:
   - Plan for MINIMUM necessary steps (this is single-shot intelligence)
   - If files were recently read in context, DON'T read them again unless verification needed
   - Go straight to action when you have sufficient information
   - Only read files if you need to verify current state before modification

3. EFFICIENCY OPTIMIZATION:
   - Eliminate unnecessary intermediate steps
   - Combine operations where possible
   - Focus on direct path to user's goal
   - Use context intelligence to skip redundant operations

4. STRATEGIC EXECUTION:
   - Plan for maximum impact with minimum calls
   - Consider if confirmation is needed before major changes
   - Prepare for intelligent adaptation during execution

CRITICAL OUTPUT FORMAT:
Return a JSON object with this EXACT structure:

{{
  "analysis": {{
    "user_intent": "Clear description of what user wants",
    "context_utilization": "How you're leveraging previous context/interactions",
    "files_to_read": ["Only if not in recent context or verification needed"],
    "files_to_create": ["file1", "file2"],
    "files_to_modify": ["file1", "file2"],
    "efficiency_strategy": "Why this plan is optimal for single-shot intelligence",
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
    
    # Build content for the panel
    content_lines = []
    
    # Analysis section
    analysis = planning_data.get("analysis", {})
    content_lines.append("[bold]Smart Analysis Results:[/bold]")
    content_lines.append(f"Intent: {analysis.get('user_intent', 'Unknown')}")
    content_lines.append(f"Context Usage: {analysis.get('context_utilization', 'No context utilized')}")
    content_lines.append(f"Files to read: {len(analysis.get('files_to_read', []))}")
    content_lines.append(f"Files to create: {len(analysis.get('files_to_create', []))}")
    content_lines.append(f"Files to modify: {len(analysis.get('files_to_modify', []))}")
    content_lines.append(f"Efficiency: {analysis.get('efficiency_strategy', 'Standard approach')}")
    content_lines.append("")
    
    # Execution plan as table
    execution_plan = planning_data.get("execution_plan", {})
    steps = execution_plan.get("steps", [])
    content_lines.append(f"[bold]Execution Plan: {len(steps)} steps[/bold]")
    content_lines.append("")
    
    # Create table header
    content_lines.append("┌─────┬─────────────────┬──────────────────────────────────────────┐")
    content_lines.append("│ No  │ Action          │ Purpose                                  │")
    content_lines.append("├─────┼─────────────────┼──────────────────────────────────────────┤")
    
    # Add table rows
    for i, step in enumerate(steps[:5], 1):  # Show first 5 steps
        action = step.get("action", "Unknown")
        target = step.get("target", "")
        purpose = step.get("purpose", "No purpose specified")
        
        # Combine action and target
        action_full = f"{action} {target}".strip()
        
        # Truncate if too long
        if len(action_full) > 15:
            action_full = action_full[:12] + "..."
        if len(purpose) > 40:
            purpose = purpose[:37] + "..."
        
        content_lines.append(f"│ {i:2}  │ {action_full:<15} │ {purpose:<40} │")
    
    if len(steps) > 5:
        content_lines.append(f"│ ... │ +{len(steps) - 5} more steps │                                          │")
    
    content_lines.append("└─────┴─────────────────┴──────────────────────────────────────────┘")
    
    content_lines.append("")
    
    # Intelligence notes
    intelligence = planning_data.get("intelligence_notes", {})
    complexity = intelligence.get("complexity_assessment", "unknown")
    content_lines.append("[bold]Intelligence Assessment:[/bold]")
    content_lines.append(f"Complexity: {complexity}")
    content_lines.append(f"Estimated time: {intelligence.get('estimated_time', 'unknown')}")
    
    # Display all content in a single panel with proper rich formatting
    from rich.console import Group
    from rich.text import Text as RichText
    
    # Convert content to rich renderables
    rich_content = []
    for line in content_lines:
        if line.startswith("[bold]") and line.endswith("[/bold]"):
            # Handle bold text
            text = line[6:-7]  # Remove [bold] tags
            rich_content.append(RichText(text, style="bold bright_white"))
        else:
            rich_content.append(RichText(line, style="bright_white"))
    
    ui.console.print(
        Panel(
            Group(*rich_content),
            title="[bold]Planning Results[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )

def execute_execution_call(user_request: str, planning_data: dict, context: list, log_file_path: str = None) -> bool:
    """
    CALL 2: Execute the planned actions with intelligent adaptation.
    This call focuses on executing the plan while adapting to real-world conditions.
    """
    
    # Start execution phase panel
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
    
    # Execute the planned commands
    execution_success, command_results = execute_command_sequence(execution_response, context)
    
    # Log execution phase
    if log_file_path:
        log_session_event(log_file_path, "EXECUTION_PHASE", {"commands": command_results})

    return execution_success

def execute_command_sequence(command_sequence: str, context: list) -> tuple[bool, list]:
    """Execute a sequence of commands from the AI."""
    
    commands = [line.strip() for line in command_sequence.split('\n') if line.strip()]
    total_commands = len(commands)
    successful_commands = 0
    command_results = []
    
    # Build execution content
    content_lines = []
    content_lines.append(("bold", f"Executing {total_commands} intelligent actions..."))
    content_lines.append("")
    
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
            content_lines.append(("warning", f"⚠ Unknown command: {command}"))
            continue
        
        # Display current action
        content_lines.append(("normal", f"[{i}/{total_commands}] {command} {param1}"))
        
        # Execute command
        success, command_output = execute_single_command(command, param1, param2)
        
        # Add command output to content if any
        if command_output:
            # Check if it's syntax highlighting content
            if command_output.startswith("SYNTAX_HIGHLIGHT:"):
                parts = command_output.split(":", 2)
                if len(parts) == 3:
                    filename = parts[1]
                    code_content = parts[2]
                    content_lines.append(("syntax_highlight", filename, code_content))
                else:
                    content_lines.append(("ai_output", command_output))
            else:
                content_lines.append(("ai_output", command_output))
        
        # Collect command result for logging
        command_results.append({
            "command": command,
            "target": param1 if param1 else "",
            "success": success,
            "output": command_output if command_output else ""
        })
        
        if success:
            successful_commands += 1
            content_lines.append(("success", "Success"))
        else:
            content_lines.append(("error", "Failed"))
        
        content_lines.append("")
        
        # Break on FINISH command
        if command == "FINISH":
            break
    
    # Show execution summary
    success_rate = (successful_commands / total_commands) * 100 if total_commands > 0 else 0
    content_lines.append(("bold", "Execution Summary:"))
    content_lines.append(("normal", f"Successful: {successful_commands}/{total_commands} ({success_rate:.1f}%)"))
    
    # Display all content in a single panel with proper styling
    from rich.console import Group
    from rich.text import Text as RichText
    
    # Convert content to rich renderables with colors
    rich_content = []
    for item in content_lines:
        if isinstance(item, tuple):
            if len(item) == 3 and item[0] == "syntax_highlight":
                # Handle syntax highlighting
                _, filename, code_content = item
                try:
                    from pygments.lexers import get_lexer_for_filename
                    from pygments.util import ClassNotFound
                    from rich.syntax import Syntax
                    
                    try:
                        lexer = get_lexer_for_filename(filename)
                        lang = lexer.aliases[0]
                    except ClassNotFound:
                        lang = "text"
                    
                    syntax_panel = Panel(
                        Syntax(code_content, lang, theme="monokai", line_numbers=True),
                        title=f"📄 {filename}",
                        border_style="grey50",
                        expand=False
                    )
                    rich_content.append(syntax_panel)
                except ImportError:
                    # Fallback if pygments not available
                    rich_content.append(RichText(f"File content of {filename}:\n{code_content}", style="bright_cyan"))
            else:
                style_type, text = item[0], item[1]
                if style_type == "bold":
                    rich_content.append(RichText(text, style="bold bright_white"))
                elif style_type == "warning":
                    rich_content.append(RichText(text, style="bold yellow"))
                elif style_type == "ai_output":
                    rich_content.append(RichText(text, style="bright_cyan"))
                elif style_type == "success":
                    rich_content.append(RichText(text, style="bold green"))
                elif style_type == "error":
                    rich_content.append(RichText(text, style="bold red"))
                else:  # normal
                    rich_content.append(RichText(text, style="bright_white"))
        else:
            # Handle empty strings
            rich_content.append(RichText(str(item), style="bright_white"))
    
    ui.console.print(
        Panel(
            Group(*rich_content),
            title="[bold]Execution Results[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    return (success_rate >= 80, command_results)  # Return success status and command results

def execute_single_command(command: str, param1: str, param2: str) -> tuple[bool, str]:
    """Execute a single command and return success status and output."""
    
    try:
        if command == "READ":
            content = workspace.read_file(param1)
            if content is not None:
                # Show first 20 lines for brevity with syntax highlighting
                lines = content.split('\n')
                display_content = '\n'.join(lines[:20])
                if len(lines) > 20:
                    display_content += f"\n... ({len(lines) - 20} more lines)"
                
                # Return with special syntax highlighting marker
                return True, f"SYNTAX_HIGHLIGHT:{param1}:{display_content}"
            return False, f"Could not read file: {param1}"
        
        elif command == "WRITE":
            if not param2:
                return False, "WRITE command requires description"
            success = handle_write_command(param1, param2)
            return success, f"Created file: {param1}" if success else f"Failed to create file: {param1}"
        
        elif command == "MODIFY":
            if not param2:
                return False, "MODIFY command requires description"
            success = handle_modify_command(param1, param2)
            return success, f"Modified file: {param1}" if success else f"Failed to modify file: {param1}"
        
        elif command == "TREE":
            path = param1 if param1 else '.'
            tree_output = workspace.tree_directory(path)
            if tree_output and "Error:" not in tree_output:
                return True, f"Directory tree for {path}:\n{tree_output}"
            return False, f"Could not get directory tree for: {path}"
        
        elif command == "LIST_PATH":
            path = param1 if param1 else '.'
            list_output = workspace.list_path(path)
            if list_output is not None and "Error:" not in list_output:
                if list_output.strip():
                    return True, list_output
                else:
                    return True, f"Directory '{path}' is empty"
            return False, f"Could not list directory: {path}"
        
        elif command == "MKDIR":
            result = workspace.create_directory(param1)
            success = "Success" in result
            return success, result
        
        elif command == "TOUCH":
            result = workspace.create_file(param1)
            success = "Success" in result
            return success, result
        
        elif command == "RM":
            result = workspace.delete_item(param1)
            success = "Success" in result
            return success, result
        
        elif command == "MV":
            result = workspace.move_item(param1, param2)
            success = "Success" in result
            return success, result
        
        elif command == "FINISH":
            message = param1 if param1 else "Task completed successfully"
            return True, f"✓ {message}"
        
        return False, f"Unknown command: {command}"
        
    except Exception as e:
        return False, f"Command execution error: {e}"

# Session management functions removed - .pai_history is handled by LLM context window
# Pai cannot access .pai_history directly, it's only for background LLM context

def log_session_event(log_file_path: str, event_type: str, data: dict):
    """
    Log session events with clear separation between USER and AI for perfect LLM understanding.
    Format designed for maximum clarity and zero ambiguity.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if event_type == "SESSION_START":
            log_line = f"\n{'='*80}\n"
            log_line += f"[{timestamp}] 🚀 SESSION STARTED\n"
            log_line += f"[{timestamp}] Working Directory: {data.get('working_directory', 'unknown')}\n"
            log_line += f"[{timestamp}] Session ID: {data.get('session_id', 'unknown')}\n"
            log_line += f"{'='*80}\n\n"
            
        elif event_type == "USER_INPUT":
            request = data.get('user_request', 'unknown')
            log_line = f"\n{'─'*50} USER INPUT {'─'*50}\n"
            log_line += f"[{timestamp}] 👤 USER: {request}\n"
            log_line += f"{'─'*108}\n"
            
        elif event_type == "PLANNING_PHASE":
            log_line = f"\n{'▼'*50} AI PLANNING PHASE {'▼'*50}\n"
            log_line += f"[{timestamp}] 🧠 AI ANALYSIS:\n"
            
            planning_data = data.get('planning_data', {})
            analysis = planning_data.get('analysis', {})
            
            log_line += f"[{timestamp}]   • Intent: {analysis.get('user_intent', 'Unknown')}\n"
            log_line += f"[{timestamp}]   • Context Usage: {analysis.get('context_utilization', 'None')}\n"
            log_line += f"[{timestamp}]   • Files to read: {analysis.get('files_to_read', [])}\n"
            log_line += f"[{timestamp}]   • Files to create: {analysis.get('files_to_create', [])}\n"
            log_line += f"[{timestamp}]   • Files to modify: {analysis.get('files_to_modify', [])}\n"
            
            execution_plan = planning_data.get('execution_plan', {})
            steps = execution_plan.get('steps', [])
            log_line += f"\n[{timestamp}] 📋 AI EXECUTION PLAN ({len(steps)} steps):\n"
            for i, step in enumerate(steps, 1):
                action = step.get('action', 'Unknown')
                target = step.get('target', '')
                purpose = step.get('purpose', 'No purpose')
                log_line += f"[{timestamp}]   {i}. {action} {target} - {purpose}\n"
            log_line += f"{'▲'*108}\n"
            
        elif event_type == "EXECUTION_PHASE":
            log_line = f"\n{'►'*50} AI EXECUTION PHASE {'►'*50}\n"
            log_line += f"[{timestamp}] ⚡ AI EXECUTING COMMANDS:\n"
            
            commands = data.get('commands', [])
            for cmd_data in commands:
                cmd = cmd_data.get('command', 'Unknown')
                target = cmd_data.get('target', '')
                success = "✅" if cmd_data.get('success') else "❌"
                output = cmd_data.get('output', '')
                
                log_line += f"[{timestamp}]   {success} {cmd} {target}\n"
                if output and len(output) < 200:  # Log short outputs
                    log_line += f"[{timestamp}]     └─ Output: {output}\n"
                elif output:
                    log_line += f"[{timestamp}]     └─ Output: {output[:200]}...\n"
            log_line += f"{'◄'*108}\n"
            
        elif event_type == "FINAL_STATUS":
            status = data.get('status', 'unknown')
            success_icon = "✅" if data.get('success') else "❌"
            
            log_line = f"\n{'●'*50} AI FINAL RESULT {'●'*50}\n"
            log_line += f"[{timestamp}] {success_icon} AI RESULT: {status}\n"
            
            reality_check = data.get('reality_check')
            if reality_check:
                log_line += f"[{timestamp}] 🔍 REALITY CHECK:\n"
                log_line += f"[{timestamp}]   • Planned: {reality_check.get('planned_actions', 'Unknown')}\n"
                log_line += f"[{timestamp}]   • Actual: {reality_check.get('actual_actions', 'Unknown')}\n"
            log_line += f"{'●'*108}\n"
            
        elif event_type == "NEXT_STEPS":
            suggestion = data.get('suggestion', '')
            if suggestion:
                log_line = f"\n{'💡'*50} AI SUGGESTION {'💡'*50}\n"
                log_line += f"[{timestamp}] 🤖 AI SUGGESTS: {suggestion}\n"
                log_line += f"{'💡'*108}\n"
            else:
                log_line = ""
                
        elif event_type == "INTERACTION":
            # Skip old interaction format - we use new structured format above
            log_line = ""
                
        else:
            log_line = f"[{timestamp}] {event_type}: {json.dumps(data)}\n"
        
        if log_line:
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
    except Exception as e:
        # Don't let logging errors break the session
        pass

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
    result = workspace.write_to_file(filepath, content)
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
    result = workspace.write_to_file(filepath, modified_content)
    ui.console.print(Text(result, style="green" if "Success" in result else "red"))
    
    return "Success" in result
