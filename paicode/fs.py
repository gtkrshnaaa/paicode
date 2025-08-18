import os
import shutil
import difflib
from . import ui

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
    if not path:
        return False
        
    try:
        # 1. Normalize the path for consistency
        norm_path = os.path.normpath(path)
        
        # 2. Check if the path tries to escape the root directory
        full_path = os.path.realpath(os.path.join(PROJECT_ROOT, norm_path))
        if not full_path.startswith(PROJECT_ROOT):
            ui.print_error(f"Operation cancelled. Path '{path}' is outside the project directory.")
            return False

        # 3. Block access to sensitive files and directories
        path_parts = norm_path.replace('\\', '/').split('/')
        if any(part in SENSITIVE_PATTERNS for part in path_parts):
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



def apply_modification_with_patch(file_path: str, original_content: str, new_content: str, threshold: int = 50) -> tuple[bool, str]:
    """
    Applies a modification to a file safely by first verifying the scope of changes.

    It generates a diff between the original and new content. If the number of changed
    lines is within the threshold, it writes the new content to the file. Otherwise,
    it rejects the change to prevent unintentional overwrites.

    Args:
        file_path: The path to the file to be modified.
        original_content: The original, unmodified content of the file.
        new_content: The new, modified content generated by the LLM.
        threshold: The maximum number of lines allowed to be changed.

    Returns:
        A tuple containing:
        - bool: True if the modification was successful, False otherwise.
        - str: A message describing the result of the operation.
    """
    if not _is_path_safe(file_path):
        return False, f"Error: Access to path '{file_path}' is denied or path is not secure."

    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(original_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}"))
    
    changed_lines_count = sum(1 for line in diff if line.startswith('+') or line.startswith('-'))
    
    if not diff:
        return True, f"Success: No changes detected for {file_path}. File left untouched."

    if changed_lines_count > threshold:
        diff_preview = "\n".join(diff[:20]) 
        message = (
            f"Warning: Modification for '{file_path}' rejected. "
            f"The change was too large ({changed_lines_count} lines), exceeding the threshold of {threshold} lines. "
            f"This is a safeguard to prevent accidental overwrites.\n"
            f"Diff Preview:\n{diff_preview}"
        )
        return False, message

    try:
        write_to_file(file_path, new_content)
        return True, f"Success: Applied modification to {file_path} ({changed_lines_count} lines changed)."
    except IOError as e:
        return False, f"Error: Failed to write modification to file: {e}"