import os
import subprocess
import pathlib
import json
import smtplib
import imaplib
import email
import shutil
import threading
import asyncio
import time
from email.header import decode_header
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
import difflib

PENDING_DIFFS = []

active_subprocesses = []
active_subprocesses_lock = threading.Lock()

def run_subprocess_managed(command: str, shell: bool = True, cwd: str = None, timeout: float = None, env: dict = None) -> subprocess.CompletedProcess:
    if env is None:
        env = os.environ.copy()
        # Explicitly inject common macOS paths since /bin/sh doesn't source .zshrc
        current_path = env.get("PATH", "")
        for p in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if p not in current_path:
                current_path = f"{p}:{current_path}"
        env["PATH"] = current_path
        
    proc = subprocess.Popen(
        command,
        shell=shell,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    with active_subprocesses_lock:
        active_subprocesses.append(proc)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(
            args=command,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr
        )
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        proc.communicate()
        raise
    finally:
        with active_subprocesses_lock:
            if proc in active_subprocesses:
                active_subprocesses.remove(proc)

def kill_active_subprocesses():
    with active_subprocesses_lock:
        for proc in active_subprocesses:
            try:
                proc.kill()
            except Exception:
                pass
        active_subprocesses.clear()

# Default workspace directory
workspace_dir = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent"

def set_workspace(new_dir: str):
    global workspace_dir
    if new_dir:
        abs_path = os.path.abspath(new_dir)
        os.makedirs(abs_path, exist_ok=True)
        workspace_dir = abs_path
        print(f"[Tools] Workspace set to: {workspace_dir}")

def get_workspace() -> str:
    return workspace_dir

def resolve_path(relative_path: str) -> str:
    if os.path.isabs(relative_path):
        return relative_path
    base = pathlib.Path(workspace_dir).resolve()
    target = (base / relative_path).resolve()
    return str(target)

def run_command(command: str) -> str:
    try:
        print(f"[Tool: run_command] Executing: {command} in Cwd: {workspace_dir}")
        result = run_subprocess_managed(
            command,
            shell=True,
            cwd=workspace_dir,
            timeout=120
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        if not output:
            output = "Command completed with no output."
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def read_file(relative_path: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
    try:
        relative_path = str(relative_path)
        file_path = resolve_path(relative_path)
        if not os.path.exists(file_path):
            return f"Error: File '{relative_path}' does not exist at path: {file_path}"
        if os.path.isdir(file_path):
            return f"Error: '{relative_path}' is a directory, not a file."
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        start = max(1, start_line)
        end = min(total_lines, end_line) if end_line is not None else total_lines
        
        if start > total_lines:
            return f"Error: Start line {start} exceeds file length {total_lines}."
            
        selected_lines = lines[start - 1:end]
        content = "".join(selected_lines)
        return f"--- Reading '{relative_path}' (Lines {start}-{end} of {total_lines}) ---\n" + content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def search_knowledge_bank(query: str) -> str:
    try:
        import math
        from collections import Counter
        import re
        
        kb_dir = resolve_path("knowledge_bank")
        if not os.path.exists(kb_dir):
            return "Knowledge bank directory does not exist."
            
        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return "Invalid query."
            
        chunks = []
        for filename in os.listdir(kb_dir):
            if not filename.endswith(".md"): continue
            filepath = os.path.join(kb_dir, filename)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            
            # Split by double newline to get paragraphs/sections
            paragraphs = text.split("\n\n")
            for i, p in enumerate(paragraphs):
                if len(p.strip()) < 30: continue
                
                p_lower = p.lower()
                # Simple keyword overlap score
                score = sum(1 for w in query_words if w in p_lower)
                
                if score > 0:
                    chunks.append((score, filename, p.strip()))
                    
        if not chunks:
            return f"No results found in knowledge bank for: {query}"
            
        # Sort descending by score
        chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Deduplicate and take top 3
        top_chunks = []
        seen = set()
        for score, fname, content in chunks:
            if content not in seen:
                seen.add(content)
                top_chunks.append((score, fname, content))
            if len(top_chunks) >= 3:
                break
                
        res = f"--- Top 3 Knowledge Bank Results for '{query}' ---\n\n"
        for score, fname, content in top_chunks:
            res += f"[Source: {fname} (Match Score: {score})]\n{content}\n\n"
        return res.strip()
    except Exception as e:
        return f"Error searching knowledge bank: {e}"

def write_file(relative_path: str, content: str) -> str:
    try:
        # Self-preservation firewall
        restricted = ['frontend', 'backend', 'models', 'knowledge_bank', 'app.py', 'run.sh']
        parts = pathlib.Path(relative_path).parts
        if parts and parts[0] in restricted:
            return f"Error: Attempted to overwrite core agent file '{relative_path}'. Self-preservation rule engaged. Please place user projects in a new directory (e.g., 'user_projects/')."
            
        file_path = resolve_path(relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create a backup if the file already exists
        old_content = ""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                old_content = f.read()
            backup_path = file_path + ".bak"
            shutil.copy2(file_path, backup_path)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Generate Diff
        diff_lines = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=relative_path,
            tofile=relative_path
        ))
        diff_str = "".join(diff_lines)
        if diff_str:
            PENDING_DIFFS.append({"file": relative_path, "diff": diff_str})

        return f"Success: File '{relative_path}' written successfully ({len(content)} chars). A backup was saved as '{relative_path}.bak'."
    except Exception as e:
        return f"Error writing file: {str(e)}"

def replace_file_content(relative_path: str, search_content: str, replacement_content: str) -> str:
    try:
        # Self-preservation firewall
        restricted = ['frontend', 'backend', 'models', 'knowledge_bank', 'app.py', 'run.sh']
        parts = pathlib.Path(relative_path).parts
        if parts and parts[0] in restricted:
            return f"Error: Attempted to edit core agent file '{relative_path}'. Self-preservation rule engaged. Please place user projects in a new directory (e.g., 'user_projects/')."
            
        file_path = resolve_path(relative_path)
        if not os.path.exists(file_path):
            return f"Error: File '{relative_path}' does not exist."
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if search_content not in content:
            return f"Error: Could not find exact search text block in '{relative_path}'. Please make sure spacing/newlines match exactly."
            
        count = content.count(search_content)
        if count > 1:
            return f"Error: Search text occurs {count} times in '{relative_path}'. Provide a more unique block to avoid ambiguity."
            
        new_content = content.replace(search_content, replacement_content)
        
        # Create a backup before editing
        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # Generate Diff
        diff_lines = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=relative_path,
            tofile=relative_path
        ))
        diff_str = "".join(diff_lines)
        if diff_str:
            PENDING_DIFFS.append({"file": relative_path, "diff": diff_str})
            
        return f"Success: Replaced 1 block in '{relative_path}'. A backup was saved as '{relative_path}.bak'."
    except Exception as e:
        return f"Error editing file: {str(e)}"

def edit_lines(relative_path: str, start_line: int, end_line: int, new_content: str) -> str:
    try:
        # Self-preservation firewall
        restricted = ['frontend', 'backend', 'models', 'knowledge_bank', 'app.py', 'run.sh']
        parts = pathlib.Path(relative_path).parts
        if parts and parts[0] in restricted:
            return f"Error: Attempted to edit core agent file '{relative_path}'. Self-preservation rule engaged. Please place user projects in a new directory (e.g., 'user_projects/')."
            
        file_path = resolve_path(relative_path)
        if not os.path.exists(file_path):
            return f"Error: File '{relative_path}' does not exist."
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return f"Error: Invalid line range {start_line}-{end_line}. File has {len(lines)} lines."
            
        # Create a backup before editing
        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)
        
        # Replace the lines (0-indexed for python arrays)
        # Ensure new_content ends with a newline if it doesn't
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'
            
        lines[start_line - 1 : end_line] = [new_content]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        return f"Success: Replaced lines {start_line} to {end_line} in '{relative_path}'. A backup was saved as '{relative_path}.bak'."
    except Exception as e:
        return f"Error editing lines: {str(e)}"


def list_dir(relative_path: str = ".") -> str:
    try:
        target_dir = resolve_path(relative_path)
        if not os.path.exists(target_dir):
            return f"Error: Directory '{relative_path}' does not exist."
        if not os.path.isdir(target_dir):
            return f"Error: '{relative_path}' is a file, not a directory."
            
        items = os.listdir(target_dir)
        if not items:
            return f"Directory '{relative_path}' is empty."
            
        dirs = []
        files = []
        for item in items:
            full_path = os.path.join(target_dir, item)
            rel = os.path.relpath(full_path, workspace_dir)
            if os.path.isdir(full_path):
                dirs.append(f"[DIR]  {rel}/")
            else:
                size = os.path.getsize(full_path)
                files.append(f"[FILE] {rel} ({size} bytes)")
                
        output = f"--- Listing '{relative_path}' ---\n"
        output += "\n".join(sorted(dirs) + sorted(files))
        return output
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def web_search(query: str) -> str:
    try:
        print(f"[Tool: web_search] Querying DuckDuckGo: '{query}'")
        from ddgs import DDGS
        with DDGS(timeout=10) as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return f"No search results found for query: '{query}'"
        
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. Title: {r.get('title')}\n   URL: {r.get('href')}\n   Snippet: {r.get('body')}\n")
        return "\n".join(formatted)
    except Exception as e:
        return f"Error searching the web: {str(e)}"

def web_fetch(url: str) -> str:
    try:
        print(f"[Tool: web_fetch] Fetching URL: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(url, headers=headers)
            
        if response.status_code != 200:
            return f"Error: HTTP status code {response.status_code} while fetching {url}."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
            
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        max_chars = 12000
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + f"\n\n... [Content truncated, total length: {len(clean_text)} characters] ..."
            
        return clean_text
    except Exception as e:
        return f"Error fetching web page: {str(e)}"

def get_secret(key: str) -> str:
    """Read a secret from the local secrets.json vault."""
    secrets_path = resolve_path("secrets.json")
    if not os.path.exists(secrets_path):
        return f"Secret '{key}' not found. The secrets vault does not exist yet."
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if key in data:
            # We obscure it slightly in the tool return so it doesn't get fully logged in raw text if not needed
            val = data[key]
            masked = val[:4] + "***" + val[-4:] if len(val) > 8 else "***"
            return f"Secret '{key}' successfully loaded. (Value: {masked})"
        return f"Secret '{key}' not found in the vault."
    except Exception as e:
        return f"Error reading secrets: {str(e)}"

def set_secret(key: str, value: str) -> str:
    """Save a secret to the local secrets.json vault."""
    secrets_path = resolve_path("secrets.json")
    try:
        data = {}
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[key] = value
        with open(secrets_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return f"Success: Secret '{key}' saved securely to the vault."
    except Exception as e:
        return f"Error saving secret: {str(e)}"

def get_gmail_credentials():
    config_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/gmail_config.json"
    if not os.path.exists(config_path):
        raise Exception("Gmail credentials not configured. Please use the sidebar in the UI to set up your email and App Password.")
    with open(config_path, "r") as f:
        data = json.load(f)
    email_addr = data.get("email")
    password = data.get("app_password")
    if not email_addr or not password:
        raise Exception("Incomplete Gmail credentials in config.")
    return email_addr, password

def gmail_list_emails(max_emails: int = 5, folder: str = "INBOX") -> str:
    try:
        sender_email, password = get_gmail_credentials()
        print(f"[Gmail] Connecting to fetch {max_emails} emails from {folder}...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=15)
        mail.login(sender_email, password)
        mail.select(folder)
        status, search_data = mail.search(None, "ALL")
        if status != 'OK' or not search_data[0]:
            return "No emails found in this folder."
        email_ids = search_data[0].split()
        latest_ids = email_ids[-max_emails:]
        latest_ids.reverse()
        output_lines = []
        output_lines.append(f"--- Recent Emails in '{folder}' (Showing top {len(latest_ids)}) ---")
        for eid in latest_ids:
            status, data = mail.fetch(eid, '(RFC822.HEADER)')
            if status != 'OK': continue
            msg = email.message_from_bytes(data[0][1])
            subject = "No Subject"
            if msg["Subject"]:
                decoded_list = decode_header(msg["Subject"])
                subj_parts = []
                for part, encoding in decoded_list:
                    if isinstance(part, bytes):
                        subj_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
                    else:
                        subj_parts.append(str(part))
                subject = "".join(subj_parts)
            from_sender = msg["From"] or "Unknown Sender"
            date = msg["Date"] or "Unknown Date"
            eid_str = eid.decode('utf-8')
            output_lines.append(f"Email ID: {eid_str}\nFrom: {from_sender}\nDate: {date}\nSubject: {subject}\n")
        mail.logout()
        return "\n".join(output_lines)
    except Exception as e:
        return f"Error listing emails: {str(e)}"

def gmail_read_email(email_id: str) -> str:
    try:
        sender_email, password = get_gmail_credentials()
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=15)
        mail.login(sender_email, password)
        mail.select("INBOX")
        status, data = mail.fetch(email_id.encode('utf-8'), '(RFC822)')
        if status != 'OK':
            return f"Error fetching email {email_id}."
        msg = email.message_from_bytes(data[0][1])
        subject = "No Subject"
        if msg["Subject"]:
            decoded_list = decode_header(msg["Subject"])
            subj_parts = []
            for part, encoding in decoded_list:
                if isinstance(part, bytes):
                    subj_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
                else:
                    subj_parts.append(str(part))
            subject = "".join(subj_parts)
        from_sender = msg["From"] or "Unknown Sender"
        date = msg["Date"] or "Unknown Date"
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body_bytes = part.get_payload(decode=True)
                    if body_bytes:
                        body += body_bytes.decode(part.get_content_charset() or 'utf-8', errors='ignore')
        else:
            body_bytes = msg.get_payload(decode=True)
            if body_bytes:
                body = body_bytes.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        mail.logout()
        header = f"=== Email ID: {email_id} ===\nFrom: {from_sender}\nDate: {date}\nSubject: {subject}\n=========================\n\n"
        max_chars = 10000
        if len(body) > max_chars:
            body = body[:max_chars] + "\n\n... [Email body truncated, too long] ..."
        return header + body
    except Exception as e:
        return f"Error reading email ID {email_id}: {str(e)}"

def gmail_delete_email(email_id: str) -> str:
    try:
        sender_email, password = get_gmail_credentials()
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=15)
        mail.login(sender_email, password)
        mail.select("INBOX")
        status, response = mail.store(email_id.encode('utf-8'), '+FLAGS', '\\Deleted')
        if status != 'OK':
            return f"Error marking email {email_id} as deleted."
        mail.expunge()
        mail.logout()
        return f"Success: Email ID {email_id} deleted permanently."
    except Exception as e:
        return f"Error deleting email: {str(e)}"

def grep_search(query: str, search_path: str = ".", is_regex: bool = False, case_insensitive: bool = True, match_per_line: bool = True) -> str:
    try:
        target_path = resolve_path(search_path)
        cmd = ["grep", "-R"]
        if case_insensitive: cmd.append("-i")
        if match_per_line: cmd.append("-n")
        else: cmd.append("-l")
        if not is_regex: cmd.append("-F")
        else: cmd.append("-E")
        # Exclude common noisy directories and massive log files
        cmd.extend(["--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=.venv", "--exclude-dir=__pycache__"])
        cmd.extend(["--exclude=*.json", "--exclude=*.log", "--exclude=project_overview.md"])
        cmd.extend([query, target_path])
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            # Truncate each line to prevent massive minified JSON lines from flooding the context
            truncated_lines = [line[:200] + ("..." if len(line) > 200 else "") for line in lines]
            if len(truncated_lines) > 50:
                return f"--- Search Results for '{query}' ---\n" + "\n".join(truncated_lines[:50]) + f"\n... (and {len(truncated_lines) - 50} more lines omitted)"
            return f"--- Search Results for '{query}' ---\n" + "\n".join(truncated_lines)
        elif result.returncode == 1:
            return f"No matches found for '{query}'."
        else:
            return f"Search Error:\n{result.stderr}"
    except Exception as e:
        return f"Error executing search: {str(e)}"

# Dangerous shell command patterns that should NEVER be passed as a "task"
DANGEROUS_PATTERNS = ["kill ", "rm -rf", "sudo ", "mkfs", "dd if=", ":(){ :|:& };:", "> /dev/", "shutdown", "reboot", "passwd"]

queue_lock = threading.Lock()

# Global GPU inference lock to serialize local model loads and executions
gpu_inference_lock = threading.Lock()


def set_subagent_status(role: str, status: str):
    """Write subagent status (e.g. RUNNING, COMPLETED, CRASHED) to subagent_status.json."""
    status_path = resolve_path("subagent_status.json")
    try:
        with queue_lock:
            data = {}
            if os.path.exists(status_path):
                try:
                    with open(status_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except:
                    data = {}
            data[role] = {
                "status": status,
                "timestamp": time.time()
            }
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    except:
        pass


def get_subagents_summary() -> str:
    """Return a readable text summary of all active subagents and their current running statuses."""
    status_path = resolve_path("subagent_status.json")
    try:
        if not os.path.exists(status_path):
            return "No active subagents."
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return "No active subagents."
        
        lines = []
        for role, info in data.items():
            status = info.get("status", "UNKNOWN")
            if status == "RUNNING":
                elapsed = int(time.time() - info.get("timestamp", time.time()))
                lines.append(f"- Subagent '{role}': {status} (running for {elapsed}s)")
            else:
                lines.append(f"- Subagent '{role}': {status}")
        return "\n".join(lines)
    except:
        return "No active subagents."


def _subagent_thread_runner(role: str, task: str):
    """Background thread function that runs a subagent.
    Uses free online HF serverless models first to run in parallel without GPU thrashing.
    Falls back to sequential local model execution (via gpu_inference_lock) if offline/limited.
    Results are written back to message_queue.json so the main agent can read them."""
    set_subagent_status(role, "RUNNING")
    try:
        subagent_result = {"text": ""}
        success = False
        
        # 1. Try cloud API integration first if we have keys or a cloud model is selected
        try:
            from cloud_runner import is_cloud_model, stream_cloud
            # Read active model ID from server settings if possible
            active_model_id = "groq/llama-3.3-70b"  # Default to a high-quality cloud model
            
            # Look up if a custom model has been selected
            try:
                state_path = resolve_path("chat_sessions.json")
                if os.path.exists(state_path):
                    with open(state_path, "r") as f:
                        session_data = json.load(f)
                    # chat_sessions.json is structured as {"sessions": [...]}
                    sessions = session_data.get("sessions", [])
                    if sessions:
                        # Inspect key items
                        last_session = sessions[-1]
                        # Look for active model inside history or defaults
                        active_model_id = last_session.get("model_id", active_model_id)
            except:
                pass
                
            if is_cloud_model(active_model_id):
                # Teach the subagent how to use tools to modify files in the user's workspace
                system_prompt = (
                    f"You are an expert AI Subagent role-playing as: {role}. Assist the main agent.\n"
                    "You have direct access to the user's local filesystem and terminal via tools.\n"
                    "To use a tool, you MUST output a standard JSON block wrapped in a markdown ```json code block. After outputting the tool call, STOP generating immediately.\n\n"
                    "Available tools:\n"
                    "- write_file(path, content): Create a new file with the specified content.\n"
                    "- run_command(command): Run a shell command in the workspace directory.\n\n"
                    "Example tool call format:\n"
                    "```json\n"
                    "{\n"
                    "  \"tool\": \"write_file\",\n"
                    "  \"args\": {\n"
                    "    \"path\": \"user_projects/hello.py\",\n"
                    "    \"content\": \"print('hello')\"\n"
                    "  }\n"
                    "}\n"
                    "```\n"
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": task}
                ]
                
                print(f"[Subagent] '{role}' running online via cloud model '{active_model_id}'...")
                
                # Run the agent-loop inside the subagent thread to parse and execute its tools
                loop_count = 0
                max_subagent_loops = 5
                response_text = ""
                
                while loop_count < max_subagent_loops:
                    loop_count += 1
                    chunk_text = ""
                    for token_chunk in stream_cloud(active_model_id, messages, max_tokens=2048, temperature=0.2):
                        if "[ERROR]" in token_chunk or "[GROQ" in token_chunk:
                            raise ValueError(token_chunk)
                        chunk_text += token_chunk
                    
                    response_text += chunk_text
                    
                    # Parse tool call if present in accumulated text
                    from agent import extract_tool_call
                    tool_data = extract_tool_call(response_text)
                    if tool_data and "tool" in tool_data:
                        tname = tool_data["tool"]
                        targs = tool_data.get("args", {})
                        print(f"[Subagent Tool] '{role}' requested tool '{tname}' with args {targs}")
                        
                        # Translate subagent write_file calls to correct local write_file parameter keys
                        if tname == "write_file":
                            targs = {
                                "relative_path": targs.get("path", ""),
                                "content": targs.get("content", "")
                            }
                        elif tname == "run_command":
                            targs = {
                                "command": targs.get("command", "")
                            }
                            
                        # Execute the tool
                        try:
                            result_out = execute_tool(tname, targs)
                            print(f"[Subagent Tool Result] Done: {str(result_out)[:200]}")
                        except Exception as tool_err:
                            result_out = f"Error running tool: {tool_err}"
                            print(f"[Subagent Tool Result] Fail: {result_out}")
                            
                        messages.append({"role": "assistant", "content": chunk_text})
                        messages.append({"role": "user", "content": f"TOOL RESULT ({tname}):\n{result_out}"})
                        # Reset response text so we accumulate the next agent turn cleanly
                        response_text = ""
                    else:
                        # If no tool was called, this is the final conversational answer
                        break
                
                if response_text.strip():
                    subagent_result["text"] = response_text
                    success = True
                    print(f"[Subagent] '{role}' successfully processed online via '{active_model_id}'.")
        except Exception as api_err:
            import traceback
            traceback.print_exc()
            print(f"[Subagent] Cloud API execution failed for '{role}': {api_err}. Falling back to local MLX engine...")

        # 2. Local fallback using local MLX engine
        if not success:
            try:
                from agent import run_agent_loop
            except ImportError:
                from .agent import run_agent_loop

            async def subagent_callback(msg: Dict[str, Any]):
                """Capture the subagent's final_response."""
                if msg.get("type") == "final_response":
                    subagent_result["text"] = msg.get("text", "")

            # Acquire GPU lock so we don't reload/unload local models in parallel threads
            with gpu_inference_lock:
                print(f"[Subagent] '{role}' acquired GPU lock. Running local inference...")
                asyncio.run(run_agent_loop(
                    user_prompt=task,
                    model_id="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",  # Default local model for subagents
                    ws_send_callback=subagent_callback,
                    role=role
                ))

        # Write the result back to message_queue.json for the main agent
        queue_path = resolve_path("message_queue.json")
        with queue_lock:
            queue = {}
            if os.path.exists(queue_path):
                try:
                    with open(queue_path, "r") as f:
                        queue = json.load(f)
                except Exception:
                    queue = {}
            if "MainAgent" not in queue:
                queue["MainAgent"] = []
            queue["MainAgent"].append({
                "from": role,
                "message": f"Subagent '{role}' completed.\nResult: {subagent_result['text'][:2000]}"
            })
            with open(queue_path, "w") as f:
                json.dump(queue, f, indent=2)
        set_subagent_status(role, "COMPLETED")
        print(f"[Subagent] '{role}' finished successfully.")

    except Exception as e:
        # Crash in subagent must NOT kill the main agent
        print(f"[Subagent] '{role}' crashed: {e}")
        set_subagent_status(role, f"CRASHED: {str(e)[:50]}")
        try:
            queue_path = resolve_path("message_queue.json")
            with queue_lock:
                queue = {}
                if os.path.exists(queue_path):
                    try:
                        with open(queue_path, "r") as f:
                            queue = json.load(f)
                    except Exception:
                        queue = {}
                if "MainAgent" not in queue:
                    queue["MainAgent"] = []
                queue["MainAgent"].append({
                    "from": role,
                    "message": f"Subagent '{role}' crashed with error: {str(e)[:500]}"
                })
                with open(queue_path, "w") as f:
                    json.dump(queue, f, indent=2)
        except Exception:
            pass  # Last resort: don't propagate queue write failures


def invoke_subagent(role: str, task: str) -> str:
    # Safety guard: block raw shell commands masquerading as tasks
    task_lower = task.strip().lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in task_lower:
            return f"Error: Safety violation. The task '{task[:60]}...' looks like a dangerous shell command, not an AI task description. Use `run_command` for shell commands. The `invoke_subagent` tool spawns an AI agent, not a terminal."
    
    queue_path = resolve_path("message_queue.json")
    try:
        with queue_lock:
            queue = {}
            if os.path.exists(queue_path):
                try:
                    with open(queue_path, "r") as f:
                        queue = json.load(f)
                except Exception:
                    queue = {}
            if role not in queue:
                queue[role] = []
            queue[role].append({"from": "MainAgent", "message": task})
            with open(queue_path, "w") as f:
                json.dump(queue, f, indent=2)

        # Launch the subagent in a background thread so the main agent
        # can continue working while the subagent processes the task.
        thread = threading.Thread(
            target=_subagent_thread_runner,
            args=(role, task),
            daemon=True,
            name=f"subagent-{role}"
        )
        thread.start()
        print(f"[Subagent] Launched background thread for '{role}'")

        return f"Subagent '{role}' invoked with task: {task}. It is now running in the background. Use `check_inbox` with my_role='MainAgent' to get the result when ready."
    except Exception as e:
        return f"Error invoking subagent: {str(e)}"

def send_message(recipient_role: str, message: str) -> str:
    queue_path = resolve_path("message_queue.json")
    try:
        with queue_lock:
            queue = {}
            if os.path.exists(queue_path):
                try:
                    with open(queue_path, "r") as f:
                        queue = json.load(f)
                except Exception:
                    queue = {}
            if recipient_role not in queue:
                queue[recipient_role] = []
            queue[recipient_role].append({"message": message})
            with open(queue_path, "w") as f:
                json.dump(queue, f, indent=2)
        return f"Message sent to '{recipient_role}'."
    except Exception as e:
        return f"Error sending message: {str(e)}"

def check_inbox(my_role: str) -> str:
    queue_path = resolve_path("message_queue.json")
    try:
        with queue_lock:
            if os.path.exists(queue_path):
                try:
                    with open(queue_path, "r") as f:
                        queue = json.load(f)
                except Exception:
                    return "Inbox is empty (corrupted queue file reset)."
            else:
                return "Inbox is empty. The subagents are still working in the background. Do NOT keep calling check_inbox immediately. Instead, use the 'wait' tool to pause for 5-10 seconds, or perform other tasks."
            
            messages = queue.get(my_role, [])
            if not messages:
                return "Inbox is empty. The subagents are still working in the background. Do NOT keep calling check_inbox immediately. Instead, use the 'wait' tool to pause for 5-10 seconds, or perform other tasks."
            
            queue[my_role] = []
            with open(queue_path, "w") as f:
                json.dump(queue, f, indent=2)
            
        output = "--- Inbox Messages ---\n"
        for msg in messages:
            output += f"- {msg}\n"
        return output
    except Exception as e:
        return f"Error checking inbox: {str(e)}"


def wait(seconds: int) -> str:
    """Pause execution for a specified duration in seconds to let subagents finish or avoid hot-polling."""
    try:
        secs = int(seconds)
        time.sleep(secs)
        return f"Successfully paused execution for {secs} seconds."
    except Exception as e:
        return f"Error waiting: {str(e)}"



# ─────────────────────────────────────────────────────────────────────────────
# Code Execution Sandbox (Upgrade 5)
# Runs untrusted commands with:
# - 30-second timeout
# - Restricted PATH (only essential system binaries)
# - No network access (using macOS sandbox-exec if available)
# - Captured stdout + stderr
# ─────────────────────────────────────────────────────────────────────────────

# macOS sandbox profile that denies all network access
_SANDBOX_PROFILE = """(version 1)
(allow default)
(deny network*)
"""


def run_sandboxed(command: str) -> str:
    """Run an untrusted command in a restricted sandbox.
    
    Security measures:
    - 30-second hard timeout
    - Restricted PATH (only /usr/bin, /bin, /usr/local/bin)
    - No network access via macOS sandbox-exec (graceful fallback if unavailable)
    - Both stdout and stderr captured
    """
    try:
        print(f"[Tool: run_sandboxed] Executing in sandbox: {command}")

        # Restricted environment: limited PATH, no proxy/network env vars
        sandbox_env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": os.path.expanduser("~"),
            "LANG": "en_US.UTF-8",
        }

        # Try to use macOS sandbox-exec for network isolation
        # sandbox-exec is available on macOS and enforces kernel-level restrictions
        use_sandbox_exec = shutil.which("sandbox-exec") is not None

        if use_sandbox_exec:
            # Write temporary sandbox profile
            import tempfile
            profile_fd, profile_path = tempfile.mkstemp(suffix=".sb", prefix="mlx_sandbox_")
            try:
                with os.fdopen(profile_fd, "w") as pf:
                    pf.write(_SANDBOX_PROFILE)
                
                full_command = f'sandbox-exec -f "{profile_path}" /bin/bash -c {_shell_quote(command)}'
                result = run_subprocess_managed(
                    full_command,
                    shell=True,
                    cwd=workspace_dir,
                    timeout=30,
                    env=sandbox_env
                )
            finally:
                # Always clean up the temp profile
                try:
                    os.unlink(profile_path)
                except OSError:
                    pass
        else:
            # Fallback: run without sandbox-exec but still with restricted env and timeout
            print("[Tool: run_sandboxed] WARNING: sandbox-exec not available, running with restricted env only")
            result = run_subprocess_managed(
                command,
                shell=True,
                cwd=workspace_dir,
                timeout=30,
                env=sandbox_env
            )

        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        if not output.strip():
            output = "Command completed with no output."
        return output

    except subprocess.TimeoutExpired:
        return "Error: Sandboxed command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing sandboxed command: {str(e)}"


def _shell_quote(s: str) -> str:
    """Quote a string for safe shell inclusion."""
    return "'" + s.replace("'", "'\"'\"'") + "'"

TOOLS_MANIFEST = [
    {
        "name": "run_command",
        "description": "Execute a terminal/bash command inside the active workspace directory. Use this to compile code, run tests, install packages, check directories, or execute scripts.",
        "parameters": {"command": "The shell command string to execute."}
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from the workspace. Supports specifying lines to view.",
        "parameters": {"relative_path": "Path to the file relative to the workspace root.", "start_line": "Optional. The starting line number (1-indexed). Defaults to 1.", "end_line": "Optional. The ending line number (inclusive, 1-indexed)."}
    },
    {
        "name": "search_knowledge_bank",
        "description": "Ultra-fast local RAG tool. Instantly searches all Subagent Knowledge Bank Markdown files for a conceptual query and returns the top 3 most relevant paragraphs. ALWAYS use this first when asked a conceptual question.",
        "parameters": {"query": "The keyword or concept to search for."}
    },
    {
        "name": "write_file",
        "description": "Write a new file or completely overwrite an existing file with the provided content.",
        "parameters": {"relative_path": "Path to save the file, relative to the workspace root.", "content": "The full string content to write to the file."}
    },
    {
        "name": "replace_file_content",
        "description": "Make a targeted edit to a file by replacing a single unique block of text with a replacement block. Preferred over write_file for modifying existing files.",
        "parameters": {
            "relative_path": "Path to the file relative to the workspace root.",
            "search_content": "The exact block of text inside the file to replace.",
            "replacement_content": "The block of text to put in place of the search_content."
        }
    },
    {
        "name": "edit_lines",
        "description": "Make a targeted edit to a file by replacing a specific range of line numbers. Much more reliable than replace_file_content because it doesn't require matching exact text spacing.",
        "parameters": {
            "relative_path": "Path to the file relative to the workspace root.",
            "start_line": "The starting line number to replace (1-indexed).",
            "end_line": "The ending line number to replace (inclusive).",
            "new_content": "The new content to insert in place of the specified lines."
        }
    },
    {
        "name": "list_dir",
        "description": "List the contents of a directory in the workspace.",
        "parameters": {"relative_path": "Optional. The directory path to list, relative to the workspace root. Defaults to '.' (the root)."}
    },
    {
        "name": "web_search",
        "description": "Search DuckDuckGo for info. Useful for finding documentation, checking recent events, or searching code errors.",
        "parameters": {"query": "The search term or query string."}
    },
    {
        "name": "web_fetch",
        "description": "Fetch a webpage's raw text content. Useful for reading web articles, documentation pages, or GitHub code from search results.",
        "parameters": {"url": "The complete URL of the page to scrape."}
    },
    {
        "name": "gmail_list_emails",
        "description": "List recent emails from a Gmail folder.",
        "parameters": {"max_emails": "Number of emails to fetch (default 5).", "folder": "Folder name (default 'INBOX')."}
    },
    {
        "name": "gmail_read_email",
        "description": "Read the full text body of a specific email by ID.",
        "parameters": {"email_id": "The string ID of the email to retrieve and read."}
    },
    {
        "name": "gmail_delete_email",
        "description": "Delete a specific email from Gmail by its ID. Be very careful with this tool.",
        "parameters": {"email_id": "The string ID of the email to delete."}
    },
    {
        "name": "grep_search",
        "description": "Search for a specific string or regex pattern across files in a directory using ripgrep.",
        "parameters": {"query": "The text to search for.", "search_path": "The directory to search inside.", "is_regex": "Set true to use regex matching.", "case_insensitive": "Set true to ignore case."}
    },
    {
        "name": "final_answer",
        "description": "Send the final text response back to the user when the task is complete.",
        "parameters": {"message": "The final message content to output to the user."}
    },
    {
        "name": "invoke_subagent",
        "description": "Spawn a new AI subagent with a specialized role to work on a subtask. This does NOT run shell commands — use `run_command` for that. The role should be an AI specialty like 'Researcher', 'QA Tester', 'Code Reviewer', or 'Security Auditor'. The task should be a natural-language description of what you want the AI to do, like 'Read the README and summarize the architecture'.",
        "parameters": {"role": "The AI specialty role, e.g. 'Researcher', 'QA Tester', 'Code Reviewer'. NOT a terminal name.", "task": "A natural-language description of the AI task. NOT a shell command."}
    },
    {
        "name": "send_message",
        "description": "Send a natural-language message to another AI subagent by its role name. Use this to hand off results, request reviews, or coordinate between agents.",
        "parameters": {"recipient_role": "The role name of the AI subagent to send the message to.", "message": "The natural-language message content."}
    },
    {
        "name": "check_inbox",
        "description": "Check your inbox for messages from other AI subagents.",
        "parameters": {"my_role": "Your role name to check messages for."}
    },
    {
        "name": "wait",
        "description": "Pause execution for a specified duration in seconds to let subagents finish or avoid hot-polling.",
        "parameters": {"seconds": "The number of seconds to sleep (e.g. 5 or 10)."}
    },
    {
        "name": "get_secret",
        "description": "Read a secret (like a token or password) from the local secrets vault. Use this before running commands that require authentication.",
        "parameters": {"key": "The name of the secret to retrieve (e.g. 'github_token')."}
    },
    {
        "name": "set_secret",
        "description": "Save a secret to the local secrets vault for future use. Ask the user for the token first, then save it.",
        "parameters": {"key": "The name of the secret (e.g. 'github_token').", "value": "The actual secret string."}
    },
    {
        "name": "run_sandboxed",
        "description": "Run an untrusted command in a restricted sandbox with no network access and a 30-second timeout. Use this for running user-generated or AI-generated code that has not been reviewed.",
        "parameters": {"command": "The shell command string to execute in the sandbox."}
    }
]

def execute_tool(name: str, args: Dict[str, Any]) -> str:
    try:
        # Normalize all argument keys to lowercase to gracefully handle LLM capitalization hallucinations
        args = {k.lower(): v for k, v in args.items()}
        
        # Parameter Name Alias Normalization:
        # Map alternate path parameters to 'relative_path'
        for path_key in ["path", "absolutepath", "directorypath", "search_path", "file_path", "filepath"]:
            if path_key in args:
                if "relative_path" not in args or isinstance(args["relative_path"], bool):
                    args["relative_path"] = args[path_key]
        # Map alternate content parameters to 'content'
        for content_key in ["codecontent", "code_content", "text", "replacementcontent"]:
            if content_key in args:
                if "content" not in args or isinstance(args["content"], bool):
                    args["content"] = args[content_key]
        
        if name == "run_command": return run_command(args["command"])
        elif name == "read_file": return read_file(args["relative_path"], args.get("start_line", 1), args.get("end_line"))
        elif name == "write_file": return write_file(args["relative_path"], args["content"])
        elif name == "replace_file_content": return replace_file_content(args["relative_path"], args["search_content"], args["replacement_content"])
        elif name == "edit_lines": return edit_lines(args["relative_path"], int(args["start_line"]), int(args["end_line"]), args["new_content"])
        elif name == "list_dir": return list_dir(args.get("relative_path", "."))
        elif name == "search_knowledge_bank": return search_knowledge_bank(args["query"])
        elif name == "web_search": return web_search(args["query"])
        elif name == "web_fetch": return web_fetch(args["url"])
        elif name == "gmail_list_emails": return gmail_list_emails(args.get("max_emails", 5), args.get("folder", "INBOX"))
        elif name == "gmail_read_email": return gmail_read_email(args["email_id"])
        elif name == "gmail_delete_email": return gmail_delete_email(args["email_id"])
        elif name == "grep_search": return grep_search(args["query"], args.get("search_path", "."), args.get("is_regex", False), args.get("case_insensitive", True))
        elif name == "get_secret": return get_secret(args["key"])
        elif name == "set_secret": return set_secret(args["key"], args["value"])
        elif name == "final_answer": return args.get("message", "Task completed.")
        elif name == "invoke_subagent": return invoke_subagent(args["role"], args["task"])
        elif name == "send_message": return send_message(args["recipient_role"], args["message"])
        elif name == "check_inbox": return check_inbox(args["my_role"])
        elif name == "wait": return wait(args["seconds"])
        elif name == "run_sandboxed": return run_sandboxed(args["command"])
        else: return f"Error: Tool '{name}' is not recognized."
    except KeyError as e:
        return f"Error: Missing required argument '{e.args[0]}' for tool '{name}'."
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"
