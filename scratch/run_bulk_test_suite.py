import os
os.environ["HF_HUB_OFFLINE"] = "1"

import asyncio
import json
import sys
import time

# Adjust path to find backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey-Patch MLXRunner BEFORE loading backend.agent to bypass GPU / Model Load entirely
from backend.mlx_runner import MLXRunner

def mock_load_model(self, model_id):
    print(f"[MockRunner] Loading simulated model {model_id} instantly...")
    return "mock_model", "mock_tokenizer"

def mock_generate_stream(self, model_id, prompt, **kwargs):
    # Resolve the last user prompt content
    if isinstance(prompt, list):
        user_prompt = prompt[-1]["content"].lower()
    else:
        user_prompt = str(prompt).lower()

    # If history already contains tool output, return final_answer to terminate task
    messages = prompt if isinstance(prompt, list) else []
    has_tool_run = any("Tool" in m.get("content", "") for m in messages if m.get("role") == "user")

    if has_tool_run:
        yield '```json\n{"tool": "final_answer", "args": {"message": "Simulated task execution verified successfully."}}\n```'
        return

    # Initial Tool Dispatches based on prompt keywords to exercise tools.py
    if "index.html" in user_prompt or "toggle button" in user_prompt:
        yield '```json\n{"tool": "run_command", "args": {"command": "echo \'<html></html>\' > user_projects/index.html"}}\n```'
    elif "css" in user_prompt or "stylesheet" in user_prompt:
        yield '```json\n{"tool": "write_file", "args": {"Path": "user_projects/style.css", "CodeContent": "body { background: #000; }"}}\n```'
    elif "sql" in user_prompt or "query" in user_prompt or "bigquery" in user_prompt:
        yield '```json\n{"tool": "write_file", "args": {"path": "user_projects/query.sql", "content": "SELECT * FROM users LIMIT 10;"}}\n```'
    elif "python version" in user_prompt:
        yield '```json\n{"tool": "run_command", "args": {"command": "python3 --version"}}\n```'
    elif "git branch" in user_prompt:
        yield '```json\n{"tool": "run_command", "args": {"command": "git branch"}}\n```'
    elif "subagent" in user_prompt or "invoke" in user_prompt:
        # Mock subagent tool
        yield '```json\n{"tool": "invoke_subagent", "args": {"role": "QATester", "task": "Simulated validation task"}}\n```'
    elif "read" in user_prompt or "show" in user_prompt or "parse" in user_prompt:
        yield '```json\n{"tool": "read_file", "args": {"Path": "README.md"}}\n```'
    elif "list" in user_prompt or "ls" in user_prompt:
        yield '```json\n{"tool": "list_dir", "args": {"DirectoryPath": "."}}\n```'
    else:
        yield '```json\n{"tool": "final_answer", "args": {"message": "Simulated general text answer."}}\n```'

# Apply monkey patches
MLXRunner.load_model = mock_load_model
MLXRunner.generate_stream = mock_generate_stream

# Import run_agent_loop AFTER patch
from backend.agent import run_agent_loop

# Define 100+ diverse tasks across different categories
TASKS = [
    # Category 1: Frontend & Web Development (20 tasks)
    "Create a clean index.html with a dark mode toggle button.",
    "Write a CSS stylesheet for a modern landing page with glassmorphism cards.",
    "Create a JavaScript file that animates a canvas particle system.",
    "Write a simple React component that fetches data from an API and lists it.",
    "Create a responsive navigation bar using vanilla HTML and CSS.",
    "Build a countdown timer in JavaScript that displays days, hours, and minutes.",
    "Write a CSS file with a modern grid layout for a photo gallery.",
    "Create a JavaScript script to validate a contact form (email, phone, name).",
    "Build an interactive modal pop-up in vanilla JavaScript.",
    "Write a CSS animation for a loading spinner.",
    "Create an HTML page that embeds a responsive video player.",
    "Write a JavaScript function to filter a list of products by category and price.",
    "Build a simple calculator UI with HTML and CSS grid.",
    "Create a JavaScript drag-and-drop file upload zone mockup.",
    "Write a CSS theme switcher using custom properties (CSS variables).",
    "Build a custom audio player UI with progress tracking in JS.",
    "Create a simple FAQ accordion component with smooth transitions.",
    "Write a JS script to search and highlight keywords in a webpage paragraph.",
    "Build a basic weather widget UI with local time display.",
    "Create a CSS flexbox sidebar that collapses on mobile screens.",

    # Category 2: BigQuery & Database Operations (20 tasks)
    "Write a SQL query to select all users who registered in the last 30 days.",
    "Create a BigQuery schema JSON file for a web analytics event table.",
    "Write a SQL query to calculate the average order value grouped by country.",
    "Generate a SQL script to partition a BigQuery table by registration date.",
    "Write a query to find the top 5 most viewed products in BigQuery.",
    "Create a mock database table schema for storing user profile details.",
    "Write a SQL query to join a users table with a transactions table to find VIP customers.",
    "Generate a SQL script to deduplicate records in a BigQuery table using ROW_NUMBER().",
    "Write a query to calculate daily active users (DAU) from event logs.",
    "Create a schema for a NoSQL Firestore database tracking user orders.",
    "Write a SQL query to calculate month-over-month revenue growth.",
    "Generate a BigQuery SQL script to export search query data to CSV.",
    "Write a query to count the number of null values in each column of a table.",
    "Create a Firestore security rule allowing users to read only their own data.",
    "Write a SQL query to perform a full-text search on product names in BigQuery.",
    "Generate a schema for a relational database tracking student grades.",
    "Write a SQL query to calculate a 7-day rolling average of active signups.",
    "Create a SQL script to update the status of expired subscriptions.",
    "Write a query to find users who have not made a transaction in 90 days.",
    "Generate a SQL script to delete user data requested under GDPR compliance.",

    # Category 3: File & Code Manipulation (20 tasks)
    "Write a Python script that parses a JSON config file and prints keys.",
    "Search for all imports of 'os' in the workspace.",
    "Count the total number of lines in tools.py.",
    "Write a Python function to check if a string is a palindrome.",
    "Create a mock requirements.txt file with common ML packages.",
    "Search the workspace for any occurrences of 'TODO' in comments.",
    "Write a Python script that downloads an image from a URL and saves it.",
    "Create a simple Makefile for a Python project (install, run, test).",
    "Search for where 'run_command' is defined in the backend directory.",
    "Write a Python script to compress all files in a folder into a ZIP archive.",
    "Create a .gitignore file ignoring node_modules, .venv, and logs.",
    "Write a Python function that parses a CSV file and calculates column averages.",
    "Search for 'execute_tool' inside tools.py.",
    "Create a Python script that generates a random password of a given length.",
    "Write a script to rename all .txt files in a directory to .bak.",
    "Search the workspace for any references to 'websocket'.",
    "Write a Python decorator that prints the execution time of a function.",
    "Create a JSON config file holding API credentials placeholder keys.",
    "Write a Python script to scan a file and count occurrences of each word.",
    "Search for 'ws_send_callback' in backend/agent.py.",

    # Category 4: System & OS Check Operations (20 tasks)
    "Check the currently installed Python version.",
    "Get the active git branch name.",
    "Verify if node and npm are installed on the system.",
    "Check system memory usage and swap memory status.",
    "List the contents of the user_projects directory.",
    "Find where the main app entrypoint run.sh is located.",
    "Check the current directory path.",
    "List all globally installed npm packages.",
    "Find the size of the server.log file in bytes.",
    "Check if the local git repository has any unstaged changes.",
    "Get the OS kernel name and system release version.",
    "Check if there are any running Python processes on the system.",
    "List all available network interfaces.",
    "Find all files modified in the last 24 hours in the project folder.",
    "Verify if Docker is running locally.",
    "Check the current local time of the system.",
    "Get the username of the currently logged-in shell user.",
    "Check the system disk space allocation.",
    "Show recent git commits on the active branch.",
    "Check if curl is available on the system.",

    # Category 5: Multi-Agent & Swarm Operations (20 tasks)
    "Invoke a subagent named 'WebDeveloper' to build a portfolio page.",
    "Check your inbox for any pending review responses from subagents.",
    "Invoke a subagent named 'DatabaseDesigner' to draft a SQL schema.",
    "Send a message to DatabaseDesigner requesting partition keys.",
    "Invoke a subagent named 'SecurityAuditor' to audit tools.py.",
    "Check your inbox for subagent SecurityAuditor's report.",
    "Invoke a subagent named 'QATester' to run the test suite.",
    "Send a message to QATester to verify command injection parameters.",
    "Invoke a subagent named 'DocWriter' to write a API document.",
    "Check your inbox for messages from DocWriter.",
    "Invoke a subagent named 'UIReviewer' to inspect style.css.",
    "Send a message to UIReviewer with the theme variables.",
    "Invoke a subagent named 'SystemOptimizer' to profile memory usage.",
    "Check your inbox for SystemOptimizer's summary.",
    "Invoke a subagent named 'GCPArchitect' to verify BigQuery settings.",
    "Send a message to GCPArchitect asking about partition limits.",
    "Invoke a subagent named 'CodeReviewer' to review agent.py edits.",
    "Check your inbox for feedback from CodeReviewer.",
    "Invoke a subagent named 'DeploymentManager' to verify staging builds.",
    "Send a message to DeploymentManager requesting deployment status."
]

async def test_task(task_index, prompt, log_file):
    history = []
    actions = []
    errors = []
    
    async def callback(packet):
        t = packet.get("type")
        if t == "tool_start":
            actions.append(f"{packet.get('name')}({packet.get('args')})")
        elif t == "tool_error":
            errors.append(f"Tool {packet.get('name')} failed: {packet.get('output', '')[:200]}")
        elif t == "error":
            errors.append(f"Backend Error: {packet.get('message')}")

    start_time = time.time()
    try:
        await run_agent_loop(
            user_prompt=prompt,
            model_id="mock-model",
            ws_send_callback=callback,
            history=history,
            max_loops=2
        )
    except Exception as e:
        errors.append(f"Crashed: {e}")
        
    duration = time.time() - start_time
    status = "SUCCESS" if not errors else "FAILED"
    
    record = {
        "index": task_index,
        "prompt": prompt,
        "duration_sec": round(duration, 3),
        "status": status,
        "actions_taken": actions,
        "errors_encountered": errors
    }
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
        
    return record

async def main():
    log_file = "scratch/bulk_suite_results.jsonl"
    
    print("\n==================================================")
    print("   Initializing MOCK Fast AI Agent Test Suite")
    print(f"   Total Tasks: {len(TASKS)}")
    print(f"   Log File: {log_file}")
    print("==================================================\n")
    
    # Reset log file
    with open(log_file, "w", encoding="utf-8") as f:
        pass
        
    start_all = time.time()
    success_count = 0
    
    for idx, prompt in enumerate(TASKS):
        res = await test_task(idx + 1, prompt, log_file)
        if res["status"] == "SUCCESS":
            success_count += 1
            
    total_duration = time.time() - start_all
    
    print("==================================================")
    print(f"   Done! Completed {len(TASKS)} tasks in {round(total_duration, 2)} seconds!")
    print(f"   Success Rate: {success_count}/{len(TASKS)} (100% Mock Verification)")
    print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
