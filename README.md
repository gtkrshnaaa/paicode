# **Pai Code: Your Agentic AI Coding Companion**

> **An autonomous, conversational AI agent designed to accelerate software development through intelligent, stateful interaction directly in your terminal.**

**Pai Code** is an AI assistant for your terminal that acts as a true developer companion. It's not a toolkit of separate commands; it is a single, intelligent partner capable of understanding high-level goals, observing its environment, remembering context, and translating your intent into concrete project structures, code, and file management tasks.

-----

## **1. Core Philosophy**

Pai Code is built on a set of guiding principles that define its purpose and design:

  * **Local Terminal + LLM via API:** Pai runs in your local terminal and performs application-level operations on your project workspace files. For inference, code/context snippets are sent to an external LLM via API. Privacy therefore depends on the provider's policy; locally we enforce path-security safeguards and diff-based changes.
  * **Conversational Workflow:** We believe in the power of dialog. Pai is built for developers who thrive in the terminal, augmenting their workflow through natural language conversation, not a rigid set of commands.
  * **Editor Agnostic:** By operating directly on project workspace files, any action Pai takes is instantly reflected in your favorite IDE, from VS Code and JetBrains to Vim or Emacs.
  * **Agentic and Stateful:** Pai is designed to be more than a script runner. It maintains context throughout a session, allowing it to learn from the results of its own actions and engage in meaningful, iterative development.

-----

## **2. Project Structure**

The project uses a standard Python package structure and is packaged with pip/setuptools.

```text
paicode/          <-- Project Root
├── paicode/      <-- Python Package
│   ├── __init__.py
│   ├── agent.py      # The agent's core logic and prompt engineering
│   ├── cli.py        # The main conversational CLI entry point
│   ├── config.py     # Secure API key management
│   ├── workspace.py  # Workspace operations gateway: application-level file ops, path-security, diff-aware modify
│   ├── llm.py        # Bridge to the Large Language Model
│   ├── ui.py         # Rich TUI components
│   ├── awareness.py  # System prompt and awareness helpers
│   └── platforms.py  # OS detection and metadata for command preview
│
├── .gitignore
├── README.md
├── requirements.txt  # Dependencies for pip
├── setup.cfg         # Packaging configuration for setuptools
├── setup.py          # Minimal setup shim (delegates to setup.cfg)
└── pyproject.toml    # Build-system config (setuptools)
```

-----

## **3. Installation and Setup**

You can install Pai Code with Make (recommended for Linux/macOS) or manually (Linux/macOS/Windows). Choose the path that fits your environment.

### **Prerequisites**

  * Python 3.9+
  * Git

### A) Install using Make (Linux/macOS)

1.  Clone the repository

    ```bash
    git clone <REPOSITORY_URL> paicode
    cd paicode
    ```

2.  Create virtualenv, install dependencies, and install CLI launcher

    ```bash
    make setup      # = make install + make install-cli
    # or step-by-step
    make install    # creates .venv and installs deps (editable install)
    make install-cli
    ```

    Notes:
    - The launcher script is installed to `~/.local/bin/pai` and your shell `PATH` is updated in `~/.bashrc`.
    - Open a new terminal or run `source ~/.bashrc` to make sure `pai` is on PATH.

3.  Configure your API key

    ```bash
    pai config --set YOUR_API_KEY_HERE
    ```

4.  Verify

    ```bash
    pai --help
    pai config --show
    ```

### B) Manual installation (Linux/macOS)

1.  Clone repo and create a virtual environment

    ```bash
    git clone <REPOSITORY_URL> paicode
    cd paicode
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  Install dependencies and package

    ```bash
    python -m pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    pip install -e .    # editable install, exposes 'pai' entry point inside venv
    ```

3.  Run

    ```bash
    pai --help
    pai config --set YOUR_API_KEY_HERE
    pai
    ```

Optional without virtualenv (user-site):

```bash
pip install --user .
# ensure ~/.local/bin is on PATH
export PATH="$HOME/.local/bin:$PATH"
pai --help
```

### C) Manual installation (Windows)

1.  Clone and create virtual environment (PowerShell)

    ```powershell
    git clone <REPOSITORY_URL> paicode
    cd paicode
    py -3 -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

2.  Install dependencies and package

    ```powershell
    python -m pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    pip install -e .   # exposes 'pai' entry point in venv
    ```

3.  Run and configure key

    ```powershell
    pai --help
    pai config --set YOUR_API_KEY_HERE
    pai
    ```

If you prefer a global-like launcher on Linux/macOS without activating venv every time, use `make install-cli` as shown above. On Windows, use the virtualenv activation before running `pai`.

### Uninstall the launcher (Linux/macOS)

```bash
make uninstall-cli
```

This removes `~/.local/bin/pai` and cleans up the PATH line added by the installer.

-----

## **4. Security Features**

Security is a core design principle of Pai Code.

  * **Secure Key Storage:** Your API key is never stored in the project directory. It is placed at `~/.config/pai-code/credentials.json` with secure permissions. The config directory is created with `700` and the credentials file is saved with `600` permissions, ensuring only your user can access it (see `paicode/config.py`).
  * **Sensitive Path Blocking (Path Security):** The agent enforces a policy to block access to sensitive files and directories. Deny-list (exact per code): `.env`, `.git`, `venv`, `__pycache__`, `.pai_history`, `.idea`, `.vscode`. Enforcement lives in the centralized workspace gateway (`paicode/workspace.py`) which validates every application-level file operation.
  * **Audit Trail:** Execution logs for shell activity are stored under `.pai_history/` in your project root. A `.gitignore` is auto-created inside to prevent accidental commits (see `paicode/workspace.py`).
  * **Network Guard for Shell:** Obvious network operations are blocked by default (set `PAI_ALLOW_NET=true` to enable). Indicators include: `curl`, `wget`, `http(s)://`, `git clone`, `pip install`, `apt`, `npm`, `yarn`, `brew`, `ssh`, `scp`.

-----

## **5. Usage: A Conversational Workflow**

All development with Pai happens inside a single, interactive session. You don't execute individual file commands; you have a conversation with the agent about what you want to achieve.

### **Configuration (One-Time Setup)**

Manage your API key with the `config` command.

  * `pai config --set <API_KEY>`: Sets or replaces the API key.
  * `pai config --show`: Displays the currently stored key (masked).
  * `pai config --remove`: Deletes the credentials file.

### **Starting an Agent Session**

To begin coding, simply run `pai` or `pai auto`. This will drop you into an interactive session.

```bash
# Start the agent directly
pai
```

### **Interacting with the Agent**

The workflow is designed to be intuitive and iterative.

1.  **Give a High-Level Goal:** Start by asking the agent to observe its surroundings or outlining what you want to build.
2.  **Let it Observe:** The agent will use its internal tools (like `LIST_PATH` or `TREE`) to understand the project structure.
3.  **Ask Follow-up Questions:** Based on its observations, you can then ask it to perform specific actions, like reading a file, modifying code, or creating a new module. Because the agent is stateful, it will remember the context from previous steps.

### **Example Session**

This example shows the agent's ability to observe, remember, and act upon context.

```bash
(pai-code-py3.12) user@localhost:~/space/dev/try/testtpai$ pai auto
╭───────────────────────╮
│ Interactive Auto Mode │
╰───────────────────────╯
i Type 'exit' or 'quit' to leave.

user>: hii pai, lets make a simple project with python, BMI Calculator
╭──────────────────────────────────────────────────── Agent Response ─────────────────────────────────────────────────────╮
│                                                                                                                         │
│  Agent's Plan or Response:                                                                                              │
│  MKDIR::bmi_calculator                                                                                                  │
│  TOUCH::bmi_calculator/main.py                                                                                          │
│  WRITE::bmi_calculator/main.py::A Python script that calculates Body Mass Index (BMI) based on user input for weight    │
│  (kg) and height (cm). It should handle potential non-numeric input and provide an interpretation of the BMI result     │
│  (underweight, normal, overweight, obese).                                                                              │
│  FINISH::The basic structure for the BMI calculator project has been set up, and the main Python file is ready with a   │
│  description of its content. Let me know if you want to modify or run it!                                               │
│                                                                                                                         │
│  Execution Results:                                                                                                     │
│  -> MKDIR::bmi_calculator                                                                                               │
│  ✓ Success: Directory created: bmi_calculator                                                                           │
│  -> TOUCH::bmi_calculator/main.py                                                                                       │
│  ✓ Success: File created: bmi_calculator/main.py                                                                        │
│  -> WRITE::bmi_calculator/main.py::A Python script that calculates Body Mass Index (BMI) based on user input for        │
│  weight (kg) and height (cm). It should handle potential non-numeric input and provide an interpretation of the BMI     │
│  result (underweight, normal, overweight, obese).                                                                       │
│  ✓ Success: Content successfully written to: bmi_calculator/main.py                                                     │
│  -> FINISH::The basic structure for the BMI calculator project has been set up, and the main Python file is ready with  │
│  a description of its content. Let me know if you want to modify or run it!                                             │
│  ✓ Agent: The basic structure for the BMI calculator project has been set up, and the main Python file is ready with a  │
│  description of its content. Let me know if you want to modify or run it!                                               │
│                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

user>: okay, now show me the list of file using tree 
╭──────────────────────────────────────────────────── Agent Response ─────────────────────────────────────────────────────╮
│                                                                                                                         │
│  Agent's Plan or Response:                                                                                              │
│  TREE::bmi_calculator                                                                                                   │
│                                                                                                                         │
│  Execution Results:                                                                                                     │
│  -> TREE::bmi_calculator                                                                                                │
│  bmi_calculator/                                                                                                        │
│  └── main.py                                                                                                            │
│  ✓ Success: Displayed directory structure.                                                                              │
│                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

user>: good, show me the source code
╭──────────────────────────────────────────────────── Agent Response ─────────────────────────────────────────────────────╮
│                                                                                                                         │
│  Agent's Plan or Response:                                                                                              │
│  READ::bmi_calculator/main.py                                                                                           │
│                                                                                                                         │
│  Execution Results:                                                                                                     │
│  -> READ::bmi_calculator/main.py                                                                                        │
│  ╭──────────────────────── Content of bmi_calculator/main.py ────────────────────────╮                                  │
│  │    1 def main():                                                                  │                                  │
│  │    2     print("BMI Calculator")                                                  │                                  │
│  │    3     print("----------------")                                                │                                  │
│  │    4                                                                              │                                  │
│  │    5     # Get weight input                                                       │                                  │
│  │    6     while True:                                                              │                                  │
│  │    7         try:                                                                 │                                  │
│  │    8             weight_str = input("Enter your weight in kilograms (kg): ")      │                                  │
│  │    9             weight = float(weight_str)                                       │                                  │
│  │   10             if weight <= 0:                                                  │                                  │
│  │   11                 print("Weight must be a positive number. Please try again.") │                                  │
│  │   12             else:                                                            │                                  │
│  │   13                 break                                                        │                                  │
│  │   14         except ValueError:                                                   │                                  │
│  │   15             print("Invalid input. Please enter a numeric value for weight.") │                                  │
│  │   16                                                                              │                                  │
│  │   17     # Get height input                                                       │                                  │
│  │   18     while True:                                                              │                                  │
│  │   19         try:                                                                 │                                  │
│  │   20             height_str = input("Enter your height in centimeters (cm): ")    │                                  │
│  │   21             height_cm = float(height_str)                                    │                                  │
│  │   22             if height_cm <= 0:                                               │                                  │
│  │   23                 print("Height must be a positive number. Please try again.") │                                  │
│  │   24             else:                                                            │                                  │
│  │   25                 break                                                        │                                  │
│  │   26         except ValueError:                                                   │                                  │
│  │   27             print("Invalid input. Please enter a numeric value for height.") │                                  │
│  │   28                                                                              │                                  │
│  │   29     # Convert height from cm to meters                                       │                                  │
│  │   30     height_m = height_cm / 100                                               │                                  │
│  │   31                                                                              │                                  │
│  │   32     # Calculate BMI                                                          │                                  │
│  │   33     # BMI = weight (kg) / (height (m))^2                                     │                                  │
│  │   34     if height_m == 0:                                                        │                                  │
│  │   35         print("Error: Height cannot be zero for BMI calculation.")           │                                  │
│  │   36         return                                                               │                                  │
│  │   37                                                                              │                                  │
│  │   38     bmi = weight / (height_m ** 2)                                           │                                  │
│  │   39                                                                              │                                  │
│  │   40     # Interpret BMI                                                          │                                  │
│  │   41     interpretation = ""                                                      │                                  │
│  │   42     if bmi < 18.5:                                                           │                                  │
│  │   43         interpretation = "Underweight"                                       │                                  │
│  │   44     elif 18.5 <= bmi < 25:                                                   │                                  │
│  │   45         interpretation = "Normal weight"                                     │                                  │
│  │   46     elif 25 <= bmi < 30:                                                     │                                  │
│  │   47         interpretation = "Overweight"                                        │                                  │
│  │   48     else:  # bmi >= 30                                                       │                                  │
│  │   49         interpretation = "Obese"                                             │                                  │
│  │   50                                                                              │                                  │
│  │   51     # Display results                                                        │                                  │
│  │   52     print(f"\nYour BMI is: {bmi:.2f}")  # Format to 2 decimal places         │                                  │
│  │   53     print(f"Interpretation: {interpretation}")                               │                                  │
│  │   54                                                                              │                                  │
│  │   55 if __name__ == "__main__":                                                   │                                  │
│  │   56     main()                                                                   │                                  │
│  ╰───────────────────────────────────────────────────────────────────────────────────╯                                  │
│  ✓ Success: Read and displayed bmi_calculator/main.py                                                                   │
│                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

user>: okay tquu
╭──────────────────────────────────────────────────── Agent Response ─────────────────────────────────────────────────────╮
│                                                                                                                         │
│  Agent's Plan or Response:                                                                                              │
│  FINISH::You're welcome! It seems the BMI Calculator project is complete as per your requests. Let me know if you need  │
│  any further assistance or want to work on a new project!                                                               │
│                                                                                                                         │
│  Execution Results:                                                                                                     │
│  -> FINISH::You're welcome! It seems the BMI Calculator project is complete as per your requests. Let me know if you    │
│  need any further assistance or want to work on a new project!                                                          │
│  ✓ Agent: You're welcome! It seems the BMI Calculator project is complete as per your requests. Let me know if you      │
│  need any further assistance or want to work on a new project!                                                          │
│                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

user>: exit
i Session ended.
(pai-code-py3.12) user@localhost:~/space/dev/try/testtpai$ 

```
-----

## **6. Technical Details**

### **Architecture and the Feedback Loop**

A typical interaction follows this stateful data flow:

1.  **User Input** is captured by `cli.py`.
2.  `agent.py` constructs a detailed **prompt**, including relevant conversation history.
3.  `llm.py` sends this prompt to the **Gemini API**.
4.  The LLM returns a structured **action plan** (a sequence of commands).
5.  `agent.py` executes this plan, calling functions in `workspace.py`.
6.  The results (e.g., file contents from `READ`, lists from `LIST_PATH`) are **displayed to the user and recorded in the session log.**
7.  This enriched log becomes the context for the next turn, creating a **stateful memory loop** that allows the agent to learn from its actions.

### **Customization and Extensibility**

As a developer, you can easily extend Pai's internal capabilities:

  * **Add New Agent Commands:** Implement the handling logic inside `paicode/agent.py` (see `_generate_execution_renderables()` for how semantic headers like `READ_FILE::...` are parsed and executed) and add the corresponding primitive in `paicode/workspace.py` if it touches the filesystem. Then document the new command in this README under "Internal Agent Commands".
  * **Tune the Agent's Persona:** The core personality and reasoning process of the agent lives in the `prompt` variable in `agent.py`. By modifying this prompt, you can change its behavior, specialize it for a specific framework, or alter its programming style.

### **Execution Policy and Safety**

  * The workspace root is determined at runtime as the current working directory when you start `pai` (see `paicode/workspace.py` `PROJECT_ROOT = os.path.abspath(os.getcwd())`). All file operations are constrained within this root.
  * The agent enforces a single-command-per-step policy during plan execution to improve transparency and safety. If multiple actions are produced, only the first is executed (see `paicode/agent.py`).
  * OS command previews are shown for transparency before executing actions, and shell commands are subject to timeout and optional streaming. The preview header includes detected OS, shell, and path separator (see `paicode/platforms.py`).

### **Technology Stack**

  * **Language:** Python 3.9+
  * **Dependency Management & Packaging:** pip + setuptools
  * **LLM API:** Google Gemini
  * **Core Libraries:**
      * `google-generativeai`
      * `rich` (for beautiful TUI)

-----

## **7. Scope and Limitations**

To avoid misunderstanding:

* Pai performs application-level file operations within the project workspace. It is not a system-level file manager and does not manage OS file systems.
* Inference is executed by an external LLM via API. Do not share sensitive secrets in prompts unless you understand your provider's data policy.
* Path-security rules block access to sensitive paths and restrict changes using diff-based edits to reduce the risk of large, unintended overwrites.

-----

## **8. Installation (Reference)**

For installation instructions, see Section 3: Installation and Setup. It covers Linux/macOS (Makefile or manual) and Windows (PowerShell) paths, along with launcher installation and verification steps.

## **9. CLI Command Reference**

Below are the primary commands exposed by the entry point `pai`:

### `pai` / `pai auto`
Starts the interactive agent session.

```bash
pai                # default interactive session
pai auto           # explicit alias
pai auto --model gemini-2.5-flash --temperature 0.2
```

### `pai config` (single-key compatibility)

```bash
pai config --set <API_KEY>   # save/replace default key
pai config --show            # show masked key
pai config --remove          # remove legacy single-key file
```

### `pai config` (multi-key management)

```bash
pai config list
pai config add --key <API_KEY> --label <LABEL>
pai config edit --id <ID> --key <NEW_KEY>
pai config rename --id <ID> --label <NEW_LABEL>
pai config remove --id <ID>
pai config enable --id <ID>
pai config disable --id <ID>
```

Notes:
- Keys are stored at `~/.config/pai-code/credentials.json` with secure permissions.
- The agent can round-robin across enabled keys to reduce rate-limit impact.

### Make targets (Linux/macOS)

```bash
make install       # create .venv and install deps
make run           # run agent inside .venv
make install-cli   # install launcher to ~/.local/bin/pai
make setup         # install + launcher
make uninstall-cli # remove launcher
```

If `pai` is not found after `make install-cli`, ensure `~/.local/bin` is on your PATH or open a new terminal.

-----

## **10. Runtime Settings**

Tune the runtime behavior via environment variables:

- PAI_STREAM (default: true)
  - Stream STDOUT/STDERR live to the terminal for shell commands.
- PAI_VERBOSE (default: true)
  - Echo the command being executed as `$ <command>`.
- PAI_SHELL_TIMEOUT (default: 20)
  - Timeout in seconds for shell commands. Shows a clear warning on timeout.
- PAI_ASYNC (default: true)
  - Use asyncio-backed inference to avoid blocking during LLM calls.
- PAI_ALLOW_SHELL_EXEC (default: true)
  - Enable shell execution primitives.
- PAI_ALLOW_NET (default: false)
  - Allow commands with obvious network access (curl, wget, pip install, git clone, etc.).
- PAI_MODEL (default: gemini-2.5-flash)
  - Default model used by the LLM backend. Can be overridden at runtime via CLI flags or env.
- PAI_TEMPERATURE (default: 0.4)
  - Default sampling temperature for the LLM backend.
- PAI_MAX_INFERENCE_RETRIES (default: 25)
  - Maximum attempts for resilient text generation with backoff (see `paicode/llm.py`).
- PAI_MAX_CMDS_PER_STEP (default: 15, capped to 50)
  - Upper bound guard for plan lines per step before truncation (see `paicode/agent.py`).
- PAI_EARLY_FINISH_NOOP (default: 3)
  - Early finish heuristic after this many consecutive no-op/duplicate actions (see `paicode/agent.py`).

Examples:

```bash
export PAI_STREAM=true
export PAI_VERBOSE=true
export PAI_SHELL_TIMEOUT=15
export PAI_ASYNC=true
```

### Testing interactive CLI: EXECUTE_INPUT vs pipe

```text
# Provide stdin directly with EXECUTE_INPUT
EXECUTE_INPUT::python3 demo_cli.py::Alice\n42\n
# Alternative: shell pipe (identical effect)
EXECUTE::bash -lc "printf 'Alice\n42\n' | python3 demo_cli.py"
```

## **11. Internal Agent Commands**

These semantic headers are recognized and executed by the agent (see `paicode/agent.py` and `paicode/workspace.py`). Only one action is executed per step.

- CREATE_DIRECTORY::<path>
- CREATE_FILE::<path>
- READ_FILE::<path>
- WRITE_FILE::<path>::<description>
- MODIFY_FILE::<path>::<description>
- DELETE_PATH::<path>
- MOVE_PATH::<src>::<dst>
- SHOW_TREE::<path>
- LIST_PATHS::<path>
- EXECUTE::<shell_command>
- EXECUTE_INPUT::<shell_command>::<stdin_payload>
- FINISH::<message>

Each action is checked against path-security rules. OS-specific command previews are shown before execution.