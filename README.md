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

3.  **Configure Your API Key**
    Pai Code uses a simple, secure single-key configuration system. Your API key is stored in your home config directory with restricted permissions.

    ```bash
    # Set your Google Gemini API key
    pai config set YOUR_API_KEY

    # Show the current API key (masked for security)
    pai config show

    # Remove the stored API key
    pai config remove

    # Validate the current API key
    pai config validate
    ```

    **Key Management:**
    - Keys are securely stored in `~/.config/pai-code/credentials.json` with `600` file permissions
    - Only your user account can access the stored key
    - You can change your API key at any time with `pai config set <NEW_KEY>`
    - The new key will be used immediately on the next request (no restart needed)

    **Notes:**
    - Obtain your Google Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
    - Keep your API key private and never commit it to version control
    - If you suspect your key is compromised, regenerate it immediately in Google Cloud Console

4.  **Verify the Installation**

    ```bash
    # Check if the main command is available
    pai --help

    # Verify that the API key is configured
    pai config show

    # Validate the API key format
    pai config validate
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

Manage your API key with the `config` command:

  * `pai config set <API_KEY>`: Set or update your Google Gemini API key.
  * `pai config show`: Display the current API key (masked for security).
  * `pai config remove`: Remove the stored API key.
  * `pai config validate`: Validate that the current API key is properly configured.

### **Starting an Agent Session**

To begin coding, simply run `pai`. This will drop you into an interactive conversational session.

```bash
# Start the agent
pai
```
Pai example prompt:
```bash
Hi Pai, create a Python boilerplate project for a simple number range classification task. For now, use a basic array as the data source instead of a CSV file.  
For example, generate an array of random numbers and classify them into categories like “low”, “medium”, and “high” based on defined numeric ranges. Make the structure modular and ready to be replaced with CSV input later.  
Include separate functions for loading data, preprocessing, and classification. If possible, use a class-based design to make future expansion easier.
```

### **Interacting with the Agent**

The workflow uses a single-shot intelligence system with exactly 2 API calls per request:

1.  **Planning Phase (Call 1):** Describe what you want to accomplish. The agent analyzes your request and creates a detailed execution plan.
2.  **Execution Phase (Call 2):** The agent executes the plan, performing file operations, code modifications, and other tasks as needed.
3.  **Iterative Refinement:** You can ask follow-up questions or request modifications. The agent maintains context from previous interactions within the session.

**Example Workflow:**
```
user> Create a Python script that reads a CSV file and prints the first 10 rows

[Agent analyzes request and creates plan]

[Agent executes: creates script, handles errors, provides feedback]

user> Now add error handling for missing files

[Agent modifies the script based on context from previous interaction]
```


## **6. Technical Details**

### **Architecture and the Single-Shot Intelligence System**

Pai Code uses a **Single-Shot Intelligence** approach with exactly 2 API calls per user request:

**Call 1 - Planning Phase:**
1.  **User Input** is captured by `cli.py`.
2.  `agent.py` constructs a detailed **planning prompt**, including user request and conversation context.
3.  `llm.py` sends the planning prompt to the **Gemini API**.
4.  The LLM returns a comprehensive **execution plan** (analysis, strategy, and step-by-step actions).

**Call 2 - Execution Phase:**
5.  `agent.py` constructs an **execution prompt** based on the plan.
6.  `llm.py` sends the execution prompt to the **Gemini API**.
7.  The LLM returns **executable commands** (READ, WRITE, MODIFY, etc.).
8.  `agent.py` executes these commands, calling functions in `workspace.py`.
9.  The results are **displayed to the user and recorded in the session log**.
10. Session context is maintained for follow-up interactions, allowing the agent to learn from previous actions within the session.

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

## **7. Recent Updates and Bug Fixes**

### **API Key Caching Fix (Latest)**
- **Issue:** When changing API key with `pai config set <NEW_KEY>`, the new key was not used immediately due to model object caching.
- **Solution:** Model object is now recreated on every `_prepare_runtime()` call, ensuring fresh API key configuration is always used.
- **Impact:** API key changes now take effect immediately without requiring application restart.
- **Technical Details:** See `llm.py` `_prepare_runtime()` function for implementation details.

-----

## **8. Scope and Limitations**

To avoid misunderstanding:

* Pai performs application-level file operations within the project workspace. It is not a system-level file manager and does not manage OS file systems.
* Inference is executed by an external LLM via API. Do not share sensitive secrets in prompts unless you understand your provider's data policy.
* Path-security rules block access to sensitive paths and restrict changes using diff-based edits to reduce the risk of large, unintended overwrites.