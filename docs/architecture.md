# Internal Architecture

Paicode relies on a sequence of internal logic loops to process user requests safely, maintain context, and execute file operations reliably.

## The Execution Loop

When you submit a request in interactive mode (`pai auto`), Paicode follows a strict execution logic:

1. **Context Compression**: 
   The agent gathers the project's environment variables, recent history, and system capabilities. To prevent token overflow, this context is continually summarized and compressed to the most relevant information.

2. **Intent Classification**: 
   The request is evaluated to determine if it is a simple conversational query ("What is this project?") or an actionable task requiring file manipulation.

3. **Pre-Execution Thinking (Planning)**: 
   The agent generates a brief, structured plan outlining the files it intends to read, tools it plans to use, and edge cases to consider. This step emphasizes discovery before modification.

4. **Action Generation**: 
   The agent translates its plan into specific internal commands (e.g., `READ::main.py`, `SEARCH::auth_token::src/`).

5. **Execution & Validation**: 
   The commands are executed by the `workspace.py` module. The standard output and standard error of these commands are captured and returned to the agent.

6. **Integrity Check (Self-Healing)**: 
   After executing an action, the agent conducts an integrity check. It evaluates the output to confirm if the action succeeded (e.g., checking if a linter passed after modifying a Python file). If the action failed or introduced errors, Paicode enters a *Self-Healing* loop, attempting to correct its previous output autonomously.

7. **Architectural Guardrails**:
   If the execution involved writing or modifying code, a secondary audit evaluates the changes for obvious security vulnerabilities (SQL injection, XSS) and basic architectural patterns. A low score on this audit can also trigger the Self-Healing loop.

## Persistent Memory (`.pai_brain`)

To maintain context across multiple sessions, Paicode manages a `.pai_brain/` directory.

- **`task.md`**: The agent creates and maintains a local checklist representing the steps required to complete the current objective. This allows you to close the terminal, reopen it later, and Paicode will resume exactly where it left off by reading the progress in this file.

## Surgical Modification Protocol (`MODIFY`)

The `MODIFY` command relies on an internal Search & Replace algorithm rather than writing files wholesale. 

1. The agent reads the original file.
2. It outputs blocks defining the precise existing code to be searched (`<<<< SEARCH`) and the new code to replace it (`====`).
3. The system ensures the search block matches the file exactly (including indentation) before applying the change. This prevents unintentional modifications and formatting drift.

## Environment Detection

During startup, Paicode "sniffs" the host environment. It detects the installation of required binaries like Git, npm, Python 3, Docker, or tools like Bandit. The availability of these tools dictates what autonomous commands (like automatic security linting) are activated during the session.
