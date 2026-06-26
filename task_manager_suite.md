# 📋 CLI Task Manager & Terminal Security Suite

This suite combines a clean, well-documented Python CLI-based Task Manager with a comprehensive security checklist for Python terminal-based applications.

---

## 🛠️ Part 1: CLI-Based Task Manager Python Code

Below is the complete, documented Python script for the Task Manager. It supports adding, listing, completing, and deleting tasks, with persistent JSON storage.

```python
#!/usr/bin/env python3
"""
CLI Task Manager
A command-line interface application for managing daily tasks.
Features persistent storage using JSON, task status toggling, and clean list presentation.
"""

import os
import json
import sys
from datetime import datetime

# File where tasks will be persisted
TASKS_FILE = "tasks.json"

def load_tasks():
    """Load tasks from the JSON database file. Returns a list of dicts."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Error: The task database file is corrupted. Starting with an empty list.")
        return []
    except Exception as e:
        print(f"Error loading tasks: {e}")
        return []

def save_tasks(tasks):
    """Persist the task list to the JSON database file."""
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving tasks: {e}")

def add_task(title):
    """Add a new task with a default status of incomplete."""
    if not title.strip():
        print("Error: Task title cannot be empty.")
        return
    tasks = load_tasks()
    new_task = {
        "id": len(tasks) + 1,
        "title": title.strip(),
        "completed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    tasks.append(new_task)
    save_tasks(tasks)
    print(f"Task '{title}' added successfully (ID: {new_task['id']}).")

def list_tasks():
    """Display all tasks in a clean tabular format."""
    tasks = load_tasks()
    if not tasks:
        print("No tasks found. Use 'add <title>' to create one.")
        return
    
    print("\n" + "="*60)
    print(f"{'ID':<5} | {'Status':<10} | {'Task Title':<30} | {'Created At'}")
    print("="*60)
    for task in tasks:
        status = "✅ Done" if task["completed"] else "❌ Pending"
        print(f"{task['id']:<5} | {status:<10} | {task['title']:<30} | {task['created_at']}")
    print("="*60 + "\n")

def complete_task(task_id):
    """Mark a specific task as completed."""
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            save_tasks(tasks)
            print(f"Task ID {task_id} marked as completed.")
            return
    print(f"Error: Task with ID {task_id} not found.")

def delete_task(task_id):
    """Delete a task and re-index the remaining task IDs."""
    tasks = load_tasks()
    initial_length = len(tasks)
    tasks = [task for task in tasks if task["id"] != task_id]
    
    if len(tasks) == initial_length:
        print(f"Error: Task with ID {task_id} not found.")
        return
        
    # Re-index remaining tasks
    for index, task in enumerate(tasks, start=1):
        task["id"] = index
        
    save_tasks(tasks)
    print(f"Task ID {task_id} deleted successfully.")

def print_help():
    """Print the usage guide."""
    print("""
Usage:
  python task_manager.py add "[title]"  - Add a new task
  python task_manager.py list           - View all tasks
  python task_manager.py complete [id]  - Complete a task by ID
  python task_manager.py delete [id]    - Delete a task by ID
  python task_manager.py help           - Show this help menu
""")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "add":
        if len(sys.argv) < 3:
            print("Error: Missing task title.")
            sys.exit(1)
        title = " ".join(sys.argv[2:])
        add_task(title)
    elif command == "list":
        list_tasks()
    elif command == "complete":
        if len(sys.argv) < 3:
            print("Error: Missing task ID.")
            sys.exit(1)
        try:
            task_id = int(sys.argv[2])
            complete_task(task_id)
        except ValueError:
            print("Error: Task ID must be a number.")
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Missing task ID.")
            sys.exit(1)
        try:
            task_id = int(sys.argv[2])
            delete_task(task_id)
        except ValueError:
            print("Error: Task ID must be a number.")
    elif command in ("help", "--help", "-h"):
        print_help()
    else:
        print(f"Unknown command: '{command}'")
        print_help()

if __name__ == "__main__":
    main()
```

---

## 🔒 Part 2: Security Checklist for Python Terminal Applications

CLI and terminal-based applications often execute with local system privileges, making them appealing targets if input validation or environment checks are neglected. Follow this checklist to secure your Python CLI apps:

### 1. Input Sanitization & Type Constraints
- [ ] **Type casting:** Always cast string inputs to expected types (e.g. integer IDs) using `try/except ValueError` block wrappers.
- [ ] **Avoid raw sql queries:** Use parameterized inputs if writing to sqlite databases.
- [ ] **Shell command validation:** Strip dangerous shell chars (`;`, `&`, `|`, `` ` ``) if user inputs are printed or utilized in logs.

### 2. File & Path Safety
- [ ] **Prevent Path Traversal:** Resolve all file paths to absolute paths using `os.path.abspath()` and confirm they reside inside the intended workspace directory.
- [ ] **Restrict Permissions:** Ensure persisted JSON/database files are saved with restricted filesystem permissions (`chmod 600` or equivalent) to prevent external local users from reading or writing task files.
- [ ] **Safe directory creation:** Use `os.makedirs(..., exist_ok=True)` and avoid shell expansion shortcuts (`~/` or `$HOME`) unless safely resolved.

### 3. Safe Subprocess Execution
- [ ] **Avoid `shell=True`:** Never run commands with `subprocess.Popen(..., shell=True)` using unvalidated user input, as it allows arbitrary bash injection.
- [ ] **Use lists for arguments:** Pass command arguments as a list (e.g., `["ls", "-l", path]`) rather than concatenating strings.
- [ ] **Specify explicit PATH environment:** Restrict or explicitly set executable paths to prevent execution of malicious binaries placed in user-writable paths.

### 4. Credential & Environment Isolation
- [ ] **No Hardcoded Tokens:** Never embed API keys, email credentials, or security tokens inside your CLI source code.
- [ ] **Use `.env` files:** Load credentials from local `.env` configuration files that are explicitly ignored in your `.gitignore`.
- [ ] **Secure Input Masking:** Use Python's built-in `getpass` library instead of `input()` when requesting user passwords in the console so typing is hidden.
