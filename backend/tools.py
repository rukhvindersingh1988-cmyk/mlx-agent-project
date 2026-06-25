import os
import subprocess
import pathlib
import json
import smtplib
import imaplib
import email
import shutil
from email.header import decode_header
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
import difflib

PENDING_DIFFS = []

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
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
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
        cmd = ["rg"]
        if case_insensitive: cmd.append("-i")
        if match_per_line: cmd.append("-n")
        else: cmd.append("-l")
        if not is_regex: cmd.append("-F")
        cmd.extend(["--max-count", "50", query, target_path])
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if result.returncode == 0:
            return f"--- Search Results for '{query}' ---\n{result.stdout}"
        elif result.returncode == 1:
            return f"No matches found for '{query}'."
        else:
            return f"Search Error:\n{result.stderr}"
    except Exception as e:
        return f"Error executing search: {str(e)}"

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
    }
]

def execute_tool(name: str, args: Dict[str, Any]) -> str:
    try:
        if name == "run_command": return run_command(args["command"])
        elif name == "read_file": return read_file(args["relative_path"], args.get("start_line", 1), args.get("end_line"))
        elif name == "write_file": return write_file(args["relative_path"], args["content"])
        elif name == "replace_file_content": return replace_file_content(args["relative_path"], args["search_content"], args["replacement_content"])
        elif name == "list_dir": return list_dir(args.get("relative_path", "."))
        elif name == "web_search": return web_search(args["query"])
        elif name == "web_fetch": return web_fetch(args["url"])
        elif name == "gmail_list_emails": return gmail_list_emails(args.get("max_emails", 5), args.get("folder", "INBOX"))
        elif name == "gmail_read_email": return gmail_read_email(args["email_id"])
        elif name == "gmail_delete_email": return gmail_delete_email(args["email_id"])
        elif name == "grep_search": return grep_search(args["query"], args.get("search_path", "."), args.get("is_regex", False), args.get("case_insensitive", True))
        elif name == "final_answer": return args.get("message", "Task completed.")
        else: return f"Error: Tool '{name}' is not recognized."
    except KeyError as e:
        return f"Error: Missing required argument '{e.args[0]}' for tool '{name}'."
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"
