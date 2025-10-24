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

```
paicode/          <-- Project Root
├── paicode/      <-- Python Package
│   ├── __init__.py
│   ├── agent.py      # The agent's core logic and prompt engineering
│   ├── cli.py        # The main conversational CLI entry point
│   ├── config.py     # Secure API key management
│   ├── workspace.py # Workspace operations gateway: application-level file ops, path-security, diff-aware modify
│   ├── llm.py        # Bridge to the Large Language Model
│   └── ui.py         # Rich TUI components
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

The setup process uses pip and Make.

### **Prerequisites**

  * **Python 3.10+**
  * **Git**

### **Step-by-Step Guide**

1.  **Clone the Repository**

    ```bash
    # Replace <REPOSITORY_URL> with the actual Git URL
    git clone <REPOSITORY_URL> paicode
    cd paicode
    ```

2.  **Install CLI (pip, user-site)**

    ```bash
    # From the project's root directory
    make install-cli
    # or
    pip install --user .
    ```

3.  **Configure Your API Keys (Multi-Key Support)**
    Pai Code includes a secure, built‑in configuration manager with multi-key support. Keys are stored under your home config and can be switched via an explicit default.

    ```bash
    # Add keys with IDs (recommended)
    pai config add g1 YOUR_API_KEY_1
    pai config add g2 YOUR_API_KEY_2
    pai config add g3 YOUR_API_KEY_3

    # List stored keys (masked)
    pai config list

    # Set the default key to use
    pai config set-default g1

    # Show a specific key (masked)
    pai config show g1

    # Remove a key by ID
    pai config remove g3
    ```

    Notes:
    - Legacy flags like `pai config --set/--show/--remove` are still available but DEPRECATED. Prefer the subcommands shown above.
    - Keys are securely stored in your user config directory (not in the repository).

4.  **Verify the Installation**

    ```bash
    # Check if the main command is available
    pai --help

    # Verify that the API key is configured
    pai config --show
    ```

-----

## **4. Security Features**

Security is a core design principle of Pai Code.

  * **Secure Key Storage:** Your API key is never stored in the project directory. It is placed in a `.config` folder in your home directory with `600` file permissions, meaning only your user account can access it.
  * **Sensitive Path Blocking (Path Security):** The agent enforces a policy to block access to sensitive files and directories like `.env`, `.git`, `venv/`, and IDE-specific folders. This is implemented by a centralized workspace gateway (`workspace.py`) that inspects every application-level file operation in the project workspace.

-----

## **5. Usage: A Conversational Workflow**

All development with Pai happens inside a single, interactive session. You don't execute individual file commands; you have a conversation with the agent about what you want to achieve.

### **Configuration (One-Time Setup)**

Manage your API keys with the `config` command (multi-key mode):

  * `pai config add <ID> <API_KEY>`: Add a new API key with an identifier.
  * `pai config list`: List all stored keys (masked) and the current default.
  * `pai config show <ID>`: Display a masked version of the key by ID.
  * `pai config remove <ID>`: Remove a stored key by ID.
  * `pai config set-default <ID>`: Set which key is used by the agent.

Legacy (deprecated) flags retained for compatibility:

  * `pai config --set <API_KEY>`
  * `pai config --show`
  * `pai config --remove`

### **Starting an Agent Session**

To begin coding, simply run `pai` or `pai auto`. This will drop you into an interactive session.

```bash
# Start the agent directly
pai
```
Pai example prompt:
```bash
Hi Pai, create a Python boilerplate project for a simple number range classification task. For now, use a basic array as the data source instead of a CSV file.  
For example, generate an array of random numbers and classify them into categories like “low”, “medium”, and “high” based on defined numeric ranges. Make the structure modular and ready to be replaced with CSV input later.  
Include separate functions for loading data, preprocessing, and classification. If possible, use a class-based design to make future expansion easier.
```

### **Interacting with the Agent**

The workflow is designed to be intuitive and iterative.

1.  **Give a High-Level Goal:** Start by asking the agent to observe its surroundings or outlining what you want to build.
2.  **Let it Observe:** The agent will use its internal tools (like `LIST_PATH` or `TREE`) to understand the project structure.
3.  **Ask Follow-up Questions:** Based on its observations, you can then ask it to perform specific actions, like reading a file, modifying code, or creating a new module. Because the agent is stateful, it will remember the context from previous steps.


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

  * **Add New Agent Commands:** Add a command to `VALID_COMMANDS` in `agent.py`, create a corresponding function in `workspace.py`, and add the handling logic in `_generate_execution_renderables`. This gives the agent a new tool to use in its planning.
  * **Tune the Agent's Persona:** The core personality and reasoning process of the agent lives in the `prompt` variable in `agent.py`. By modifying this prompt, you can change its behavior, specialize it for a specific framework, or alter its programming style.

### **Technology Stack**

  * **Language:** Python 3.10+
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