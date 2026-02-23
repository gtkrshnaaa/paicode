import os
import shutil
import difflib
import tempfile
import re
from . import ui

"""
workspace.py
------------
This module acts as the workspace controller for Pai Code. It centralizes
application-level operations on the project's workspace, such as reading,
writing, listing, tree visualization, moving, removing, creating files and
directories, as well as applying diff-aware modifications. In order to protect
the workspace, it enforces path-security policies (path normalization, root
verification, and deny-listing sensitive paths) before executing any action.

All functions defined in this module are the provided primitives to manipulate
and manage files within the project workspace in a controlled, secure manner.
All operations are constrained strictly within the project root determined at
runtime (workspace scope), ensuring controlled manipulation of project files.
"""

PROJECT_ROOT = os.path.abspath(os.getcwd())

# List of sensitive files and directories to be blocked
SENSITIVE_PATTERNS = {
    '.env', 
    '.git', 
    'venv', 
    '__pycache__', 
    '.pai_history', 
    '.idea', 
    '.vscode'
}

def _is_path_safe(path: str) -> bool:
    """
    Ensures the target path is within the project directory and not sensitive.
    """
    if not path or not isinstance(path, str):
        return False
        
    try:
        # 1. Normalize the path for consistency and strip whitespace
        norm_path = os.path.normpath(path.strip())
        
        # 2. Reject empty paths after normalization, but allow '.' for current directory
        if not norm_path or norm_path == '..':
            return False
        
        # 3. Check if the path tries to escape the root directory
        full_path = os.path.realpath(os.path.join(PROJECT_ROOT, norm_path))
        if not full_path.startswith(os.path.realpath(PROJECT_ROOT)):
            ui.print_error(f"Operation cancelled. Path '{path}' is outside the project directory.")
            return False

        # 4. Block access to sensitive files and directories
        path_parts = norm_path.replace('\\', '/').split('/')
        if any(part in SENSITIVE_PATTERNS for part in path_parts if part):
            ui.print_error(f"Access to the sensitive path '{path}' is denied.")
            return False

    except Exception as e:
        ui.print_error(f"Error during path validation: {e}")
        return False

    return True

def tree_directory(path: str = '.') -> str:
    """Creates a string representation of the directory structure recursively."""
    if not _is_path_safe(path):
        return f"Error: Cannot access path '{path}'."

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(full_path):
        return f"Error: '{path}' is not a valid directory."

    tree_lines = [f"{os.path.basename(full_path)}/"]

    def build_tree(directory, prefix=""):
        try:
            items = sorted([item for item in os.listdir(directory) if item not in SENSITIVE_PATTERNS])
        except FileNotFoundError:
            return

        pointers = ['├── '] * (len(items) - 1) + ['└── ']
        
        for pointer, item in zip(pointers, items):
            tree_lines.append(f"{prefix}{pointer}{item}")
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                extension = '│   ' if pointer == '├── ' else '    '
                build_tree(item_path, prefix=prefix + extension)

    build_tree(full_path)
    return "\n".join(tree_lines)

def list_path(path: str = '.') -> str | None:
    """
    Lists all files and subdirectories recursively for a given path in a simple,
    machine-readable, newline-separated format.
    """
    if not _is_path_safe(path):
        return f"Error: Cannot access path '{path}'."

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(full_path):
        return f"Error: '{path}' is not a valid directory."

    path_list = []
    for root, dirs, files in os.walk(full_path, topdown=True):
        # Filter out sensitive directories from being traversed
        dirs[:] = [d for d in dirs if d not in SENSITIVE_PATTERNS]
        
        # Process files
        for name in files:
            if name not in SENSITIVE_PATTERNS:
                # Get relative path from the initial 'path'
                rel_dir = os.path.relpath(root, PROJECT_ROOT)
                path_list.append(os.path.join(rel_dir, name).replace('\\', '/'))
        
        # Process directories
        for name in dirs:
            rel_dir = os.path.relpath(root, PROJECT_ROOT)
            path_list.append(os.path.join(rel_dir, name).replace('\\', '/') + '/')

    return "\n".join(sorted(path_list))
    

def delete_item(path: str) -> str:
    """Deletes a file or directory and returns a status message."""
    if not _is_path_safe(path): return f"Error: Access to path '{path}' is denied or path is not secure."
    try:
        full_path = os.path.join(PROJECT_ROOT, path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            return f"Success: File deleted: {path}"
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)
            return f"Success: Directory deleted: {path}"
        else:
            return f"Warning: Item not found, nothing deleted: {path}"
    except OSError as e:
        return f"Error: Failed to delete '{path}': {e}"

def move_item(source: str, destination: str) -> str:
    """Moves an item and returns a status message."""
    if not _is_path_safe(source) or not _is_path_safe(destination):
        return "Error: Source or destination path is not secure or is denied."
    try:
        full_source = os.path.join(PROJECT_ROOT, source)
        full_destination = os.path.join(PROJECT_ROOT, destination)
        shutil.move(full_source, full_destination)
        return f"Success: Item moved from '{source}' to '{destination}'"
    except (FileNotFoundError, shutil.Error) as e:
        return f"Error: Failed to move '{source}': {e}"

def create_file(file_path: str) -> str:
    """Creates an empty file and returns a status message."""
    if not _is_path_safe(file_path): return f"Error: Access to path '{file_path}' is denied or path is not secure."
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f: pass
        return f"Success: File created: {file_path}"
    except IOError as e:
        return f"Error: Failed to create file: {e}"

def create_directory(dir_path: str) -> str:
    """Creates a directory and returns a status message."""
    if not _is_path_safe(dir_path): return f"Error: Access to path '{dir_path}' is denied or path is not secure."
    try:
        full_path = os.path.join(PROJECT_ROOT, dir_path)
        os.makedirs(full_path, exist_ok=True)
        return f"Success: Directory created: {dir_path}"
    except OSError as e:
        return f"Error: Failed to create directory: {e}"

def read_file(file_path: str) -> str | None:
    """Reads a file and returns its content, or None on failure."""
    if not _is_path_safe(file_path): return None
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        with open(full_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Let the caller (agent/cli) handle printing the error
        return None
    except IOError as e:
        ui.print_error(f"Failed to read file: {e}")
        return None

def write_to_file(file_path: str, content: str) -> str:
    """Writes to a file and returns a status message."""
    if not _is_path_safe(file_path): return f"Error: Access to path '{file_path}' is denied or path is not secure."
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return f"Success: Content successfully written to: {file_path}"
    except IOError as e:
        return f"Error: Failed to write to file: {e}"





def grep_search(pattern: str, path: str = '.') -> str:
    """
    Searches for a regex pattern across all readable files in the given directory.
    """
    if not _is_path_safe(path):
        return f"Error: Access to path '{path}' is denied or path is not secure."
        
    full_search_root = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(full_search_root):
        # If it's a file, we could search it, but usually this is used for directories
        if os.path.isfile(full_search_root):
            search_files = [full_search_root]
        else:
            return f"Error: '{path}' is not a valid directory or file."
    else:
        # Collect all safe files recursively
        search_files = []
        for root, dirs, files in os.walk(full_search_root):
            dirs[:] = [d for d in dirs if d not in SENSITIVE_PATTERNS]
            for name in files:
                if name not in SENSITIVE_PATTERNS:
                    search_files.append(os.path.join(root, name))

    results = []
    max_results = 100 # Safety limit
    
    try:
        regex = re.compile(pattern, re.IGNORECASE) # Default to case-insensitive for better discovery
    except re.error as e:
        return f"Error: Invalid regex pattern '{pattern}': {e}"

    for file_path in search_files:
        if len(results) >= max_results:
            results.append(f"... and more (capped at {max_results} results)")
            break
            
        try:
            # Skip binary files by checking for null bytes in the first 1024 bytes
            with open(file_path, 'rb') as f:
                if b'\x00' in f.read(1024):
                    continue
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        rel_path = os.path.relpath(file_path, PROJECT_ROOT).replace('\\', '/')
                        results.append(f"{rel_path}:{line_num}:{line.strip()}")
                        if len(results) >= max_results:
                            break
        except Exception:
            continue

    if not results:
        return f"No matches found for pattern '{pattern}' in '{path}'."
    
    return "\n".join(results)

def apply_surgical_edit(file_path: str, original_content: str, blocks_text: str) -> tuple[bool, str]:
    """
     Applies one or more Search and Replace blocks to the original content.
    
    This is the core of the Surgical-Edit Protocol, designed for high token 
    efficiency by only sending and receiving changed blocks rather than 
    the entire file.
    
    Format of a block:
    <<<< SEARCH
    [exact content to find]
    ====
    [content to replace with]
    >>>>
    
    Args:
        file_path: Relative path of the file being edited.
        original_content: Current content of the file.
        blocks_text: Raw string containing one or more S&R blocks.
        
    Returns:
        Tuple (success: bool, message: str).
    """
    if not _is_path_safe(file_path):
        return False, f"Error: Access to path '{file_path}' is denied."

    # Normalize line endings
    current_content = original_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split the blocks_text into individual blocks
    import re
    block_pattern = re.compile(r'<<<< SEARCH\n(.*?)\n====\n(.*?)\n>>>>', re.DOTALL)
    blocks = block_pattern.findall(blocks_text)

    if not blocks:
        # Fallback: check if the model just forgot the newlines after SEARCH/====
        block_pattern_fallback = re.compile(r'<<<< SEARCH(.*?)\n====\n(.*?)\n>>>>', re.DOTALL)
        blocks = block_pattern_fallback.findall(blocks_text)
        if not blocks:
            return False, "Error: No valid Search & Replace blocks found in the response."

    modified_content = current_content
    success_count = 0
    failures = []

    for i, (search_text, replace_text) in enumerate(blocks, 1):
        # Try exact match first
        if search_text in modified_content:
            # Check for multiple occurrences to avoid ambiguity
            count = modified_content.count(search_text)
            if count > 1:
                failures.append(f"Block {i}: Search block is ambiguous (found {count} times).")
                continue
            
            modified_content = modified_content.replace(search_text, replace_text)
            success_count += 1
        else:
            # Try a slightly more relaxed match (ignoring leading/trailing whitespace of the search block)
            stripped_search = search_text.strip()
            if stripped_search and stripped_search in modified_content:
                # Still need to be careful about ambiguity
                count = modified_content.count(stripped_search)
                if count == 1:
                    modified_content = modified_content.replace(stripped_search, replace_text)
                    success_count += 1
                else:
                    failures.append(f"Block {i}: Exact match failed, and stripped match is ambiguous.")
            else:
                failures.append(f"Block {i}: Search block not found in file.")

    if success_count == 0:
        return False, "Error: Failed to apply any Search & Replace blocks.\n" + "\n".join(failures)

    # Save the modified content
    write_result = write_to_file(file_path, modified_content)
    if "Success" in write_result:
        message = f"Success: Applied {success_count} block(s) to '{file_path}'."
        if failures:
            message += f" However, {len(failures)} block(s) failed: " + "; ".join(failures)
        return True, message
    else:
        return False, write_result

def map_workspace_pulse(path: str = '.') -> str:
    """
    Identifies the project's technology stack and maps key architectural points.
    
    This command provides high-level "Architectural Awareness" by detecting 
    frameworks (Laravel, React, Django, etc.) and showing only the most 
    relevant directories.
    
    Returns:
        A formatted summary of the project's architectural pulse.
    """
    if not _is_path_safe(path):
        return f"Error: Access to path '{path}' is denied."

    root = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(root):
        return f"Error: '{path}' is not a directory."

    # 1. Detect Stack
    files_at_root = os.listdir(root)
    
    # Framework Identification Signatures
    signatures = {
        "Laravel": ["artisan", "composer.json", "app/Providers"],
        "React/Next.js": ["package.json", "next.config.js", "src/app", "src/pages"],
        "Django": ["manage.py", "wsgi.py"],
        "Go": ["go.mod", "main.go"],
        "Python Package": ["setup.py", "pyproject.toml"],
        "Rust": ["Cargo.toml", "src/main.rs"]
    }

    detected_stack = "Unknown / Generic"
    for stack, sig_files in signatures.items():
        if any(f in files_at_root or os.path.exists(os.path.join(root, f)) for f in sig_files):
            detected_stack = stack
            break
    # We look for "meaningful" folders and skip common boilerplate/vendor folders
    important_folders = []
    skipped_folders = ["node_modules", "vendor", "dist", "build", "venv", ".git", "__pycache__"]
    
    potential_meaningful = [
        "app", "src", "lib", "routes", "database", "resources", "public", 
        "components", "views", "models", "controllers", "api", "config", "tests"
    ]

    found_meaningful = []
    for folder in potential_meaningful:
        if os.path.isdir(os.path.join(root, folder)):
            found_meaningful.append(folder)

    # 3. Generate Output
    output = [
        f"Project Pulse: {detected_stack}",
        f"Location: {path}",
        "-" * 30,
        "Key Directories Identified:"
    ]
    
    if found_meaningful:
        for folder in found_meaningful:
            try:
                # Show top-level children of each meaningful folder (capped)
                children = sorted([c for c in os.listdir(os.path.join(root, folder)) 
                                 if c not in SENSITIVE_PATTERNS and c not in skipped_folders])
                child_str = ", ".join(children[:5])
                if len(children) > 5:
                    child_str += f", ... (+{len(children)-5} more)"
                output.append(f"  - {folder}/: [{child_str if child_str else 'empty'}]")
            except Exception:
                output.append(f"  - {folder}/")
    else:
        output.append("  - No standard framework directories identified.")

    # Show root files (excluding sensitive ones)
    root_files = [f for f in files_at_root if os.path.isfile(os.path.join(root, f)) 
                  and f not in SENSITIVE_PATTERNS]
    if root_files:
        output.append("\nRoot Files of Interest:")
        output.append("  " + ", ".join(root_files[:10]))
        if len(root_files) > 10:
            output[-1] += f", ... (+{len(root_files)-10} more)"

    return "\n".join(output)

def execute_command(command: str) -> str:
    """
    Executes a shell command within the project root.
    
    Security is paramount:
    - Blocks 'cd' and directory escaping.
    - Blocks dangerous/destructive commands.
    - Limits execution time to prevent hanging.
    
    Returns:
        The command output (stdout + stderr) or a security error message.
    """
    import subprocess
    import shlex
    
    # 1. Security check: Block directory changes and escaping
    # We use shlex to properly parse the command even with quotes
    try:
        args = shlex.split(command)
    except Exception as e:
        return f"Error: Failed to parse command: {e}"

    if not args:
        return "Error: Empty command."

    # Deny-list of dangerous keywords/commands
    dangerous_keywords = ["cd", "sudo", "rm -rf /", ":(){ :|:& };:", "rm -rf .git", "mv /*", "chmod -R 777"]
    cmd_lower = command.lower()
    
    if any(kw in cmd_lower for kw in dangerous_keywords):
        return f"Error: Command contains restricted or dangerous keywords."
        
    # Block shell redirection that might be used for escaping or sensitive data exfiltration
    if any(char in command for char in [";", "&", "|", ">", "<"]):
        # Allow basic pipe/redirect if it's within the project, but for now let's be strict
        # actually, many useful commands use these. Let's rely on path safety and user oversight.
        # But we MUST block 'cd' even as part of a chain.
        if "cd " in cmd_lower or "cd\t" in cmd_lower:
            return "Error: Directory changes (cd) are not allowed."

    try:
        # Run command with 30s timeout
        # We run in PROJECT_ROOT to ensure context
        result = subprocess.run(
            command,
            shell=True, # shell=True is needed for pipes/redirects, but we must be careful
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n--- STDERR ---\n{result.stderr}"
            
        if not output.strip():
            return f"Success: Command executed with exit code {result.returncode} (no output)."
            
        return output.strip()
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error: Failed to execute command: {e}"

BRAIN_DIR = os.path.join(PROJECT_ROOT, ".pai_brain")

def ensure_brain_dir():
    """Ensures the .pai_brain directory exists."""
    os.makedirs(BRAIN_DIR, exist_ok=True)

def write_brain_artifact(filename: str, content: str):
    """Writes an artifact to the .pai_brain directory."""
    ensure_brain_dir()
    path = os.path.join(BRAIN_DIR, filename)
    with open(path, 'w') as f:
        f.write(content)

def read_brain_artifact(filename: str) -> str:
    """Reads an artifact from the .pai_brain directory. Returns empty string if not found."""
    path = os.path.join(BRAIN_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return ""