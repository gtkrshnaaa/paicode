# **Pai Code: Agentic AI Coding Companion**

> **An autonomous, command-line-based AI agent designed to accelerate software development through intelligent, direct file system interaction.**

**Pai Code** is a local AI assistant that operates directly from your terminal. It serves as a true developer companion, capable of understanding high-level goals and translating them into concrete project structures, code, and file management tasks. By interacting with the file system, any action Pai takes is instantly reflected in your favorite IDE, creating a seamless and powerful workflow.

## **1. Core Philosophy**

Pai Code is built on a set of guiding principles that define its purpose and design:

  * **Local-First and Private:** Your code and your interactions are yours alone. Pai operates entirely on your local machine. Nothing is stored or tracked on a remote server beyond the necessary API calls to Gemini.
  * **CLI-Native Workflow:** We believe in the power and speed of the command line. Pai Code is built for developers who thrive in the terminal, augmenting their workflow without forcing them into a GUI.
  * **Editor Agnostic:** By operating directly on the file system, Pai is compatible with any text editor or IDE you choose, from VS Code and JetBrains IDEs to Vim or Emacs.
  * **Focused & Minimalist:** Pai does one thing and does it well: it builds and manages code. There are no complex GUIs or plugins to manage.

-----

## **2. Project Structure**

The project uses a standard package structure managed by Poetry.

```
paicode/            <-- Project Root
├── paicode/        <-- Python Package
│   ├── __init__.py
│   ├── agent.py      # The agent's core logic and prompt engineering
│   ├── cli.py        # The main CLI entry point
│   ├── config.py     # Secure API key management
│   ├── fs.py         # File system gateway and security layer
│   ├── llm.py        # Bridge to the Gemini Large Language Model
│   └── ui.py         # Rich TUI components
│
├── .gitignore
├── README.md
├── poetry.lock     # Poetry's lock file for consistent installs
└── pyproject.toml  # Project definition and dependencies for Poetry
```

-----

## **3. Installation and Setup**

With Poetry, the setup process is simpler and more integrated.

### **Prerequisites**

  * **Python 3.9+**
  * **Git**
  * **Poetry**

### **Step-by-Step Guide**

1.  **Clone the Repository**
    First, get the source code from the repository and navigate into the project directory.

    ```bash
    # Replace <REPOSITORY_URL> with the actual Git URL
    git clone <REPOSITORY_URL> paicode
    cd paicode
    ```

2.  **Install Dependencies**
    Poetry will read the `pyproject.toml` file, automatically create a virtual environment, and install all required dependencies.

    ```bash
    # Run from the project's root directory
    poetry install
    ```

3.  **Configure Your API Key**
    Pai Code uses a secure, built-in configuration manager. You only need to set your key once.

    ```bash
    # Replace YOUR_API_KEY_HERE with your Gemini API key
    poetry run pai config --set YOUR_API_KEY_HERE
    ```

    This command securely stores your key in `~/.config/pai-code/credentials`.

4.  **Verify the Installation**
    Confirm that everything is set up correctly.

    ```bash
    # Check if the main command is available
    poetry run pai --help

    # Verify that the API key is configured
    poetry run pai config --show
    ```

-----

## **4. Security Features**

Security is a core design principle of Pai Code.

  * **Secure Key Storage:** Your API key is never stored in the project directory. It is placed in a `.config` folder in your home directory with `600` file permissions, meaning only your user account can access it.
  * **Sensitive Path Blocking:** The agent is hard-coded to **deny all access** (read, write, or list) to sensitive files and directories like `.env`, `.git`, `venv/`, and IDE-specific folders. This is enforced by a centralized security gateway (`_is_path_safe`) that inspects every file operation.

-----

## **5. Usage and Command Reference**

To run all `pai` commands, you can either use `poetry run` or enter the virtual shell with `poetry shell`.

  * **Using `poetry run` (for single commands):** `poetry run pai <command>`
  * **Using `poetry shell` (for interactive sessions):** Run `poetry shell`, then you can call `pai <command>` directly.

### **Configuration: `pai config`**

  * **Description:** Manages the essential API key configuration.
  * **Sub-commands:**
      * `--set <API_KEY>`: Sets or replaces the API key.
      * `--show`: Displays the currently stored key in a masked format.
      * `--remove`: Deletes the credentials file.
  * **Usage:**
    ```bash
    poetry run pai config --set "YOUR_GEMINI_API_KEY"
    ```

### **File System Operations**

These are the building blocks for development.

  * **`poetry run pai touch <filename>`**

      * **Description:** Creates a new, empty file at the specified path.
      * **Example:** `poetry run pai touch paicode/app/main.py`

  * **`poetry run pai mkdir <dirname>`**

      * **Description:** Creates a new directory.
      * **Example:** `poetry run pai mkdir tests/unit`

  * **`poetry run pai read <filename>`**

      * **Description:** Reads the content of a file and prints it to the console.
      * **Example:** `poetry run pai read pyproject.toml`

  * **`poetry run pai write <file> "<task>"`**

      * **Description:** An AI-powered command that generates code based on a task description and writes it to a file.
      * **Example:** `poetry run pai write paicode/utils.py "Create a utility function to validate email addresses using regex."`

  * **`poetry run pai tree [path]`**

      * **Description:** Displays a visual, tree-like representation of the directory structure.
      * **Example:** `poetry run pai tree paicode`

  * **`poetry run pai rm <path>`**

      * **Description:** Deletes a file or an entire directory recursively.
      * **Example:** `poetry run pai rm old_feature.py`

  * **`poetry run pai mv <source> <destination>`**

      * **Description:** Moves or renames a file or directory.
      * **Example:** `poetry run pai mv paicode/utils.py paicode/helpers.py`

### **Auto Mode: The Autonomous Agent**

The `pai auto` command unlocks the agent's full potential as an autonomous developer.

  * **The Agent's Mind:**

      * **Goal Decomposition:** When given a high-level task, the agent's first step is to decompose the abstract idea into concrete, programmable components.
      * **Plan Formulation:** This mental model is then translated into a machine-readable, step-by-step plan composed of the file system commands listed above.
      * **Stateful Interaction:** The agent remembers the conversation history within a session, allowing for iterative development. You can ask it to build a feature, then ask it to modify or add to that same feature.

  * **Example `auto` Session:**
    This example shows how the agent handles a request to build a simple application from scratch.

    ```bash
    # For an interactive session, using 'poetry shell' is more convenient
    poetry shell

    (paicode-py3.12) $ pai auto
    ──────────────────────────── Interactive Auto Mode ─────────────────────────────
    i Type 'exit' or 'quit' to leave.
    pai>: Create a modular Python program to calculate Body Mass Index (BMI)...

    # ... The agent's output remains the same ...
    ```

-----

## **6. Technical Details**

### **Architecture and Data Flow**

A typical `auto` mode command follows this internal data flow:

1.  **User Input** (`poetry run pai auto "..."`) is captured by `cli.py`.
2.  `agent.py` loads session history and constructs a detailed **prompt** for the LLM.
3.  `llm.py` sends this prompt to the **Gemini API**.
4.  The LLM returns a structured **action plan** (a sequence of commands).
5.  `agent.py` executes this plan, calling functions in `fs.py` for each step.
6.  The **results** are printed and added to the session history.

### **Customization and Extensibility**

As a developer, you can easily extend Pai's capabilities:

  * **Add New Commands:** Add a command to `VALID_COMMANDS` in `agent.py`, create a corresponding function in `fs.py`, and add the handling logic in `_execute_plan`.
  * **Tune the Agent's Persona:** The core personality of the agent lives in the `prompt` variable in `agent.py`. By modifying this prompt, you can change its behavior, specialize it for a specific framework, or change its programming style.

### **Technology Stack**

  * **Language:** Python 3.9+
  * **Dependency Management & Packaging:** Poetry
  * **LLM API:** Google Gemini
  * **Core Libraries:**
      * `google-generativeai`
      * `rich` (for beautiful TUI)