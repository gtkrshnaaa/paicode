# Usage & Commands

Paicode is designed to be invoked from the command line. It operates on the directory where it was launched.

## Starting Paicode

### Single Action Mode
If you have a quick task or query, you can pass it directly as an argument:

```bash
pai "find all instances of the calculate_tax function"
```

### Interactive Auto Mode
For continuous interaction and complex tasks, enter the interactive mode. Paicode will maintain context of the conversation and the project state.

```bash
pai auto
```

## Available Internal Commands

Paicode interacts with your files via a predefined set of commands. These are executed by the agent internally based on your natural language requests:

- `MKDIR::path`
  Creates a new directory at the specified path.

- `TOUCH::path`
  Creates an empty file at the specified path.

- `WRITE::path::description`
  Writes entirely new content to a file. 

- `MODIFY::path::description`
  Applies surgical edits (Search & Replace) to an existing file. This is preferred for large files to conserve tokens and reduce errors.

- `READ::path`
  Reads the content of a file into the agent's context.

- `LIST_PATH::path`
  Lists the files and subdirectories within a specific directory.

- `RM::path`
  Removes a file or directory.

- `MV::source::destination`
  Moves or renames a file or directory.

- `TREE::path`
  Generates a tree representation of the directory structure.

- `SEARCH::pattern::path`
  Conducts a Ripgrep search for a specific pattern within the given path.

- `MAP_ROOT::path`
  Analyzes the project structure to identify the technology stack (e.g., Python, Node.js, PHP) and summarize key dependencies.

- `RUN_COMMAND::command`
  Executes a safe bash command (e.g., `git status`, `pytest`, `npm install`). The `cd` command is blocked to prevent losing working directory context. Includes a timeout mechanism to prevent hanging.

- `DIAGNOSE`
  Captures a snapshot of the live system state, including processes consuming the most memory (`ps aux`) and active network ports (`netstat` / `lsof`).

- `SNIFF_LOGS::pattern`
  Searches for error patterns across common log directories automatically.

- `PROFILE::script_path`
  Profiles a Python script using `cProfile` and returns a summary of the most time-consuming functions.

- `FINISH::message`
  Signals the completion of a task iteration.

## Keyboard Shortcuts in Interactive Mode

- `Ctrl+C` (once): Interrupts the current AI response. Useful if the agent is outputting an incorrect plan. The session remains active.
- `Ctrl+C` (twice): Exits the session completely.
- `exit` or `quit`: Exits the session safely.

## Project History
When you run `pai auto`, Paicode creates a `.pai_history/` directory in the current working directory. This folder contains detailed logs of the session's commands, the agent's internal thought processes, and the execution results.
