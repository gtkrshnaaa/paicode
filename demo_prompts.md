# Pai Demo Prompts - Showcasing Best Capabilities

## Prompt 1: Building Modular Project Structure (MKDIR, TREE, WRITE)

**Objective:** Demonstrate Pai's ability to create well-organized, modular project structure with multiple files.

```
Create a simple task management CLI application in Python with the following requirements:

1. Create a modular project structure with separate files for different concerns
2. Use proper Python package structure with __init__.py files
3. Include these components:
   - Main entry point (cli.py)
   - Task manager class (task_manager.py)
   - Data storage handler (storage.py)
   - Configuration file (config.py)
   - README with usage instructions

4. The application should support:
   - Add new tasks
   - List all tasks
   - Mark tasks as complete
   - Delete tasks
   - Store tasks in JSON file

5. Use clean code practices:
   - Type hints
   - Docstrings
   - Error handling
   - Separation of concerns

Please create the complete project structure with all necessary files.
```

---

## Prompt 2: Modifying Existing Code (READ, MODIFY)

**Objective:** Demonstrate Pai's ability to read, understand, and intelligently modify existing code.

```
Enhance the task management application with the following improvements:

1. Add priority levels to tasks (high, medium, low)
2. Add due dates to tasks with date validation
3. Implement task filtering by:
   - Priority level
   - Completion status
   - Due date range

4. Add a new command to show task statistics:
   - Total tasks
   - Completed vs pending
   - Tasks by priority
   - Overdue tasks count

5. Improve the CLI interface:
   - Add colored output for better readability (use colorama or rich)
   - Add input validation with helpful error messages
   - Add confirmation prompts for destructive operations (delete)

Please read the existing code and make the necessary modifications while maintaining the modular structure and code quality.
```

---

## Why These Prompts Work Well

### Prompt 1 Showcases:
- **MKDIR**: Creating organized directory structure
- **TREE**: Understanding project hierarchy
- **WRITE**: Creating multiple files with quality code
- **Planning**: Breaking down requirements into modular components
- **Best Practices**: Type hints, docstrings, separation of concerns

### Prompt 2 Showcases:
- **READ**: Understanding existing codebase
- **MODIFY**: Surgical, focused modifications across multiple files
- **Intelligence**: Maintaining existing patterns and style
- **Complexity**: Adding features without breaking existing functionality
- **Integration**: Connecting new features with existing code

### Combined Impact:
1. **Modular Design**: Not a single-file mess, but proper project structure
2. **Real-world Scenario**: Actual development workflow (build → enhance)
3. **Code Quality**: Production-ready code with proper practices
4. **Progressive Complexity**: Start simple, then add features
5. **Maintainability**: Easy to understand and extend

---

## Expected Results

### After Prompt 1:
```
task_manager/
├── README.md
├── task_manager/
│   ├── __init__.py
│   ├── cli.py
│   ├── task_manager.py
│   ├── storage.py
│   └── config.py
└── tasks.json (created at runtime)
```

### After Prompt 2:
- All existing files modified with new features
- Enhanced CLI with colors and validation
- New statistics command
- Priority and due date support
- Improved user experience

---

## Usage Tips

1. **Run Prompt 1 first** to create the base project
2. **Test the application** to see it works
3. **Run Prompt 2** to see how Pai enhances existing code
4. **Compare before/after** to see the quality of modifications

This demonstrates Pai's full workflow: **Build → Test → Enhance → Maintain**
