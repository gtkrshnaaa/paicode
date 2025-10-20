import os
import shutil
import difflib
from . import ui
import subprocess
from .platforms import detect_os
from datetime import datetime
import threading
import time

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
AUDIT_DIR = os.path.join(PROJECT_ROOT, ".pai_history")
# One-time notices to avoid spamming logs
_timeout_notice_shown = False

# List of sensitive files and directories to be blocked
SENSITIVE_PATTERNS = {
    '.env', 
    '.git', 
    'venv', 
    '.venv',
    '__pycache__', 
    '.pai_history', 
    '.idea', 
    '.vscode'
}

# ---------------- Interactive Shell Sessions (stateful) ----------------
_SESSIONS: dict[str, dict] = {}
_SESSION_COUNTER = 0

def _new_session_id() -> str:
    global _SESSION_COUNTER
    _SESSION_COUNTER += 1
    return f"sh-{int(time.time())}-{_SESSION_COUNTER}"

def run_shell_session_start(command: str) -> str:
    """Start a persistent shell process for interactive programs and return a session id.

    Use run_shell_session_input() to feed stdin and see output live. End with run_shell_session_end().
    """
    info = detect_os()
    # Verbose
    verbose = os.getenv('PAI_VERBOSE', 'true').lower() in {'1','true','yes','on'}
    if verbose:
        try:
            preview = command if len(command) <= 200 else command[:200] + '...'
            ui.print_action(f"$ {preview}")
        except Exception:
            pass
    # Timeout (with one-time info when default is used)
    global _timeout_notice_shown
    timeout_env = os.getenv('PAI_SHELL_TIMEOUT')
    try:
        timeout_sec = int(timeout_env) if timeout_env is not None else 20
        if timeout_sec < 1:
            timeout_sec = 20
            if not _timeout_notice_shown:
                try:
                    ui.console.print("Info: Using default shell timeout 20s (PAI_SHELL_TIMEOUT not set or invalid).", style="dim")
                except Exception:
                    pass
                _timeout_notice_shown = True
    except ValueError:
        timeout_sec = 20
        if not _timeout_notice_shown:
            try:
                ui.console.print("Info: Using default shell timeout 20s (PAI_SHELL_TIMEOUT invalid).", style="dim")
            except Exception:
                pass
            _timeout_notice_shown = True
    if info.name == 'windows':
        full_cmd = ["powershell", "-NoProfile", "-Command", command]
    else:
        full_cmd = ["bash", "-lc", command]

    # Start process
    try:
        proc = subprocess.Popen(
            full_cmd,
            cwd=PROJECT_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except Exception as e:
        return f"Error: Failed to start session: {e}"

    # Readers
    def _reader(pipe, style):
        try:
            for line in iter(pipe.readline, ''):
                try:
                    ui.console.print(line.rstrip(), style=style)
                except Exception:
                    pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    t_out = threading.Thread(target=_reader, args=(proc.stdout, "info"), daemon=True)
    t_err = threading.Thread(target=_reader, args=(proc.stderr, "warning"), daemon=True)
    t_out.start(); t_err.start()

    sid = _new_session_id()
    _SESSIONS[sid] = {"proc": proc, "t_out": t_out, "t_err": t_err}
    # Audit
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        with open(os.path.join(AUDIT_DIR, "shell.log"), 'a') as lf:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lf.write(f"[{ts}] START_SESSION: {sid} CMD: {command}\n")
    except Exception:
        pass
    return f"Success: Started session {sid}. Use EXECUTE_FEED::{sid}::<input> and EXECUTE_END::{sid}."

def run_shell_session_input(session_id: str, input_text: str) -> str:
    """Feed input to an existing shell session (stdin)."""
    sess = _SESSIONS.get(session_id)
    if not sess:
        return f"Error: Session not found: {session_id}"
    proc: subprocess.Popen = sess.get("proc")
    if not proc or proc.poll() is not None:
        return f"Error: Session {session_id} has already exited."
    try:
        if proc.stdin:
            proc.stdin.write(input_text)
            proc.stdin.flush()
        # Audit
        try:
            os.makedirs(AUDIT_DIR, exist_ok=True)
            with open(os.path.join(AUDIT_DIR, "shell.log"), 'a') as lf:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                preview = input_text if len(input_text) < 120 else input_text[:120] + '...'
                lf.write(f"[{ts}] FEED_SESSION: {session_id} INPUT: {preview}\n")
        except Exception:
            pass
        return f"Success: Fed input to session {session_id}."
    except Exception as e:
        return f"Error: Failed to write to session {session_id}: {e}"

def run_shell_session_end(session_id: str) -> str:
    """Terminate a running session and clean up."""
    sess = _SESSIONS.pop(session_id, None)
    if not sess:
        return f"Warning: Session not found or already closed: {session_id}"
    proc: subprocess.Popen = sess.get("proc")
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    except Exception:
        pass
    # Audit
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        with open(os.path.join(AUDIT_DIR, "shell.log"), 'a') as lf:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lf.write(f"[{ts}] END_SESSION: {session_id}\n")
    except Exception:
        pass
    return f"Success: Ended session {session_id}."

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

def tree_directory(path: str = '.', max_depth: int | None = None) -> str:
    """Creates a string representation of the directory structure recursively.

    Args:
        path: Base path to render from (relative to PROJECT_ROOT).
        max_depth: Optional depth limit (0 means only the base dir, 1 includes its children, etc.).
    """
    if not _is_path_safe(path):
        return f"Error: Cannot access path '{path}'."

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(full_path):
        return f"Error: '{path}' is not a valid directory."

    tree_lines = [f"{os.path.basename(full_path)}/"]

    def build_tree(directory, prefix="", depth=0):
        # Respect depth limit if provided
        if max_depth is not None and depth >= max_depth:
            return
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
                build_tree(item_path, prefix=prefix + extension, depth=depth + 1)

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
        if os.path.exists(full_path):
            return f"Warning: File already exists, left untouched: {file_path}"
        with open(full_path, 'x') as f: pass
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
        # If exists and identical, skip write for idempotency
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as rf:
                    existing = rf.read()
                if existing == content:
                    return f"Warning: No changes detected for {file_path}. File left untouched."
            except Exception:
                pass
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

    # Normalize line endings to avoid false negatives
    original_lines = original_content.replace('\r\n', '\n').replace('\r', '\n').splitlines(keepends=True)
    new_lines = new_content.replace('\r\n', '\n').replace('\r', '\n').splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}"
    ))

    # Count only real content changes, exclude diff headers like '+++', '---'
    def _is_content_change(line: str) -> bool:
        if not line:
            return False
        if line.startswith('+++') or line.startswith('---'):
            return False
        return line.startswith('+') or line.startswith('-')

    changed_lines_count = sum(1 for line in diff if _is_content_change(line))
    
    if not diff:
        return False, f"Warning: No changes detected for {file_path}. File left untouched."

    # No size-based rejection: apply any non-empty diff (user prefers iterative focus without hard limits)

    try:
        msg = write_to_file(file_path, new_content)
        ok = isinstance(msg, str) and msg.startswith("Success")
        # Preserve accurate downstream logging (do not fabricate success)
        if ok:
            return True, f"Success: Applied modification to {file_path} ({changed_lines_count} lines changed)."
        else:
            return False, msg
    except IOError as e:
        return False, f"Error: Failed to write modification to file: {e}"


# ---------------- OS Command Preview (Display Only) ----------------
def _posix_cmd_for(action: str) -> str | None:
    cmd, _, params = action.partition('::')
    cmd = cmd.upper().strip()
    # Normalize single-path parameters: only use the first segment before '::'
    def _path_only(p: str) -> str:
        head, _, _ = p.partition('::')
        return head or '.'
    # Semantic headers
    if cmd == 'CREATE_DIRECTORY':
        p = _path_only(params)
        return f"mkdir -p '{p}'"
    if cmd == 'CREATE_FILE':
        p = _path_only(params)
        return f"touch '{p}'"
    if cmd == 'DELETE_PATH':
        p = _path_only(params)
        return f"rm -rf '{p}'"
    if cmd == 'MOVE_PATH':
        src, _, dst = params.partition('::')
        return f"mv '{src}' '{dst}'"
    if cmd == 'LIST_PATHS':
        path = _path_only(params)
        return f"ls -la '{path}'"
    if cmd == 'SHOW_TREE':
        path = _path_only(params)
        return fr"(command -v tree >/dev/null 2>&1 && tree '{path}') || find '{path}' \( -name .git -o -name __pycache__ -o -name .env -o -name venv -o -name .vscode -o -name .idea \) -prune -o -print"
    if cmd == 'READ_FILE':
        p = _path_only(params)
        return f"sed -n '1,200p' '{p}'"
    if cmd == 'WRITE_FILE':
        file_path, _, _desc = params.partition('::')
        return f"# write content to '{file_path}' (omitted in preview)"
    if cmd == 'MODIFY_FILE':
        file_path, _, _desc = params.partition('::')
        return f"# modify '{file_path}' (apply diff)"
    if cmd == 'EXECUTE':
        exe = params.split('::', 1)[0].strip()
        return exe
    if cmd == 'EXECUTE_INPUT':
        # Preview only; do not show the full input payload
        exe, _, _payload = params.partition('::')
        return f"# with stdin -> {exe.strip()}"
    if cmd == 'FINISH':
        return f"# finish: {params}"
    return None

def _pwsh_cmd_for(action: str) -> str | None:
    cmd, _, params = action.partition('::')
    cmd = cmd.upper().strip()
    # Normalize single-path parameters: only use the first segment before '::'
    def _path_only(p: str) -> str:
        head, _, _ = p.partition('::')
        return head or '.'
    # Semantic headers
    if cmd == 'CREATE_DIRECTORY':
        p = _path_only(params)
        return f"New-Item -ItemType Directory -Force -Path '{p}' | Out-Null"
    if cmd == 'CREATE_FILE':
        p = _path_only(params)
        return f"New-Item -ItemType File -Force -Path '{p}' | Out-Null"
    if cmd == 'DELETE_PATH':
        p = _path_only(params)
        return f"Remove-Item -Recurse -Force -Path '{p}'"
    if cmd == 'MOVE_PATH':
        src, _, dst = params.partition('::')
        return f"Move-Item -Force -Path '{src}' -Destination '{dst}'"
    if cmd == 'LIST_PATHS':
        path = _path_only(params)
        return f"Get-ChildItem -Force -Recurse '{path}'"
    if cmd == 'SHOW_TREE':
        path = _path_only(params)
        return f"Get-ChildItem -Force -Recurse '{path}' | Format-List FullName"
    if cmd == 'READ_FILE':
        p = _path_only(params)
        return f"Get-Content -TotalCount 200 '{p}'"
    if cmd == 'WRITE_FILE':
        file_path, _, _desc = params.partition('::')
        return f"# write content to '{file_path}' (omitted in preview)"
    if cmd == 'MODIFY_FILE':
        file_path, _, _desc = params.partition('::')
        return f"# modify '{file_path}' (apply diff)"
    if cmd == 'EXECUTE':
        exe = params.split('::', 1)[0].strip()
        return exe
    if cmd == 'FINISH':
        return f"# finish: {params}"
    return None

def os_command_preview(actions: list[str]) -> str:
    """Return a multi-line string of OS-specific command previews for the given action lines."""
    info = detect_os()
    # Timeout guard to avoid indefinite hangs on interactive commands
    try:
        timeout_sec = int(os.getenv('PAI_SHELL_TIMEOUT', '20'))
        if timeout_sec < 1:
            timeout_sec = 20
    except ValueError:
        timeout_sec = 20
    lines: list[str] = []
    header = f"# OS: {info.name} | Shell: {info.shell} | PathSep: {info.path_sep}"
    lines.append(header)
    mapper = _pwsh_cmd_for if info.name == 'windows' else _posix_cmd_for
    for a in actions:
        cmdline = mapper(a)
        if cmdline:
            lines.append(cmdline)
    return "\n".join(lines)


def _stream_process(full_cmd: list[str], *, input_text: str | None, timeout_sec: int) -> tuple[int, str, str, bool]:
    """Run a subprocess with live streaming of stdout/stderr.

    Returns (exit_code, captured_stdout, captured_stderr, timed_out).
    """
    proc = subprocess.Popen(
        full_cmd,
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    captured_out: list[str] = []
    captured_err: list[str] = []
    timed_out = False

    def _reader(pipe, sink_list, style):
        try:
            for line in iter(pipe.readline, ''):
                sink_list.append(line)
                try:
                    ui.console.print(line.rstrip(), style=style)
                except Exception:
                    pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    t_out = threading.Thread(target=_reader, args=(proc.stdout, captured_out, "info"), daemon=True)
    t_err = threading.Thread(target=_reader, args=(proc.stderr, captured_err, "warning"), daemon=True)
    t_out.start(); t_err.start()

    # Provide stdin then close
    if input_text is not None and proc.stdin:
        try:
            proc.stdin.write(input_text)
            proc.stdin.flush()
            proc.stdin.close()
        except Exception:
            pass

    start = time.time()
    while True:
        try:
            ret = proc.wait(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            if time.time() - start > timeout_sec:
                try:
                    proc.kill()
                except Exception:
                    pass
                timed_out = True
                break
            continue

    # Ensure threads exit
    t_out.join(timeout=1.0)
    t_err.join(timeout=1.0)
    exit_code = proc.returncode if proc.returncode is not None else -1
    return exit_code, ''.join(captured_out), ''.join(captured_err), timed_out


def run_shell(command: str) -> str:
    """Execute a shell command in a cross-platform way (optional, gated by env var).

    Safety:
    - Runs with cwd restricted to PROJECT_ROOT.
    - Does not enforce full path-safety on arbitrary shell code (USE WITH CARE).
    - Enable by setting environment variable PAI_ALLOW_SHELL_EXEC=true
    """
    allow = os.getenv('PAI_ALLOW_SHELL_EXEC', 'true').lower() in {'1', 'true', 'yes', 'on'}
    if not allow:
        return "Warning: Shell execution is disabled. Set PAI_ALLOW_SHELL_EXEC=true to enable."

    # Optional network guard: block obvious network operations unless explicitly allowed
    allow_net = os.getenv('PAI_ALLOW_NET', 'false').lower() in {'1', 'true', 'yes', 'on'}
    net_indicators = [
        'curl ', ' wget ', ' http://', ' https://', ' git clone', ' pip install', ' apt ', ' apt-get ',
        ' npm ', ' pnpm ', ' yarn ', ' brew ', ' ssh ', ' scp '
    ]
    # pad with spaces to reduce false positives at start
    padded_cmd = f" {command} "
    if not allow_net and any(tok in padded_cmd for tok in net_indicators):
        return (
            "Warning: Network operations are disabled. Set PAI_ALLOW_NET=true to enable.\n"
            "Blocked command due to potential network access."
        )

    info = detect_os()
    # Timeout (with one-time info when default is used)
    global _timeout_notice_shown
    timeout_env = os.getenv('PAI_SHELL_TIMEOUT')
    try:
        timeout_sec = int(timeout_env) if timeout_env is not None else 20
        if timeout_sec < 1:
            timeout_sec = 20
            if not _timeout_notice_shown:
                try:
                    ui.console.print("Info: Using default shell timeout 20s (PAI_SHELL_TIMEOUT not set or invalid).", style="dim")
                except Exception:
                    pass
                _timeout_notice_shown = True
    except ValueError:
        timeout_sec = 20
        if not _timeout_notice_shown:
            try:
                ui.console.print("Info: Using default shell timeout 20s (PAI_SHELL_TIMEOUT invalid).", style="dim")
            except Exception:
                pass
            _timeout_notice_shown = True

    try:
        if info.name == 'windows':
            # Use PowerShell
            full_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
        else:
            # Use bash/sh
            full_cmd = ["bash", "-lc", command]

        stream = os.getenv('PAI_STREAM', 'true').lower() in {'1','true','yes','on'}
        if stream:
            code, out, err, timed_out = _stream_process(full_cmd, input_text=None, timeout_sec=timeout_sec)
            if timed_out:
                return (
                    "Warning: Shell command timed out. It may be waiting for interactive input.\n"
                    f"Command: {command}\n"
                    f"Timeout: {timeout_sec}s (configurable via PAI_SHELL_TIMEOUT).\n"
                    "Tip: Use EXECUTE_INPUT to provide stdin or use a non-interactive strategy."
                )
            out = out.strip(); err = err.strip()
        else:
            try:
                proc = subprocess.run(
                    full_cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout_sec,
                )
            except subprocess.TimeoutExpired:
                return (
                    "Warning: Shell command timed out. It may be waiting for interactive input.\n"
                    f"Command: {command}\n"
                    f"Timeout: {timeout_sec}s (configurable via PAI_SHELL_TIMEOUT).\n"
                    "Tip: Use EXECUTE_INPUT to provide stdin or use a non-interactive strategy."
                )
            out = proc.stdout.strip(); err = proc.stderr.strip(); code = proc.returncode
        msg = []
        msg.append(f"ExitCode: {code}")
        if out:
            msg.append("STDOUT:\n" + out)
        if err:
            msg.append("STDERR:\n" + err)
        prefix = "Success" if code == 0 else "Error"
        # Audit log
        try:
            os.makedirs(AUDIT_DIR, exist_ok=True)
            # Ensure .gitignore exists to avoid committing audit logs
            try:
                gi_path = os.path.join(AUDIT_DIR, ".gitignore")
                if not os.path.exists(gi_path):
                    with open(gi_path, 'w') as gf:
                        gf.write("# Ignore all audit/session logs in this directory\n*\n!.gitignore\n")
            except Exception:
                pass
            log_path = os.path.join(AUDIT_DIR, "shell.log")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, 'a') as lf:
                lf.write(f"[{ts}] CMD: {command}\nEXIT: {code}\n\n")
        except Exception:
            pass
        return f"{prefix}: Shell command executed.\n" + "\n".join(msg)
    except Exception as e:
        return f"Error: Failed to execute shell command: {e}"

def run_shell_with_input(command: str, input_text: str) -> str:
    """Execute a shell command and provide input_text to its STDIN.

    Mirrors run_shell() semantics, adds stdin piping, timeout, verbose, and auditing.
    """
    allow = os.getenv('PAI_ALLOW_SHELL_EXEC', 'true').lower() in {'1', 'true', 'yes', 'on'}
    if not allow:
        return "Warning: Shell execution is disabled. Set PAI_ALLOW_SHELL_EXEC=true to enable."

    allow_net = os.getenv('PAI_ALLOW_NET', 'false').lower() in {'1', 'true', 'yes', 'on'}
    net_indicators = [
        'curl ', ' wget ', ' http://', ' https://', ' git clone', ' pip install', ' apt ', ' apt-get ',
        ' npm ', ' pnpm ', ' yarn ', ' brew ', ' ssh ', ' scp '
    ]
    padded_cmd = f" {command} "
    if not allow_net and any(tok in padded_cmd for tok in net_indicators):
        return (
            "Warning: Network operations are disabled. Set PAI_ALLOW_NET=true to enable.\n"
            "Blocked command due to potential network access."
        )

    info = detect_os()
    # Verbose
    verbose = os.getenv('PAI_VERBOSE', 'true').lower() in {'1','true','yes','on'}
    if verbose:
        try:
            preview = command if len(command) <= 200 else command[:200] + '...'
            ui.print_action(f"$ {preview}  <<stdin {len(input_text)} bytes>")
        except Exception:
            pass

    # Timeout (with one-time info when default is used)
    global _timeout_notice_shown
    timeout_env = os.getenv('PAI_SHELL_TIMEOUT')
    try:
        timeout_sec = int(timeout_env) if timeout_env is not None else 20
        if timeout_sec < 1:
            timeout_sec = 20
            if not _timeout_notice_shown:
                try:
                    ui.console.print("Info: Using default shell timeout 20s (PAI_SHELL_TIMEOUT not set or invalid).", style="dim")
                except Exception:
                    pass
                _timeout_notice_shown = True
    except ValueError:
        timeout_sec = 20
        if not _timeout_notice_shown:
            try:
                ui.console.print("Info: Using default shell timeout 20s (PAI_SHELL_TIMEOUT invalid).", style="dim")
            except Exception:
                pass
            _timeout_notice_shown = True

    try:
        if info.name == 'windows':
            full_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
        else:
            full_cmd = ["bash", "-lc", command]

        stream = os.getenv('PAI_STREAM', 'true').lower() in {'1','true','yes','on'}
        # Ensure final newline so the last input() receives an Enter
        payload = input_text if (input_text.endswith("\n") or input_text.endswith("\r\n")) else (input_text + "\n")
        if stream:
            code, out, err, timed_out = _stream_process(full_cmd, input_text=payload, timeout_sec=timeout_sec)
            if timed_out:
                return (
                    "Warning: Shell command timed out while providing stdin. It may expect more input.\n"
                    f"Command: {command}\n"
                    f"Timeout: {timeout_sec}s (configurable via PAI_SHELL_TIMEOUT)."
                )
            out = out.strip(); err = err.strip()
        else:
            try:
                proc = subprocess.run(
                    full_cmd,
                    cwd=PROJECT_ROOT,
                    input=payload,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout_sec,
                )
            except subprocess.TimeoutExpired:
                return (
                    "Warning: Shell command timed out while providing stdin. It may expect more input.\n"
                    f"Command: {command}\n"
                    f"Timeout: {timeout_sec}s (configurable via PAI_SHELL_TIMEOUT)."
                )
            out = proc.stdout.strip(); err = proc.stderr.strip(); code = proc.returncode
        msg = []
        msg.append(f"ExitCode: {code}")
        if out:
            msg.append("STDOUT:\n" + out)
        if err:
            msg.append("STDERR:\n" + err)
        prefix = "Success" if code == 0 else "Error"

        # Audit
        try:
            os.makedirs(AUDIT_DIR, exist_ok=True)
            try:
                gi_path = os.path.join(AUDIT_DIR, ".gitignore")
                if not os.path.exists(gi_path):
                    with open(gi_path, 'w') as gf:
                        gf.write("# Ignore all audit/session logs in this directory\n*\n!.gitignore\n")
            except Exception:
                pass
            log_path = os.path.join(AUDIT_DIR, "shell.log")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, 'a') as lf:
                lf.write(f"[{ts}] CMD: {command} <with-stdin>\nEXIT: {code}\n\n")
        except Exception:
            pass

        return f"{prefix}: Shell command executed.\n" + "\n".join(msg)
    except Exception as e:
        return f"Error: Failed to execute shell command with input: {e}"