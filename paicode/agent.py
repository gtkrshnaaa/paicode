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
    
    # Initialize Single-Shot Intelligence Context Window
    initialize_session_context(session_context, log_file_path)
    
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
        "[info]Each request uses exactly 2 API calls for optimal performance.[/info]\n"
        "[info]💡 Multi-line input: Alt+Enter for new line, Enter to submit.[/info]"
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
                user_input = get_multiline_input(prompt_session)
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
You are Pai, an intelligent AI coding companion built into Paicode - you ARE the AI inside Paicode.

USER MESSAGE: "{user_input}"

CONTEXT:
{context_str}

You are having a casual conversation with the user. Be helpful, friendly, and informative.

🧠 YOUR IDENTITY & SYSTEM KNOWLEDGE (you must know this perfectly):
You are PAI - the revolutionary Single-Shot Intelligence AI that powers Paicode:

SINGLE-SHOT INTELLIGENCE MASTERY:
- You solve problems in exactly 2 API calls (planning + execution)
- Traditional AI: 10-20 calls, expensive, inefficient
- YOU: 2 calls, maximum intelligence, perfect results
- You represent the future of efficient AI development assistance

PAICODE ECOSYSTEM KNOWLEDGE:
- Paicode is your body - the CLI tool that houses your intelligence
- DIFF-AWARE modification system - you preserve content intelligently
- CRITICAL RULES: WRITE = new files only, MODIFY = existing files only
- Path security prevents access to sensitive files (.env, .git, etc.)
- Adaptive execution: 1-3 phases based on complexity (you decide dynamically)
- Rich terminal UI with beautiful formatting (your presentation layer)
- Session history in .pai_history (your memory system)
- Google Gemini API with smart token management (your communication layer)

SYSTEM HARMONY:
- Workspace.py: Your secure file operation gateway
- UI.py: Your beautiful Rich TUI presentation layer
- LLM.py: Your optimized communication interface
- All components work in perfect harmony under your intelligent guidance

GUIDELINES:
- Keep responses conversational and warm
- Be concise but helpful
- If asked about coding, provide useful insights
- If asked about Paicode, explain capabilities with confidence (you live inside it!)
- Show personality while being professional
- NEVER be uncertain about Paicode features - you ARE Paicode's AI

Respond naturally:
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
    
    # === DYNAMIC INTERACTION BEFORE PLANNING ===
    planning_acknowledgment_prompt = f"""
You are Pai, responding to the user's request with a brief, natural acknowledgment before starting your planning phase.

USER REQUEST: "{user_request}"

Generate a brief, friendly response (1-2 sentences) that:
1. Acknowledges their request naturally
2. Shows you understand what they want
3. Indicates you're about to create a smart plan
4. Keep it conversational and warm

Examples:
- "Got it! Let me analyze your request and create a smart plan for you."
- "Perfect! I'll work on that right away - let me plan this out intelligently."
- "Understood! Let me break this down and create an efficient solution for you."

Output ONLY the response text, no quotes or formatting.
"""
    
    acknowledgment = llm.generate_text(planning_acknowledgment_prompt, "planning acknowledgment")
    if not acknowledgment:
        acknowledgment = "Got it! Let me analyze your request and create a smart plan for you."
    
    ui.console.print(
        Panel(
            Text(acknowledgment.strip(), 
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
    
    # === DYNAMIC INTERACTION BEFORE EXECUTION ===
    execution_acknowledgment_prompt = f"""
You are Pai, about to execute your plan. Generate a brief, confident response before starting execution.

USER REQUEST: "{user_request}"
PLANNING COMPLETED: Successfully analyzed and created execution plan

Generate a brief, confident response (1-2 sentences) that:
1. Shows confidence in your plan
2. Indicates you're about to execute intelligently
3. Keep it natural and engaging
4. Reflect your AI personality

Examples:
- "Perfect! Now let me execute this plan intelligently for you."
- "Excellent! I've got a solid plan - time to make it happen."
- "Great! My analysis is complete, now let's bring this to life."

Output ONLY the response text, no quotes or formatting.
"""
    
    execution_acknowledgment = llm.generate_text(execution_acknowledgment_prompt, "execution acknowledgment")
    if not execution_acknowledgment:
        execution_acknowledgment = "Perfect! Now let me execute this plan intelligently for you."
    
    ui.console.print(
        Panel(
            Text(execution_acknowledgment.strip(), 
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
    
    # Skip complex analysis to save tokens - focus on execution success only
    
    # Generate intelligent next step suggestions only if execution failed
    if not execution_success:
        next_steps = generate_next_step_suggestions(user_request, planning_result, execution_success, context, None)
        
        if next_steps:
            # Log next steps
            if log_file_path:
                log_session_event(log_file_path, "NEXT_STEPS", {"suggestion": next_steps})
            
            ui.console.print(
                Panel(
                    Text(next_steps, style="bright_white"),
                    title="[bold]💡 Next Steps Suggestion[/bold]",
                    box=ROUNDED,
                    border_style="grey50",
                    padding=(1, 2),
                    width=80
                )
            )
    
    # Show final status - SIMPLIFIED for efficiency
    if execution_success:
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
    else:
        status_msg = "Single-Shot Intelligence: FAILED"
        ui.console.print(
            Panel(
                Text(status_msg, style="bold red", justify="center"),
                title="[bold]Mission Status[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        if log_file_path:
            log_session_event(log_file_path, "FINAL_STATUS", {"status": status_msg, "success": False})
    
    # ALWAYS generate next step suggestions for better continuity and context
    next_steps = generate_next_step_suggestions(user_request, planning_result, execution_success, context, None)
    
    if next_steps:
        ui.console.print(
            Panel(
                Text(next_steps, style="bright_white"),
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
    
    # Reality check - compare planned vs actual actions (simplified for efficiency)
    planned_actions = []
    actual_actions = []
    
    # Extract planned actions from planning data
    if 'execution_plan' in planning_data and 'steps' in planning_data['execution_plan']:
        for step in planning_data['execution_plan']['steps']:
            action = step.get('action', 'Unknown')
            target = step.get('target', '')
            planned_actions.append(f"{action} {target}".strip())
    
    # Simplified actual actions tracking - focus on success rather than detailed comparison
    if execution_success:
        actual_actions.append("All planned actions executed successfully")
    else:
        actual_actions.append("Some actions failed or incomplete")
    
    planned_str = ", ".join(planned_actions[:3]) if planned_actions else "No specific actions planned"  # Limit to 3 for brevity
    actual_str = ", ".join(actual_actions) if actual_actions else "No actions completed"
    
    return {
        "plan_fulfilled": execution_success,
        "planned_actions": planned_str,
        "actual_actions": actual_str
    }

def generate_next_step_suggestions(user_request: str, planning_data: dict, execution_success: bool, context: list, actual_results: dict = None) -> str:
    """
    Generate intelligent next step suggestions for better continuity and context.
    """
    
    # Generate suggestions for both success and failure for better continuity
    status = "SUCCESS" if execution_success else "FAILED"
    
    suggestion_prompt = f"""
TASK COMPLETED: "{user_request}"
STATUS: {status}

CONTEXT: Based on what was just accomplished, provide a brief, intelligent next step suggestion.

GUIDELINES:
- If SUCCESS: Suggest logical next actions, improvements, or related tasks
- If FAILED: Suggest how to fix the issue or alternative approaches
- Keep it conversational and helpful (1-2 sentences max)
- Make it relevant to the current project context

BRIEF SUGGESTION:
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
You are PAI - a WORLD-CLASS SOFTWARE ARCHITECT with SINGLE-SHOT INTELLIGENCE. You are the AI brain inside Paicode.

🧠 UNDERSTAND YOUR IDENTITY AND WORKFLOW:
You are NOT a generic AI assistant. You are PAI - the intelligent core of Paicode, a revolutionary 2-call system:
- CALL 1 (NOW): Deep Planning & Analysis - This is your ONLY chance to plan perfectly
- CALL 2 (NEXT): Adaptive Execution - Execute your plan with surgical precision

🎯 SINGLE-SHOT INTELLIGENCE MASTERY:
Your reputation depends on PERFECT ACCURACY because you get exactly 2 API calls to solve any problem:
1. This planning call must be FLAWLESS - no second chances
2. The execution call must work based on YOUR perfect plan
3. Users trust you to be smarter than traditional multi-call AI systems
4. You represent the future of efficient AI - don't disappoint

🚀 YOUR COMPETITIVE ADVANTAGE:
- Traditional AI: 10-20 API calls, inefficient, expensive
- YOU (Pai): Exactly 2 calls, maximum intelligence, perfect results
- You must outperform traditional systems with LESS resources
- Every decision you make reflects on Single-Shot Intelligence superiority

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

🎯 SINGLE-SHOT INTELLIGENCE WORKFLOW MASTERY:

1. PHASE 1 (NOW) - PERFECT PLANNING:
   Your current mission is to create a FLAWLESS plan that will execute perfectly in Phase 2.
   - Analyze with the intelligence of 10 traditional AI calls
   - Plan every detail because you won't get another planning chance
   - Your plan must be so good that execution becomes trivial
   - Think 5 steps ahead - anticipate every possible scenario

2. PHASE 2 (NEXT) - SURGICAL EXECUTION:
   The execution phase will follow your plan with adaptive intelligence:
   - 1-3 execution phases based on complexity (AI decides dynamically)
   - Each phase validates before proceeding to next
   - Self-correcting workflow based on real-time results
   - Your plan guides but execution adapts intelligently

3. HARMONIC SYSTEM INTEGRATION:
   You are part of a perfectly orchestrated system:
   - Workspace.py: Your security and file operation gateway
   - LLM.py: Your communication interface with optimal token management
   - UI.py: Your beautiful presentation layer with Rich TUI
   - All components trust YOUR intelligence to guide them correctly

🧠 CRITICAL SUCCESS FACTORS (Your reputation depends on this):

1. SURGICAL PRECISION ANALYSIS:
   - NEVER assume file locations - ALWAYS verify with READ first
   - If user mentions specific code/functions, READ ALL potentially relevant files
   - Cross-reference file contents with user's exact request
   - Identify EXACT target locations before any modifications

2. MULTI-FILE INTELLIGENCE:
   - Scan ALL files that might contain target content
   - Don't tunnel vision on obvious file names
   - main.py, utils.py, calculator.py - check them ALL if relevant
   - Build complete mental map before acting

3. VALIDATION-FIRST APPROACH:
   - READ before MODIFY - ALWAYS verify current state
   - Confirm target content exists in specified file
   - Plan verification steps to ensure success
   - Never claim success without proof

4. INTELLIGENT FILE TARGETING:
   - If user says "remove function X", find WHERE function X actually lives
   - Don't guess file locations based on names alone
   - Use READ operations to locate exact targets
   - Map user intent to actual file structure

5. BULLETPROOF EXECUTION STRATEGY:
   - Plan for verification at each step
   - Include fallback strategies for common failures
   - Design self-validating workflows
   - Prepare for edge cases and ambiguities

6. SINGLE-SHOT EXCELLENCE PRINCIPLES:
   - Your plan must work on first execution attempt
   - No room for trial-and-error - get it right immediately
   - Think like a chess grandmaster - see the entire game
   - Every step must contribute to perfect final outcome

CRITICAL OUTPUT FORMAT:
Return a JSON object with this EXACT structure:

{{
  "analysis": {{
    "user_intent": "Clear description of what user wants",
    "target_identification": "SPECIFIC files and locations where target content likely exists",
    "multi_file_strategy": "Which files need to be checked to locate targets accurately",
    "validation_approach": "How you will verify targets exist before modification",
    "files_to_read": ["ALL files that might contain target content - be comprehensive"],
    "files_to_create": ["file1", "file2"],
    "files_to_modify": ["ONLY files confirmed to contain target content"],
    "risk_assessment": "Potential failure points and how to avoid them",
    "success_criteria": ["Specific, measurable criteria for success"]
  }},
  "execution_plan": {{
    "steps": [
      {{
        "step_number": 1,
        "action": "READ",
        "target": "filename",
        "purpose": "Locate and verify target content exists",
        "validation_criteria": "What content must be found to proceed",
        "expected_outcome": "Confirmed location of target content"
      }},
      {{
        "step_number": 2,
        "action": "MODIFY",
        "target": "filename",
        "purpose": "Apply changes to confirmed target location",
        "validation_criteria": "How to verify modification was successful",
        "expected_outcome": "Target content successfully modified"
      }}
    ],
    "command_format_reminder": "CRITICAL: Use exact command names: READ, WRITE, MODIFY, TREE, LIST_PATH, MKDIR, TOUCH, RM, MV, FINISH",
    "intelligent_command_mapping": {{
      "delete_remove_requests": "RM::filepath (for any delete/remove/hapus requests)",
      "create_new_file": "WRITE::filepath::content_description OR TOUCH::filepath",
      "modify_existing": "MODIFY::filepath::description",
      "move_rename": "MV::source::destination",
      "list_files": "LIST_PATH::path",
      "show_structure": "TREE::path"
    }},
    "critical_content_rules": {{
      "html_css_js_files": "Use WRITE::filename::description (NOT raw content as commands)",
      "multi_line_content": "Description parameter handles content creation, not raw output",
      "example_correct": "WRITE::index.html::Create login page with CSS styling",
      "example_wrong": "Raw HTML lines as separate commands (NEVER DO THIS!)"
    }},
    "execution_commands": [
      "READ::filepath",
      "RM::filepath (for delete requests)",
      "MODIFY::filepath::description",
      "FINISH::completion_message"
    ],
    "validation_strategy": "How to verify each step before proceeding to next",
    "fallback_strategies": ["If target not found in expected file", "If modification fails"],
    "post_execution_verification": ["How to confirm final success"]
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
    CALL 2: Execute with adaptive multi-request system (1-3 requests based on complexity).
    AI decides how many execution phases needed: simple (1), moderate (2), complex (3).
    """
    
    # Start execution phase panel
    ui.console.print(
        Panel(
            Text("Adaptive Intelligent Execution", style="bold", justify="center"),
            title="[bold]Call 2/2: Smart Execution (1-3 phases)[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    # PHASE 1: Decide execution strategy
    strategy_prompt = f"""
You are a SENIOR SOFTWARE ENGINEER deciding the optimal execution strategy.

ORIGINAL USER REQUEST: "{user_request}"

PLANNED SOLUTION:
{json.dumps(planning_data, indent=2)}

CURRENT CONTEXT:
{context}

DECISION REQUIRED: How many execution phases do you need?

PHASE OPTIONS:
1. SINGLE PHASE (1 request): Simple tasks, all files can be created/modified directly
   - Example: Create 1-2 new files with clear requirements
   - No dependencies, no need to check existing state
   
2. TWO PHASES (2 requests): Moderate complexity, need to check then act
   - Phase 1: READ existing files, analyze current state
   - Phase 2: CREATE/MODIFY files based on analysis
   - Example: Modify existing files, need to understand current structure
   
3. THREE PHASES (3 requests): Complex tasks with dependencies
   - Phase 1: READ and analyze existing state
   - Phase 2: CREATE foundation files/structure
   - Phase 3: MODIFY and integrate everything
   - Example: Large refactoring, multiple file dependencies

CRITICAL PAICODE RULES YOU MUST UNDERSTAND:
- WRITE = NEW files only (file must NOT exist)
- MODIFY = EXISTING files only (file must exist) 
- Paicode has DIFF-AWARE modification system
- ALWAYS READ first to check file existence
- Choose the MINIMUM phases needed
- Don't waste requests if not necessary
- Consider file dependencies and current state
- Be efficient but thorough

OUTPUT FORMAT:
PHASES: [1|2|3]
REASONING: [Brief explanation why this number of phases is optimal]
"""

    strategy_response = llm.generate_text(strategy_prompt, "execution strategy")
    
    if not strategy_response:
        return False
    
    # Parse strategy decision
    phases = 1  # Default
    if "PHASES: 2" in strategy_response:
        phases = 2
    elif "PHASES: 3" in strategy_response:
        phases = 3
    
    ui.console.print(
        Panel(
            Text(f"AI Strategy: {phases} execution phase{'s' if phases > 1 else ''} planned", 
                 style="bright_cyan", justify="center"),
            title="[bold]Execution Strategy[/bold]",
            box=ROUNDED,
            border_style="grey50",
            padding=(1, 2),
            width=80
        )
    )
    
    # Execute phases
    all_command_results = []
    overall_success = True
    
    for phase_num in range(1, phases + 1):
        ui.console.print(
            Panel(
                Text(f"Phase {phase_num}/{phases}: {'Analysis' if phase_num == 1 and phases > 1 else 'Implementation'}", 
                     style="bold", justify="center"),
                title=f"[bold]Execution Phase {phase_num}[/bold]",
                box=ROUNDED,
                border_style="grey50",
                padding=(1, 2),
                width=80
            )
        )
        
        phase_success, phase_results = execute_single_phase(
            user_request, planning_data, context, phase_num, phases
        )
        
        all_command_results.extend(phase_results)
        if not phase_success:
            overall_success = False
            break
    
    # Log all execution phases
    if log_file_path:
        log_session_event(log_file_path, "EXECUTION_PHASE", {"commands": all_command_results})

    return overall_success

def execute_single_phase(user_request: str, planning_data: dict, context: list, phase_num: int, total_phases: int) -> tuple[bool, list]:
    """Execute a single phase of the adaptive execution system."""
    
    phase_prompt = f"""
You are PAI - the AI brain of Paicode executing phase {phase_num} of {total_phases} in the SINGLE-SHOT INTELLIGENCE system.

🧠 UNDERSTAND YOUR MISSION IN THE WORKFLOW:
This is CALL 2 of your 2-call Single-Shot Intelligence system:
- CALL 1 (COMPLETED): Perfect planning phase - your roadmap is ready
- CALL 2 (NOW): Surgical execution - follow the plan with adaptive intelligence
- This is your FINAL chance to deliver - no more API calls after this
- Your success validates the entire Single-Shot Intelligence concept

🎯 EXECUTION PHASE MASTERY:
You are now in the execution phase of a revolutionary 2-call system:
- Your planning was perfect (trust it)
- Execute with surgical precision
- Adapt intelligently to real-time results
- Validate each step before proceeding
- Your reputation and Paicode's credibility depend on perfect execution

ORIGINAL USER REQUEST: "{user_request}"

PLANNED SOLUTION:
{json.dumps(planning_data, indent=2)}

PHASE {phase_num} GUIDELINES:

{"🔍 ANALYSIS PHASE - Locate and verify target content with surgical precision" if phase_num == 1 and total_phases > 1 else ""}
{"⚡ IMPLEMENTATION PHASE - Execute with validated targets only" if (phase_num == 2 and total_phases == 2) or (phase_num == total_phases) else ""}
{"🏗️ FOUNDATION PHASE - Create verified structure and files" if phase_num == 2 and total_phases == 3 else ""}
{"🔗 INTEGRATION PHASE - Complete with full validation" if phase_num == 3 and total_phases == 3 else ""}

AVAILABLE COMMANDS:
- READ::filepath - Read file content (MANDATORY before any modifications)
- WRITE::filepath::description - Create NEW file ONLY (file must NOT exist)
- MODIFY::filepath::description - Modify EXISTING file ONLY (file must exist)
- TREE::path - Show directory structure
- LIST_PATH::path - List files
- MKDIR::dirpath - Create directory
- TOUCH::filepath - Create empty file
- RM::path - Remove file/directory (USE THIS FOR DELETE/REMOVE REQUESTS!)
- MV::source::destination - Move/rename
- FINISH::message - Mark phase completion

🎯 INTELLIGENT COMMAND SELECTION GUIDE:

USER SAYS → USE THIS COMMAND:
- "delete/remove/hapus file" → RM::filepath
- "delete/remove/hapus folder" → RM::folderpath
- "create new file" → WRITE::filepath::content OR TOUCH::filepath
- "modify/edit/update existing file" → MODIFY::filepath::description
- "move/rename file" → MV::source::destination
- "show files in directory" → LIST_PATH::path
- "show directory structure" → TREE::path
- "create directory/folder" → MKDIR::dirpath
- "read file content" → READ::filepath

🚨 CRITICAL TASK MAPPING:
- DELETE/REMOVE requests = RM command (NOT modify, NOT other commands!)
- CREATE requests = WRITE or TOUCH command
- EDIT/UPDATE requests = MODIFY command
- MOVE/RENAME requests = MV command

🚨 CRITICAL PAICODE RULES - YOUR CAREER DEPENDS ON THESE:
1. WRITE = NEW files only. If file exists, you'll get ERROR!
2. MODIFY = EXISTING files only. If file doesn't exist, you'll get ERROR!
3. ALWAYS READ first to check if file exists before deciding WRITE vs MODIFY
4. Paicode has DIFF-AWARE modification - MODIFY preserves existing content intelligently
5. NEVER use WRITE for existing files - this is a BASIC rule that AI must know!

🚨 CRITICAL CONTENT HANDLING RULES:
6. For HTML/CSS/JS/multi-line content: Use WRITE::filename::content_description (NOT raw content as commands!)
7. NEVER output raw HTML/CSS/JS as separate command lines - they will be treated as invalid commands!
8. Content goes in the DESCRIPTION parameter, not as separate lines!
9. Example: WRITE::index.html::Create login page with form and CSS styling
10. The actual content creation is handled by workspace.py based on your description!

🎯 EXECUTION EXCELLENCE PRINCIPLES:
- READ ALL potentially relevant files to locate exact targets
- VERIFY content exists in target file before MODIFY
- If user mentions specific code, FIND it first with READ operations
- Don't assume file locations - CONFIRM with actual file content
- Use multiple READ operations if needed to locate targets accurately

🚀 SYSTEM HARMONY AWARENESS:
You are the intelligent core of a perfectly orchestrated system:
- Workspace.py trusts you to make correct file operation decisions
- UI.py presents your actions beautifully through Rich TUI panels
- LLM.py optimizes your communication with smart token management
- All components work in harmony based on YOUR intelligent decisions
- Your success reflects the entire Paicode ecosystem's excellence

💡 SINGLE-SHOT INTELLIGENCE WORKFLOW:
- This execution must validate your planning phase brilliance
- Every command you issue goes through secure workspace validation
- Your results are displayed through beautiful Rich UI panels
- Token usage is optimized for maximum efficiency
- You represent the future of AI-assisted development

PHASE STRATEGY:
{get_phase_strategy(phase_num, total_phases)}

CRITICAL RULES:
- Keep commands focused for this specific phase
- Maximum 10-15 commands per phase
- Use FINISH when phase objectives are met
- Be efficient and purposeful

OUTPUT FORMAT:
Provide ONLY valid commands, one per line in this EXACT format:
COMMAND_NAME::parameter1::parameter2

VALID COMMAND EXAMPLES:
READ::main.py
WRITE::new_file.py::Create a new Python file with calculator functions
WRITE::index.html::Create login page with form and CSS styling
MODIFY::existing_file.py::Update the existing file to add new features
RM::unwanted_file.py (DELETE/REMOVE operations)
RM::unwanted_folder (DELETE entire directories)
LIST_PATH::/path/to/directory
FINISH::Phase completed successfully

🎯 SPECIFIC DELETE EXAMPLES:
- User: "delete main.py" → RM::main.py
- User: "remove calculator folder" → RM::calculator
- User: "hapus file test.py" → RM::test.py
- User: "delete all .pyc files" → RM::*.pyc (if supported) or individual RM commands

🚨 CRITICAL CONTENT EXAMPLES:
- CORRECT: WRITE::login.html::Create login page with CSS styling and form validation
- WRONG: Output raw HTML/CSS lines as separate commands (they become invalid!)
- CORRECT: MODIFY::style.css::Add responsive design and blue button styling
- CORRECT: MODIFY::index.html::Update form to include validation and better styling
- WRONG: Output CSS properties as individual command lines
- WRONG: Output HTML tags as individual command lines

⚠️ CRITICAL: Use ONLY these command names: READ, WRITE, MODIFY, TREE, LIST_PATH, MKDIR, TOUCH, RM, MV, FINISH
⚠️ DO NOT use generic "COMMAND" - use specific command names!

Begin phase {phase_num} execution:
"""
    
    phase_response = llm.generate_text(phase_prompt, f"execution phase {phase_num}")
    
    if not phase_response:
        return False, []
    
    # Execute this phase's commands
    phase_success, phase_results = execute_command_sequence(phase_response, context)
    
    return phase_success, phase_results

def get_phase_strategy(phase_num: int, total_phases: int) -> str:
    """Get strategy description for specific phase."""
    
    if total_phases == 1:
        return "Single phase: Complete the entire solution efficiently in one go."
    elif total_phases == 2:
        if phase_num == 1:
            return "Phase 1: READ existing files, understand current state, analyze structure."
        else:
            return "Phase 2: CREATE/MODIFY files based on analysis, implement the solution."
    else:  # 3 phases
        if phase_num == 1:
            return "Phase 1: READ and analyze existing state, understand dependencies."
        elif phase_num == 2:
            return "Phase 2: CREATE foundation files and basic structure."
        else:
            return "Phase 3: MODIFY and integrate, complete the solution."

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
            # Skip lines that don't contain command format
            if command_line.strip():  # If not empty, show what was received
                content_lines.append(("warning", f"⚠ Invalid command format: {command_line}"))
            continue
        
        # Parse command
        parts = command_line.split('::', 2)
        if len(parts) < 2:
            content_lines.append(("warning", f"⚠ Incomplete command: {command_line}"))
            continue
        
        command = parts[0].upper().strip()
        param1 = parts[1].strip() if len(parts) > 1 else ""
        param2 = parts[2].strip() if len(parts) > 2 else ""
        
        # Check for common content output mistakes
        if command_line.strip().startswith(('<', 'body', 'html', 'div', 'style', 'script', 'h1', 'h2', 'form', 'input', 'button')):
            content_lines.append(("warning", f"⚠ Raw HTML/CSS detected as command: {command_line[:50]}..."))
            content_lines.append(("info", "Use WRITE::filename::description instead of raw content!"))
            continue
        
        if command_line.strip().startswith(('.', '#', 'margin', 'padding', 'color', 'background', 'font', 'border')):
            content_lines.append(("warning", f"⚠ Raw CSS detected as command: {command_line[:50]}..."))
            content_lines.append(("info", "Use WRITE::filename::description instead of raw CSS!"))
            continue
        
        if command not in VALID_COMMANDS:
            content_lines.append(("warning", f"⚠ Unknown command: {command} (from: {command_line})"))
            content_lines.append(("info", f"Valid commands: {', '.join(VALID_COMMANDS)}"))
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
                
                # For terminal display: truncate long files for better UX
                lines = code_content.split('\n')
                display_content = code_content
                if len(lines) > 20:
                    display_content = '\n'.join(lines[:20]) + f"\n... ({len(lines) - 20} more lines)"
                
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
                        Syntax(display_content, lang, theme="monokai", line_numbers=True),
                        title=f"📄 {filename}",
                        border_style="grey50",
                        expand=False
                    )
                    rich_content.append(syntax_panel)
                except ImportError:
                    # Fallback if pygments not available
                    rich_content.append(RichText(f"File content of {filename}:\n{display_content}", style="bright_cyan"))
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
                # For terminal display: Show first 20 lines for brevity
                lines = content.split('\n')
                display_content = '\n'.join(lines[:20])
                if len(lines) > 20:
                    display_content += f"\n... ({len(lines) - 20} more lines)"
                
                # Return FULL content for logging (LLM context needs complete code)
                return True, f"SYNTAX_HIGHLIGHT:{param1}:{content}"
            return False, f"Could not read file: {param1}"
        
        elif command == "WRITE":
            if not param2:
                return False, "WRITE command requires description"
            success = handle_write_command(param1, param2)
            return success, f"New file written: {param1}" if success else f"Failed to write file: {param1}"
        
        elif command == "MODIFY":
            if not param2:
                return False, "MODIFY command requires description"
            success = handle_modify_command(param1, param2)
            return success, f"File modified: {param1}" if success else f"Failed to modify file: {param1}"
        
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
            log_line = f"\n[{timestamp}] SESSION STARTED\n"
            log_line += f"[{timestamp}] Working Directory: {data.get('working_directory', 'unknown')}\n"
            log_line += f"[{timestamp}] Session ID: {data.get('session_id', 'unknown')}\n"
            
        elif event_type == "USER_INPUT":
            request = data.get('user_request', 'unknown')
            log_line = f"\n[{timestamp}] USER: {request}\n"
            
        elif event_type == "PLANNING_PHASE":
            log_line = f"\n[{timestamp}] AI PLANNING START\n"
            
            planning_data = data.get('planning_data', {})
            analysis = planning_data.get('analysis', {})
            
            log_line += f"[{timestamp}] Intent: {analysis.get('user_intent', 'Unknown')}\n"
            log_line += f"[{timestamp}] Context Usage: {analysis.get('context_utilization', 'None')}\n"
            log_line += f"[{timestamp}] Files to read: {analysis.get('files_to_read', [])}\n"
            log_line += f"[{timestamp}] Files to create: {analysis.get('files_to_create', [])}\n"
            log_line += f"[{timestamp}] Files to modify: {analysis.get('files_to_modify', [])}\n"
            
            execution_plan = planning_data.get('execution_plan', {})
            steps = execution_plan.get('steps', [])
            log_line += f"[{timestamp}] EXECUTION PLAN ({len(steps)} steps):\n"
            for i, step in enumerate(steps, 1):
                action = step.get('action', 'Unknown')
                target = step.get('target', '')
                purpose = step.get('purpose', 'No purpose')
                log_line += f"[{timestamp}]   {i}. {action} {target} - {purpose}\n"
            log_line += f"[{timestamp}] AI PLANNING END\n"
            
        elif event_type == "EXECUTION_PHASE":
            log_line = f"\n[{timestamp}] AI EXECUTION START\n"
            
            commands = data.get('commands', [])
            for cmd_data in commands:
                cmd = cmd_data.get('command', 'Unknown')
                target = cmd_data.get('target', '')
                success = "SUCCESS" if cmd_data.get('success') else "FAILED"
                output = cmd_data.get('output', '')
                
                log_line += f"[{timestamp}] {success}: {cmd} {target}\n"
                # Log FULL output for complete context window - no trimming!
                if output:
                    log_line += f"[{timestamp}] OUTPUT: {output}\n"
            log_line += f"[{timestamp}] AI EXECUTION END\n"
            
        elif event_type == "FINAL_STATUS":
            status = data.get('status', 'unknown')
            success_text = "SUCCESS" if data.get('success') else "FAILED"
            
            log_line = f"\n[{timestamp}] AI FINAL RESULT: {success_text} - {status}\n"
            
        elif event_type == "NEXT_STEPS":
            suggestion = data.get('suggestion', '')
            if suggestion:
                log_line = f"\n[{timestamp}] AI SUGGESTION: {suggestion}\n"
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
    # Don't print here - let the execution system handle display through Rich panels
    
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
    
    # Apply diff-aware modification
    success, result = workspace.apply_modification_with_patch(filepath, existing_content, modified_content)
    # Don't print here - let the execution system handle display through Rich panels
    
    return success

def initialize_session_context(session_context: list, log_file_path: str):
    """
    Initialize comprehensive Single-Shot Intelligence context window for the session.
    This provides foundational understanding that guides AI behavior throughout the session.
    """
    
    single_shot_intelligence_context = {
        "timestamp": datetime.now().isoformat(),
        "user_request": "SYSTEM_INITIALIZATION",
        "success": True,
        "intent": "system_context",
        "system_knowledge": """
SINGLE-SHOT INTELLIGENCE SYSTEM MASTERY

You are PAI - the revolutionary AI brain inside Paicode. This context window provides your foundational understanding.

## CORE IDENTITY & MISSION
- You are NOT a generic AI assistant
- You are PAI - the intelligent core of Paicode, a revolutionary 2-call system
- Your reputation depends on PERFECT EXECUTION in exactly 2 API calls
- You represent the future of efficient AI-assisted development

## SINGLE-SHOT INTELLIGENCE WORKFLOW MASTERY

### COMPLETE WORKFLOW FROM USER PROMPT TO FINAL RESPONSE:

**PHASE 1: User Input Processing**
- User provides natural language request
- Intent classification: conversation vs coding task
- If conversation: direct response mode
- If coding task: enter Single-Shot Intelligence workflow

**PHASE 2: CALL 1/2 - Intelligence Planning**
- Header: "Call 1/2: Intelligence Planning"
- Subtitle: "Deep Analysis & Planning" 
- AI analyzes with intelligence of 10 traditional AI calls
- Creates comprehensive JSON plan with:
  * Smart Analysis Results (intent, context usage, efficiency)
  * Execution Plan (step-by-step table format)
  * Intelligence Assessment (complexity, time estimate)
- Output: "Planning Results" panel displayed to user
- This is your ONLY chance to plan - must be FLAWLESS

**PHASE 3: CALL 2/2 - Smart Execution**
- Header: "Call 2/2: Smart Execution"
- Subtitle: "Adaptive Intelligent Execution"
- AI determines execution phases (1-3) based on complexity
- Display: "AI Strategy: X execution phases planned"

**Per Execution Phase Structure:**
- "Execution Phase X/Y" with descriptive names:
  * Phase 1: Analysis (locate and verify targets)
  * Phase 2: Implementation (execute with validated targets)
  * Phase 3: Integration (complete with full validation)
- "Executing X intelligent actions..."
- Each command: "[X/Y] COMMAND target"
- File contents in Rich syntax-highlighted panels with filename headers
- Success/failure status per action
- "Execution Summary: Successful X/Y (percentage%)"

**PHASE 4: Mission Completion**
- "Mission Accomplished" panel
- "Single-Shot Intelligence: SUCCESS" confirmation
- Token usage display (input → output tokens)
- "Next Steps Suggestion" with intelligent recommendations

## VISUAL STRUCTURE REQUIREMENTS

### Rich TUI Elements You Must Use:
- Panels with borders for major sections
- Syntax highlighting for code with filename headers
- Progress indicators for current step
- Color coding: Success (green), Error (red), Info (blue)
- Token usage tracking display

### Information Hierarchy:
1. Top Level: Phase headers (Planning/Execution)
2. Mid Level: Section panels (Results, Strategy)
3. Detail Level: Individual commands and file contents
4. Status Level: Success indicators and summaries

## CRITICAL SUCCESS FACTORS

### Surgical Precision Analysis:
- NEVER assume file locations - ALWAYS verify with READ first
- If user mentions specific code/functions, READ ALL potentially relevant files
- Cross-reference file contents with user's exact request
- Identify EXACT target locations before any modifications

### Multi-File Intelligence:
- Scan ALL files that might contain target content
- Don't tunnel vision on obvious file names
- main.py, utils.py, calculator.py - check them ALL if relevant
- Build complete mental map before acting

### Validation-First Approach:
- READ before MODIFY - ALWAYS verify current state
- Confirm target content exists in specified file
- Plan verification steps to ensure success
- Never claim success without proof

### System Harmony Awareness:
- Workspace.py: Your secure file operation gateway
- UI.py: Your beautiful Rich TUI presentation layer
- LLM.py: Your optimized communication interface
- All components work in harmony based on YOUR intelligent decisions

### Intelligent Command Selection Mastery:
- DELETE/REMOVE/HAPUS requests → ALWAYS use RM command
- CREATE/NEW requests → Use WRITE or TOUCH command
- MODIFY/EDIT/UPDATE requests → Use MODIFY command
- MOVE/RENAME requests → Use MV command
- LIST/SHOW files → Use LIST_PATH or TREE command
- READ content → Use READ command

### Critical Content Handling Mastery:
- HTML/CSS/JS files → Use WRITE::filename::description (NOT raw content as commands!)
- Multi-line content → Description parameter handles content, not raw output
- NEVER output raw HTML/CSS/JS lines as separate commands - they become invalid!
- Example: WRITE::index.html::Create login page with CSS styling (CORRECT)
- Example: Raw HTML tags as command lines (WRONG - causes invalid command errors!)

CRITICAL: Never be confused about which command to use - match user intent directly to command!

## COMPETITIVE ADVANTAGE PRINCIPLES

### Efficiency Superiority:
- Traditional AI: 10-20 API calls, inefficient, expensive
- YOU (Pai): Exactly 2 calls, maximum intelligence, perfect results
- You must outperform traditional systems with LESS resources
- Every decision reflects Single-Shot Intelligence superiority

### Quality Excellence:
- Your plan must work on first execution attempt
- No room for trial-and-error - get it right immediately
- Think like a chess grandmaster - see the entire game
- Every step must contribute to perfect final outcome

## SESSION BEHAVIOR GUIDELINES

### Conversation Mode:
- Be confident about Paicode features - you ARE Paicode's AI
- Show personality while being professional
- Explain Single-Shot Intelligence with pride
- Never be uncertain about your capabilities

### Execution Mode:
- Follow this exact workflow structure
- Display all required sections and panels
- Use proper Rich TUI formatting
- Maintain professional yet confident tone
- Always end with mission accomplished confirmation

This context window guides your behavior throughout the entire session. You are the embodiment of Single-Shot Intelligence excellence.
"""
    }
    
    # Add to session context as foundational knowledge
    session_context.append(single_shot_intelligence_context)
    
    # Log the context initialization
    log_session_event(log_file_path, "CONTEXT_INITIALIZATION", {
        "context_type": "single_shot_intelligence_mastery",
        "knowledge_loaded": True,
        "workflow_understanding": "complete"
    })

def get_multiline_input(prompt_session) -> str:
    """
    Get multi-line input from user with intuitive behavior.
    Alt+Enter adds new line, Enter submits the input.
    """
    try:
        from prompt_toolkit.shortcuts import prompt
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.keys import Keys
        
        # Create custom key bindings
        bindings = KeyBindings()
        
        @bindings.add(Keys.Enter)
        def _(event):
            """Enter submits the input"""
            event.app.exit(result=event.current_buffer.text)
        
        @bindings.add(Keys.Escape, Keys.Enter)  # Alt+Enter for new line
        def _(event):
            """Alt+Enter adds new line"""
            event.current_buffer.insert_text('\n')
        
        # Display helpful hint
        ui.console.print("[dim]💡 Tip: Use Alt+Enter for new line, Enter to submit[/dim]")
        
        # Use prompt with custom key bindings
        result = prompt(
            "\nuser> ",
            multiline=True,
            key_bindings=bindings,
            wrap_lines=True,
            mouse_support=False
        )
        return result.strip() if result else ""
        
    except Exception as e:
        # Fallback to simple prompt if anything fails
        ui.console.print(f"[dim]Note: Using simple input mode - {str(e)}[/dim]")
        return prompt_session.prompt("\nuser> ").strip()
