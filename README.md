
# **Pai Code: Agentic AI Coding Companion**

> **An autonomous, command-line-based AI agent designed to accelerate software development through intelligent, direct file system interaction.**

**Pai Code** is a local AI assistant that operates directly from your terminal. It serves as a true developer companion, capable of understanding high-level goals and translating them into concrete project structures, code, and file management tasks. By interacting with the file system, any action Pai takes is instantly reflected in your favorite IDE, creating a seamless and powerful workflow.

## **1. Core Philosophy**

Pai Code is built on a set of guiding principles that define its purpose and design:

  * **Local-First and Private:** Your code and your interactions are yours alone. Pai operates entirely on your local machine. Nothing is stored or tracked on a remote server beyond the necessary API calls to Gemini.
  * **CLI-Native Workflow:** We believe in the power and speed of the command line. Pai Code is built for developers who thrive in the terminal, augmenting their workflow without forcing them into a GUI.
  * **Editor Agnostic:** By operating directly on the file system, Pai is compatible with any text editor or IDE you choose, from VS Code and JetBrains IDEs to Vim or Emacs.
  * **Focused & Minimalist:** Pai does one thing and does it well: it builds and manages code. There are no complex GUIs or plugins to manage.

## **2. Project Structure**

The project uses a standard Python application structure to separate source code from configuration.

```
pai-code/
├── .gitignore
├── README.md
├── requirements.txt
├── makefile
│
└── pai_code/
    ├── __init__.py
    ├── agent.py     # The agent's core logic and prompt engineering
    ├── cli.py       # The main CLI entry point (using argparse)
    ├── config.py    # Secure API key management
    ├── fs.py        # File system gateway and security layer
    └── llm.py       # Bridge to the Gemini Large Language Model
```

## **3. Installation and Setup**

Setting up Pai Code is designed to be quick and straightforward.

### **Prerequisites**

  * **Python 3.9+**
  * **Git**

### **Step-by-Step Guide**

1.  **Clone the Repository**
    First, get the source code from the repository and navigate into the project directory.

    ```bash
    # Replace <REPOSITORY_URL> with the actual Git URL
    git clone <REPOSITORY_URL> paicode
    cd paicode
    ```

2.  **Create and Activate a Virtual Environment**
    It is crucial to use a virtual environment to isolate project dependencies.

    ```bash
    # Create the virtual environment
    python3 -m venv venv

    # Activate the environment (on Linux/macOS)
    source venv/bin/activate
    ```

    Your terminal prompt will now be prefixed with `(venv)`.

3.  **Install in Editable Mode**
    Install the project and its dependencies. The `-e` (editable) flag allows you to modify the source code and have the changes take effect immediately.

    ```bash
    # Run from the project's root directory
    pip install -e .
    ```

4.  **Configure Your API Key**
    Pai Code uses a secure, built-in configuration manager. You must set your key once.

    ```bash
    # Replace YOUR_API_KEY_HERE with your actual Gemini API key
    pai config --set YOUR_API_KEY_HERE
    ```

    This command securely stores your key in `~/.config/pai-code/credentials` with strict file permissions.

5.  **Verify the Installation**
    Confirm that everything is set up correctly.

    ```bash
    # Check that the main command is available
    pai --help

    # Verify that your API key is configured
    pai config --show
    ```

## **4. Security Features**

Security is a core design principle of Pai Code.

  * **Secure Key Storage:** Your API key is never stored in the project directory. It is placed in a `.config` folder in your home directory with `600` file permissions, meaning only your user account can access it.
  * **Sensitive Path Blocking:** The agent is hard-coded to **deny all access** (read, write, or list) to sensitive files and directories like `.env`, `.git`, `venv/`, and IDE-specific folders. This is enforced by a centralized security gateway (`_is_path_safe`) that inspects every file operation.

## **5. Usage and Command Reference**

This section provides a detailed reference for every command available in Pai Code.

### **Configuration: `pai config`**

  * **Description:** Manages the essential API key configuration.
  * **Sub-commands:**
      * `--set <API_KEY>`: Sets or replaces the API key.
      * `--show`: Displays the currently stored key in a masked format.
      * `--remove`: Deletes the credentials file.
  * **Usage:**
    ```bash
    pai config --set "YOUR_GEMINI_API_KEY"
    ```

### **File System Operations**

These are the building blocks for development.

  * **`pai touch <filename>`**

      * **Description:** Creates a new, empty file at the specified path.
      * **Example:** `pai touch src/app/main.py`

  * **`pai mkdir <dirname>`**

      * **Description:** Creates a new directory.
      * **Example:** `pai mkdir tests/unit`

  * **`pai read <filename>`**

      * **Description:** Reads the content of a file and prints it to the console.
      * **Example:** `pai read src/app/main.py`

  * **`pai write <file> "<task>"`**

      * **Description:** An AI-powered command that generates code based on a task description and writes it to a file.
      * **Example:** `pai write src/utils.py "Create a utility function to validate email addresses using regex."`

  * **`pai tree [path]`**

      * **Description:** Displays a visual, tree-like representation of the directory structure.
      * **Example:** `pai tree src`

  * **`pai rm <path>`**

      * **Description:** Deletes a file or an entire directory recursively.
      * **Example:** `pai rm old_feature.py`

  * **`pai mv <source> <destination>`**

      * **Description:** Moves or renames a file or directory.
      * **Example:** `pai mv src/utils.py src/helpers.py`

### **Auto Mode: The Autonomous Agent**

The `pai auto` command unlocks the agent's full potential as an autonomous developer.

  * **The Agent's Mind:**

      * **Goal Decomposition:** When given a high-level task, the agent's first step is to decompose the abstract idea into concrete, programmable components.
      * **Plan Formulation:** This mental model is then translated into a machine-readable, step-by-step plan composed of the file system commands listed above.
      * **Stateful Interaction:** The agent remembers the conversation history within a session, allowing for iterative development. You can ask it to build a feature, then ask it to modify or add to that same feature.

  * **Example `auto` Session:**
    This example shows how the agent handles a request to build a simple application from scratch.

    ```bash
    (venv) user@localhost:~/my-new-app$ pai auto
    Entering interactive auto mode. Type 'exit' or 'quit' to leave.
    pai> Create a modular Python program to calculate Body Mass Index (BMI). It should take weight in kg and height in meters.

    Thinking...

    --- Plan Execution Results ---
    Of course. I will create a modular structure for the BMI calculator. Here is my plan:
    1. Create a main directory for the project.
    2. Inside, create a 'main.py' to handle user input and output.
    3. Create a 'logic.py' to contain the core BMI calculation function.
    4. Populate both files with the necessary code.

    MKDIR::bmi_calculator
    -> Action: MKDIR::bmi_calculator
    Success: Directory created: bmi_calculator
    TOUCH::bmi_calculator/main.py
    -> Action: TOUCH::bmi_calculator/main.py
    Success: File created: bmi_calculator/main.py
    TOUCH::bmi_calculator/logic.py
    -> Action: TOUCH::bmi_calculator/logic.py
    Success: File created: bmi_calculator/logic.py
    WRITE::bmi_calculator/logic.py::Create a Python function 'calculate_bmi(weight_kg, height_m)' that computes and returns the BMI. Include error handling for division by zero.
    -> Action: Writing content to file 'bmi_calculator/logic.py'...
    Success: Content successfully written to: bmi_calculator/logic.py
    WRITE::bmi_calculator/main.py::Create a main execution block that imports the 'calculate_bmi' function, prompts the user for their weight and height, calls the function, and prints the result in a user-friendly format.
    -> Action: Writing content to file 'bmi_calculator/main.py'...
    Success: Content successfully written to: bmi_calculator/main.py
    FINISH::The BMI calculator program has been created in the 'bmi_calculator' directory. You can run it via 'python bmi_calculator/main.py'.
    Agent: The BMI calculator program has been created in the 'bmi_calculator' directory. You can run it via 'python bmi_calculator/main.py'.
    ---------------------------------

    pai> exit
    Session ended.
    ```

## **6. Technical Details**

### **Architecture and Data Flow**

A typical `auto` mode command follows this internal data flow:

1.  **User Input** (`pai auto "..."`) is captured by `cli.py`.
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
  * **LLM API:** Google Gemini
  * **Core Libraries:**
      * `google-generativeai`
      * `argparse`
      * Standard libraries: `os`, `pathlib`, `shutil`

---