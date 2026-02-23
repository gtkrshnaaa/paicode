# Features & Capabilities

Paicode operates as a localized autonomous agent capable of performing a variety of software engineering tasks by inspecting and manipulating files directly on the user's system.

## Core Capabilities

1. **File System Operations**
   Paicode can read, write, move, rename, and delete files and directories. It builds an understanding of your project by reading the directory tree and file contents before attempting modifications.

2. **Surgical Code Editing**
   Instead of rewriting entire files, Paicode uses a Search & Replace protocol. It identifies the exact lines to change and applies modifications iteratively, significantly reducing token consumption and minimizing logical drift.

3. **Pattern Searching**
   Using Ripgrep under the hood, Paicode can search for variable definitions, function names, or specific error patterns across an entire repository quickly.

4. **Architectural Mapping**
   Paicode can "map" the root of a project to determine the foundational technology stack (e.g., Laravel, React, Django). It summarizes key configuration files like `package.json` or `requirements.txt` to gather context about the environment.

5. **Safe Terminal Execution**
   Paicode can execute terminal commands (e.g., running unit tests, installing dependencies, checking git status). Destructive operations and context-breaking commands like `cd` are filtered out. Command execution is limited by timeouts to prevent hanging processes.

## Advanced Primitives

1. **Self-Healing Execution Loop**
   Paicode evaluates the results of its own actions. If an action fails (e.g., a test fails after code modification, or a syntax error is introduced), Paicode autonomously attempts to diagnose and fix the issue without requiring user intervention.

2. **System Diagnosics**
   Paicode can inspect live system states using native Linux tools. It can check for currently running processes consuming high memory (using `ps aux`) and list active network ports (using `netstat` and `lsof`).

3. **Log Sniffing**
   Paicode can search for error patterns automatically within common log directories (`/var/log`, `storage/logs`, `logs/`) to contextualize issues.

4. **Architectural Guardrails**
   Before determining that a coding task is complete, Paicode conducts an internal architectural audit. It checks the modifications for common security vulnerabilities (e.g., SQL Injection, XSS), proper error handling, and separation of concerns.

5. **Performance Profiling**
   Paicode is equipped to run Python scripts under `cProfile` and measure execution time. It uses these empirical datasets to identify bottlenecks in the code.
