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

The project uses a standard package structure managed by Poetry.

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
├── poetry.lock     # Poetry's lock file for consistent installs
└── pyproject.toml  # Project definition and dependencies for Poetry
```

-----

## **3. Installation and Setup**

The setup process is simple and integrated with Poetry.

### **Prerequisites**

  * **Python 3.9+**
  * **Git**
  * **Poetry**

### **Step-by-Step Guide**

1.  **Clone the Repository**

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
  * **Sensitive Path Blocking (Path Security):** The agent enforces a policy to block access to sensitive files and directories like `.env`, `.git`, `venv/`, and IDE-specific folders. This is implemented by a centralized workspace gateway (`workspace.py`) that inspects every application-level file operation in the project workspace.

-----

## **5. Usage: A Conversational Workflow**

All development with Pai happens inside a single, interactive session. You don't execute individual file commands; you have a conversation with the agent about what you want to achieve.

### **Configuration (One-Time Setup)**

Manage your API key with the `config` command.

  * `poetry run pai config --set <API_KEY>`: Sets or replaces the API key.
  * `poetry run pai config --show`: Displays the currently stored key (masked).
  * `poetry run pai config --remove`: Deletes the credentials file.

### **Starting an Agent Session**

To begin coding, simply run `pai` or `pai auto`. This will drop you into an interactive session.

```bash
# For an interactive session, using 'poetry shell' is more convenient
poetry shell

# Start the agent
(pai-code-py3.12)$ pai
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

  * **Add New Agent Commands:** Add a command to `VALID_COMMANDS` in `agent.py`, create a corresponding function in `workspace.py`, and add the handling logic in `_generate_execution_renderables`. This gives the agent a new tool to use in its planning.
  * **Tune the Agent's Persona:** The core personality and reasoning process of the agent lives in the `prompt` variable in `agent.py`. By modifying this prompt, you can change its behavior, specialize it for a specific framework, or alter its programming style.

### **Technology Stack**

  * **Language:** Python 3.9+
  * **Dependency Management & Packaging:** Poetry
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