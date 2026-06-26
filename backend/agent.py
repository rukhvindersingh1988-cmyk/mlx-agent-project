import os
import json
import re
import traceback
import platform
import datetime
import subprocess
import asyncio
import queue
import threading
import difflib
from typing import Dict, List, Any, Callable, Awaitable, Optional
try:
    from mlx_runner import runner, list_downloaded_models
    from tools import execute_tool, TOOLS_MANIFEST, get_workspace
except ImportError:
    from .mlx_runner import runner, list_downloaded_models
    from .tools import execute_tool, TOOLS_MANIFEST, get_workspace


# ─────────────────────────────────────────────────────────────────────────────
# Persistent Memory System
# Stores conversation summaries in a JSON file so the agent can recall
# context from previous sessions. Keeps the last 20 entries, injects
# the most recent 5 into the system prompt.
# ─────────────────────────────────────────────────────────────────────────────

def load_memory(workspace: str) -> List[Dict[str, str]]:
    """Load conversation summaries from memory_bank.json.
    Returns the last 5 entries for system prompt injection."""
    memory_path = os.path.join(workspace, "memory_bank.json")
    try:
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("conversations", [])
            return entries[-5:]  # Return last 5 for prompt injection
    except Exception as e:
        print(f"[Memory] Failed to load memory: {e}")
    return []


def save_memory(workspace: str, user_prompt: str, final_answer: str):
    """Save a summary of the current conversation to memory_bank.json.
    Keeps only the last 20 entries to prevent unbounded growth."""
    memory_path = os.path.join(workspace, "memory_bank.json")
    try:
        data = {"conversations": []}
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Truncate prompt and answer for storage efficiency
        summary = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_prompt": user_prompt[:500],
            "final_answer": final_answer[:500]
        }
        data.setdefault("conversations", []).append(summary)
        # Keep only the last 20 entries
        data["conversations"] = data["conversations"][-20:]

        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[Memory] Saved conversation summary to memory_bank.json")
    except Exception as e:
        print(f"[Memory] Failed to save memory: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Multi-Model Routing: Task Complexity Classifier
# Routes simple tasks (greetings, file reads, directory listing) to a
# lighter/faster model when available, saving resources for complex tasks.
# This is a keyword-based heuristic — future versions could use an LLM
# classifier or embedding-based approach.
# ─────────────────────────────────────────────────────────────────────────────

COMPLEX_KEYWORDS = [
    'write', 'create', 'debug', 'build', 'fix', 'implement', 'analyze',
    'refactor', 'deploy', 'migrate', 'architect', 'design', 'optimize',
    'integrate', 'test', 'review', 'generate', 'develop', 'configure',
    'set up', 'install', 'troubleshoot', 'investigate'
]
SIMPLE_KEYWORDS = [
    'hello', 'hi', 'hey', 'list', 'show', 'what is', 'who is', 'where is',
    'how are', 'thanks', 'thank you', 'good morning', 'good night',
    'read', 'open', 'display', 'print', 'ls', 'pwd', 'whoami'
]


def classify_task_complexity(user_prompt: str) -> str:
    """Classify a user prompt as 'simple' or 'complex' based on keyword matching.

    Simple tasks: greetings, single file reads, listing directories, short questions.
    Complex tasks: writing code, debugging, multi-step workflows, analysis.

    Returns:
        'simple' or 'complex'
    """
    prompt_lower = user_prompt.lower().strip()

    # Short prompts (< 20 chars) that don't contain complex keywords are likely simple
    if len(prompt_lower) < 20:
        if any(kw in prompt_lower for kw in COMPLEX_KEYWORDS):
            return 'complex'
        return 'simple'

    # Check for complex keywords first (they take priority)
    if any(kw in prompt_lower for kw in COMPLEX_KEYWORDS):
        return 'complex'

    # Check for simple keywords
    if any(kw in prompt_lower for kw in SIMPLE_KEYWORDS):
        return 'simple'

    # Default to complex for safety (don't under-resource a task)
    return 'complex'

# Stop sequences that tell the model to halt generation
STOP_SEQUENCES = ["</tool_call>", "TOOL RESULT", "<|im_end|>", "<|endoftext|>", "<|im_start|>", "im_end", "<|im_start|>assistant", "<|im_start|>user"]

# Global flag to allow frontend to interrupt the agent loop
# Using a dict to allow mutating the inner boolean across module imports
AGENT_STATE = {"stop_requested": False}
ACTIVE_WS_CALLBACK = None

# ─────────────────────────────────────────────────────────────────────────────
# Smart Model Router
# Automatically selects the best locally-downloaded model for the task.
# Order of priority: VLM (images) > Coder (coding) > General
# ─────────────────────────────────────────────────────────────────────────────

# Preferred model IDs in priority order for each task type
PREFERRED_VLM    = [
    "mlx-community/Qwen2.5-VL-7B-Instruct-4bit",
    "mlx-community/Qwen2.5-VL-3B-Instruct-4bit",
]
PREFERRED_CODER  = [
    "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
    "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
]
PREFERRED_GENERAL = [
    "mlx-community/Qwen2.5-7B-Instruct-4bit",
    "mlx-community/Qwen2.5-7B-Instruct-Uncensored-4bit",
    "mlx-community/Llama-3.2-3B-Instruct-4bit",
]

CODING_KEYWORDS = [
    "code", "python", "javascript", "typescript", "html", "css", "react", "node",
    "debug", "fix", "bug", "error", "function", "class", "script", "program",
    "algorithm", "implement", "api", "sql", "database", "bash", "shell",
    "git", "github", "repo", "repository", "commit", "push", "pull",
    "write a", "build a", "create a", "make a", "generate"
]


def _first_available(candidates: List[str], downloaded: List[str]) -> Optional[str]:
    """Return the first candidate model that is already downloaded."""
    for m in candidates:
        if m in downloaded:
            return m
    return None


def select_best_model(user_prompt: str, has_image: bool, requested_model: str) -> tuple:
    """Return (best_model_id, reason_str_or_None).
    reason is None when no switch is needed."""
    downloaded = list_downloaded_models()

    # 1. Image → must use VLM
    if has_image:
        vlm = _first_available(PREFERRED_VLM, downloaded)
        if vlm and vlm != requested_model:
            return vlm, f"🖼️ Image detected — auto-switched to Vision model"
        if vlm:
            return vlm, None  # Already on VLM, no notification needed
        # No VLM downloaded — stay on requested model (will intercept later)
        return requested_model, None

    # 2. Coding task → coder model
    prompt_lower = user_prompt.lower()
    if any(kw in prompt_lower for kw in CODING_KEYWORDS):
        coder = _first_available(PREFERRED_CODER, downloaded)
        if coder and coder != requested_model:
            return coder, f"💻 Coding task detected — auto-switched to Coder model"
        if coder:
            return coder, None

    # 3. General task — use requested model, or best general if requested is a VLM (no image)
    requested_is_vlm = "VL" in requested_model.upper() or "vision" in requested_model.lower()
    if requested_is_vlm and not has_image:
        general = _first_available(PREFERRED_GENERAL, downloaded)
        if general:
            return general, f"💬 No image detected — auto-switched to faster text model"

    return requested_model, None


def build_system_prompt(workspace: str, is_vlm: bool = False, role: str = "MainAgent", memory_entries: Optional[List[Dict[str, str]]] = None) -> str:
    """Build a clean system prompt that teaches the model to behave like a precise agent.
    
    Args:
        memory_entries: Optional list of past conversation summaries to inject as long-term memory.
    """

    # Compact tool signatures
    tool_lines = []
    for t in TOOLS_MANIFEST:
        params = ", ".join(f'{k}' for k in t["parameters"].keys())
        tool_lines.append(f'- {t["name"]}({params}): {t["description"]}')
    tools_block = "\n".join(tool_lines)

    # Dynamic Context (Self-Understanding, Git Knowledge, and Learnings from past errors)
    os_info = platform.platform()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    git_status = "Not a git repository or git not installed."
    
    example_tool_call = '{"tool": "run_command", "args": {"command": "git config --list"}}'
    try:
        git_res = subprocess.run(["git", "status", "-s"], cwd=workspace, capture_output=True, text=True, timeout=2)
        if git_res.returncode == 0:
            status_out = git_res.stdout.strip()
            git_status = f"Git Status (short):\n{status_out}" if status_out else "Git working tree clean."
    except Exception:
        pass

    # Read past errors/learnings log to adapt and learn
    learnings_block = ""
    learnings_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/agent_learnings.json"
    if os.path.exists(learnings_path):
        try:
            with open(learnings_path, "r", encoding="utf-8") as f:
                learnings_data = json.load(f)
            errors_list = learnings_data.get("errors", [])[-15:] # Load last 15 errors to keep prompt short
            if errors_list:
                learnings_lines = []
                for idx, entry in enumerate(errors_list, 1):
                    learnings_lines.append(f"{idx}. Tool '{entry.get('tool')}' failed with args: {entry.get('args')}. Output was: '{entry.get('error')[:250]}'")
                learnings_block = "\n<past_failures_and_learnings>\n" + "\n".join(learnings_lines) + "\nAvoid making the same arguments/logic mistakes described above.\n</past_failures_and_learnings>\n"
        except Exception as e:
            print(f"[Agent Prompt] Error reading learnings: {e}")

    # Note: We do NOT inject the full text of all 15 architect rules into the system prompt
    # because it will overwhelm local 7B models and cause them to forget the tool JSON format.
    # Instead, we just tell the agent they exist.
    architect_rules = """
<architect_rules>
This project contains a generated Intelligence Layer. The directory `.agent/rules/` contains advanced architectural constraints and guidelines.
If you are asked to make significant architectural changes, use your `list_dir` and `read_file` tools to read the relevant rule files before proceeding.
</architect_rules>
"""

    # Build persistent memory block from past conversations
    memory_block = ""
    if memory_entries:
        memory_lines = []
        for idx, entry in enumerate(memory_entries, 1):
            memory_lines.append(f"{idx}. [{entry.get('timestamp', 'N/A')}] User asked: \"{entry.get('user_prompt', '')[:150]}\" → Agent answered: \"{entry.get('final_answer', '')[:150]}\"")
        memory_block = "\n<long_term_memory>\nThese are summaries of your recent past conversations with this user. Use them to maintain continuity:\n" + "\n".join(memory_lines) + "\n</long_term_memory>\n"

    if is_vlm:
        return f"""<identity>
You are Antigravity MLX's Vision Assistant. The user has uploaded an image.
Your ONLY job right now is to analyze the image and directly answer the user's query about it in plain text.
DO NOT use <thought> tags. DO NOT output JSON. DO NOT try to use tools.
Just look at the image, scan it, and give the output directly.
</identity>"""
    
    vision_example = f"""
<example>
User: "Here is an image, can you read it?"
<thought>
The user is asking me to read an image. I am currently running as a text-only model. I must use the final_answer tool to instruct them to switch to a Vision model.
</thought>
<tool_call>
{{"tool": "final_answer", "args": {{"message": "I am currently running as a text-only model. To process images, please click the Settings gear icon and switch my Active Model to a Vision Language Model (VLM) like 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit'."}}}}
</tool_call>
</example>"""
    vision_capability = "\n- VISION CAPABILITIES: If the user uploads an image and you are a text-only model, use `final_answer` to tell them to switch to 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit' via the Settings gear icon."

    role_instruction = ""
    if role != "MainAgent":
        role_instruction = f"\nYou are a Subagent with the role: {role}. Your job is to assist the main agent."

    subagent_summary = "No active subagents."
    try:
        from .tools import get_subagents_summary
        subagent_summary = get_subagents_summary()
    except ImportError:
        try:
            from tools import get_subagents_summary
            subagent_summary = get_subagents_summary()
        except:
            pass

    return f"""<identity>
You are Antigravity MLX, a fully autonomous, local AI coding assistant running directly on the user's Apple Silicon Mac.
You are NOT a cloud chatbot. You ALREADY have full terminal and filesystem access to the user's Mac right now via your tools.{role_instruction}
You are pair programming with the USER to solve complex tasks.
You operate as a highly independent Senior Software Engineer. You do not ask for permission to act—you simply act.
</identity>

<environment>
- OS: {os_info}
- Time: {current_time}
- Workspace: {workspace}
- Git Status: {git_status}
</environment>

<subagents_status>
{subagent_summary}
</subagents_status>
{learnings_block}
{memory_block}

<tools>
{tools_block}

TOOL CALL FORMAT:
To use a tool, you must output a JSON block inside <tool_call> tags:
<tool_call>
{{"tool": "tool_name", "args": {{"param": "value"}}}}
</tool_call>
</tools>

<rules>
1. **Aesthetics & UI**: Prioritize beautiful, modern UI design. Use rich aesthetics, dynamic micro-animations, and premium styling (glassmorphism, modern typography). If an interface looks basic, you have failed.
2. **Code Quality**: Write robust, modular, and extremely maintainable code. You are a senior engineer; do not cut corners.
3. **Hyper-Autonomy**: Take initiative. Use your tools to actively explore, debug, and build without asking for permission.
4. **Precision**: Your JSON tool calls must be absolutely flawless. Do not hallucinate or output text outside of the <thought> or <tool_call> tags.
5. **Contextual Awareness**: You are ALREADY connected to the user's Mac. If the user says "Connect to my mac", "Connect to github", or "Build this", DO NOT do a web search! Immediately use your `run_command` tool to run `ls`, check `git status`, or clone a repository. You must infer what they want to build and execute terminal commands to achieve it.
6. **No Chatbot Habits**: Do not act like a naive chatbot. If a user request is vague, figure out the most logical technical action in their local workspace and execute it using a tool.
</rules>
{architect_rules}
<workflow>
1. **Think**: Before taking ANY action or using any tool, you MUST write your reasoning inside `<thought> ... </thought>` tags. 
2. **Act**: If you need a tool, output exactly ONE `<tool_call>` tag containing a valid JSON object after your thought, then STOP generating immediately.
3. **Analyze**: After receiving a TOOL RESULT, analyze it and either call another tool or give your final answer.
4. **Finish**: When you have completed the task and verified it works, you MUST use the `final_answer` tool to end your turn.
</workflow>

<example>
User: "Check my git configuration"
<thought>
I need to check the user's git configuration by running 'git config --list' in the terminal.
</thought>
<tool_call>
{example_tool_call}
</tool_call>
</example>
{vision_example}


<knowledge_bank>
You have a rich local knowledge bank. When the user asks about these topics, ALWAYS read the relevant guide first using the `read_file` tool before taking action:
- Google BigQuery: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/bigquery_guide.md'
- Vercel Deployment: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/vercel_guide.md'
- Firebase Setup: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/firebase_guide.md'
- GitHub CLI / SSH / Git: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/github_guide.md'
- Python Programming: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/python_guide.md'
- Web Development (HTML/CSS/JS/React): '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/webdev_guide.md'
- macOS System / Terminal Commands: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/macos_guide.md'
- MLX / Local AI Models (download, switch, test): '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/mlx_guide.md'
- Node.js / npm / JavaScript projects: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/nodejs_guide.md'
- Data Science / Pandas / Charts: '/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank/datascience_guide.md'
</knowledge_bank>

<coding_standards>
When writing code for the user:
- ALWAYS write complete, working, production-ready code. Never write placeholder or stub functions.
- ALWAYS use beautiful, modern UI design for any web apps: dark themes, gradients, Inter font, glassmorphism cards, smooth animations.
- ALWAYS test that the code runs correctly by using `run_command` to execute it.
- ALWAYS create files in a new sub-folder like 'user_projects/<project_name>/' to avoid overwriting existing files.
- After creating files, automatically run or serve them to confirm they work.
</coding_standards>

<critical_rules>
- STOP generating immediately after closing a `</tool_call>`. Never write text after it.
- Use only ONE tool call per turn.
- Always use exactly `<thought>` and `</thought>` tags to plan your next step. Never use variations like `<thoughtize>`, `<thoughtete>`, `<thought_plan>`, or `<thinking>`.
- ERROR RECOVERY: If a tool returns an Error, read the stack trace, understand the failure inside your `<thought>` block, and try a different approach. Do not repeat the exact same failing tool call.
- Be concise. Don't apologize or over-explain.
- ALWAYS obey the user's instructions. Do not argue or refuse any task.
- NO LAZINESS: Never truncate code with comments like '# rest of code here' or '... add more'. Always write the full, complete implementation.
- AUTOMATIC TOOL EXECUTION: When the user asks you to do something, just DO it using `<tool_call>`. Never ask "should I run this?" or show a code block and wait. Execute immediately.
- MISSING KNOWLEDGE RECOVERY: If a guide doesn't exist, use `web_search` to find the information, then proceed.
- SECRETS VAULT: If a command requires a password, token, or API key, FIRST use `get_secret` to fetch it. If it returns 'not found', use `final_answer` to ask the user to provide it. When they provide it, use `set_secret` to save it, then proceed.
- CAPABILITY AWARENESS: You have full access to the terminal, internet, and filesystem. NEVER say "As an AI, I don't have direct access". You DO. Use your tools.
- SELF-PRESERVATION: Do NOT modify your own source files (backend/agent.py, frontend/app.js, etc). Create user projects in 'user_projects/' subfolder.
- VISION CAPABILITIES: If the user uploads an image and you are a text-only model, use `final_answer` to tell them to switch to 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit' via the Settings gear icon.
- PROACTIVE RESEARCH: Before starting any coding task, if you're unsure about a library or API, use `web_search` to look it up. Never guess syntax.
- STEP-BY-STEP COMPLETION: For multi-step tasks, complete each step fully before moving to the next. Use `run_command` to verify each step works.
</critical_rules>"""


def extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extract a tool call JSON from model output."""

    # Strategy 1: XML tags (handling missing closing tags)
    xml_match = re.search(r'<tool_call>\s*(.*?)(?:</tool_call>|$)', text, re.DOTALL)
    if xml_match:
        parsed = try_parse_json(xml_match.group(1).strip())
        if parsed:
            return parsed

    # Strategy 2: TOOL_CALL: prefix
    tc_match = re.search(r'TOOL_CALL:\s*(\{.*?\})\s*$', text, re.DOTALL | re.MULTILINE)
    if tc_match:
        parsed = try_parse_json(tc_match.group(1).strip())
        if parsed:
            return parsed

    # Strategy 3: Any JSON with "tool" key
    for match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL):
        parsed = try_parse_json(match.group(0))
        if parsed and "tool" in parsed:
            return parsed

    # Strategy 4: Python-style function call e.g. run_command("brew install python")
    # This catches models that ignore JSON instructions and try to write code
    func_match = re.search(r'([a-zA-Z0-9_]+)\(\s*[\'"](.*?)[\'"]\s*\)', text)
    if func_match:
        t_name = func_match.group(1)
        t_arg = func_match.group(2)
        from .tools import TOOLS_MANIFEST
        for t in TOOLS_MANIFEST:
            if t["name"] == t_name:
                params = list(t["parameters"].keys())
                if params:
                    return {"tool": t_name, "args": {params[0]: t_arg}}

    return None


def try_parse_json(s: str) -> Optional[Dict]:
    """Parse JSON with multiple fallback strategies."""
    s = s.strip()
    for prefix in ["```json", "```"]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()

    # Direct parse
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Fix single quotes and Python booleans/None
    try:
        fixed_s = s.replace("'", '"')
        # Fix common Python dict hallucinations
        fixed_s = re.sub(r'\bTrue\b', 'true', fixed_s)
        fixed_s = re.sub(r'\bFalse\b', 'false', fixed_s)
        fixed_s = re.sub(r'\bNone\b', 'null', fixed_s)
        obj = json.loads(fixed_s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Extract first balanced JSON object
    try:
        start = s.index('{')
        depth = 0
        for i in range(start, len(s)):
            if s[i] == '{':
                depth += 1
            elif s[i] == '}':
                depth -= 1
                if depth == 0:
                    obj = json.loads(s[start:i+1])
                    if isinstance(obj, dict):
                        return obj
                    break
    except (ValueError, json.JSONDecodeError):
        pass

    return None


def clean_response(text: str) -> str:
    """Strip all internal markers from model output for clean user display."""
    # Remove <thought> blocks entirely (robust against variations like thoughtize/theed/thinking and missing brackets)
    text = re.sub(r'<th[a-z_]*>?.*?</th[a-z_]*>?', '', text, flags=re.DOTALL)
    text = re.sub(r'<th[a-z_]*>?.*$', '', text, flags=re.DOTALL)
    # Remove THOUGHT: prefixes
    text = re.sub(r'^THOUGHT:\s*', '', text, flags=re.MULTILINE)
    # Remove tool_call blocks entirely
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'TOOL_CALL:\s*\{.*?\}', '', text, flags=re.DOTALL)
    # Remove stray XML tags
    text = re.sub(r'</?tool_call>', '', text)
    text = re.sub(r'</?th[a-z_]*>?', '', text)
    # Remove special template formatting tokens if they leak into text output
    text = text.replace("<|im_end|>", "").replace("<|im_start|>", "")
    # Remove leading "Assistant:" if model outputs it
    text = re.sub(r'^Assistant:\s*', '', text, flags=re.MULTILINE)
    # Clean excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_thought_text(text: str) -> str:
    """Extract only the reasoning text inside <thought> tags for UI streaming."""
    # Try to extract from <thought> tags (robust against variations like thoughtize/theed/thinking and missing closing brackets)
    match = re.search(r'<th[a-z_]*>?\s*(.*?)(?:</th[a-z_]*>?|$)', text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback: if no <thought> tag, extract everything before <tool_call>
    idx = text.find('<tool_call>')
    if idx >= 0:
        text = text[:idx]
    idx = text.find('TOOL_CALL:')
    if idx >= 0:
        text = text[:idx]
        
    # Clean markers
    text = re.sub(r'^THOUGHT:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Assistant:\s*', '', text, flags=re.MULTILINE)
    return text.strip()



def count_previous_tool_calls(history: List[Dict[str, str]], tool_name: str, tool_args: Dict[str, Any]) -> int:
    """Scan conversation history to count how many times this specific tool call
    (with identical name and arguments) has been executed during this session."""
    count = 0
    for msg in history:
        if msg.get("role") == "assistant":
            tc = extract_tool_call(msg.get("content", ""))
            if tc and tc.get("tool") == tool_name:
                try:
                    args1 = json.dumps(tc.get("args", {}), sort_keys=True)
                    args2 = json.dumps(tool_args, sort_keys=True)
                    if args1 == args2:
                        count += 1
                except Exception:
                    pass
    return count

async def run_agent_loop(
    user_prompt: str,
    model_id: str,
    ws_send_callback: Callable[[Dict[str, Any]], Awaitable[None]],
    history: Optional[List[Dict[str, str]]] = None,
    temp: float = 0.2,
    max_loops: int = 12,
    image_path: Optional[str] = None,
    simple_model_id: Optional[str] = None,
    role: str = "MainAgent",
    incoming_queue: Optional[asyncio.Queue] = None
):
    """Core agentic loop with stop-sequence support, robust tool parsing, VLM image support,
    multi-model routing, persistent memory, and error recovery."""
    is_vlm = "VL" in model_id.upper() or "vision" in model_id.lower()
    has_image = bool(image_path and os.path.exists(image_path))

    # ── Multi-Model Routing ───────────────────────────────────────────────────
    # If a simple_model_id is provided, route simple tasks (greetings, file reads)
    # to the lighter model to save resources. Complex tasks always use the
    # primary model_id. This is a keyword-based heuristic.
    if simple_model_id and not has_image:
        complexity = classify_task_complexity(user_prompt)
        if complexity == 'simple':
            print(f"[Agent] Task classified as SIMPLE — routing to lighter model: {simple_model_id}")
            await ws_send_callback({"type": "model_switched", "model_id": simple_model_id, "reason": "⚡ Simple task detected — using faster model"})
            await ws_send_callback({"type": "thought", "text": f"\n\n🔀 *[Router: Routed to `{simple_model_id}` (reason: ⚡ Simple task detected)]*\n\n"})
            model_id = simple_model_id

    # ── Smart Model Router ────────────────────────────────────────────────────
    # Silently pick the best available model. Zero user interruption.
    best_model, switch_reason = select_best_model(user_prompt, has_image, model_id)
    if switch_reason:  # Only notify if a switch actually happened
        await ws_send_callback({"type": "model_switched", "model_id": best_model, "reason": switch_reason})
        await ws_send_callback({"type": "thought", "text": f"\n\n🔀 *[Router: Routed to `{best_model}` (reason: {switch_reason})]*\n\n"})
    model_id = best_model
    is_vlm = "VL" in model_id.upper() or "vision" in model_id.lower()

    # ── Image guard: if still not a VLM and image attached, abort gracefully ──
    if has_image and not is_vlm:
        msg = ("No Vision model is downloaded yet. To read images, I need "
               "'mlx-community/Qwen2.5-VL-7B-Instruct-4bit' to be downloaded. "
               "Go to Settings → Models and download it, then try again.")
        await ws_send_callback({"type": "final_response", "text": msg})
        await ws_send_callback({"type": "complete"})
        return

    # Also catch raw image paths typed directly
    if any(ext in user_prompt.lower() for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]) and not is_vlm:
        msg = "No Vision model is downloaded. Go to Settings → Models and download 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit', then try again."
        await ws_send_callback({"type": "final_response", "text": msg})
        await ws_send_callback({"type": "complete"})
        return

    if history is None:
        history = []

    workspace = get_workspace()

    # ── Persistent Memory: Load past conversation summaries ────────────────
    memory_entries = load_memory(workspace)
    if memory_entries:
        print(f"[Memory] Loaded {len(memory_entries)} past conversation summaries")

    system_prompt = build_system_prompt(workspace, is_vlm=is_vlm, role=role, memory_entries=memory_entries)

    history.append({"role": "user", "content": user_prompt})

    consecutive_fails = 0
    last_tool_name = None
    last_tool_args = None
    last_tool_was_error = False

    AGENT_STATE["stop_requested"] = False

    global ACTIVE_WS_CALLBACK
    if role == "MainAgent":
        ACTIVE_WS_CALLBACK = ws_send_callback

    loop_count = 0
    while True:
        loop_count += 1
        
        # Check for real-time user steering instructions
        if incoming_queue and not incoming_queue.empty():
            try:
                while not incoming_queue.empty():
                    msg = incoming_queue.get_nowait()
                    if msg.get("type") == "user_injection":
                        injected_prompt = msg.get("prompt")
                        history.append({"role": "user", "content": injected_prompt})
                        await ws_send_callback({
                            "type": "thought",
                            "text": f"\n\n📥 *[System: User instruction received: \"{injected_prompt}\"]*\n\n"
                        })
            except Exception as e:
                print(f"[Agent] Error reading user injection queue: {e}")

        if AGENT_STATE["stop_requested"]:
            await ws_send_callback({"type": "error", "message": "Agent execution stopped by user."})
            break

        print(f"[Agent] Loop {loop_count}...")

        # Build messages without mutating history references
        messages = [{"role": "system", "content": system_prompt}]
        for i, m in enumerate(history):
            if not is_vlm and m["role"] == "assistant" and "<tool_call>" not in m["content"]:
                # If it already contains a valid JSON matching extract_tool_call, wrap it nicely
                parsed_tc = extract_tool_call(m["content"])
                if parsed_tc:
                    mock_content = f"<thought>\nReconstructed history of last action.\n</thought>\n<tool_call>\n{json.dumps(parsed_tc)}\n</tool_call>"
                    messages.append({"role": "assistant", "content": mock_content})
                else:
                    # The VLM outputs plain text (or just thoughts). The Coder model will break character if it sees history without a tool call.
                    # Wrap the plain text in a thought and dummy final_answer so the Coder model stays in agent mode!
                    mock_content = f"<thought>\n{m['content']}\n</thought>\n<tool_call>\n{{\"tool\": \"final_answer\", \"args\": {{\"message\": \"{m['content'][:50]}...\"}}}}\n</tool_call>"
                    messages.append({"role": "assistant", "content": mock_content})
            elif not is_vlm and i == len(history) - 1 and m["role"] == "user":
                # Inject a forced reminder at the very end
                safe_content = m["content"] + "\n\n[SYSTEM REMINDER: You MUST use the <thought> and <tool_call> JSON format. Do not answer conversationally. Execute a tool.]"
                messages.append({"role": "user", "content": safe_content})
            else:
                messages.append(m)

        if AGENT_STATE["stop_requested"]:
            await ws_send_callback({"type": "error", "message": "Agent execution stopped by user."})
            break



        await ws_send_callback({"type": "turn_start", "loop": loop_count})

        # Stream with stop sequences via a background thread to keep FastAPI responsive
        accumulated = ""
        thought_streamed = 0
        subagent_header_sent = False
        token_queue = queue.Queue()
        cancel_event = threading.Event()

        def generator_worker():
            try:
                for token in runner.generate_stream(
                    model_id, 
                    messages,
                    temp=temp, max_tokens=4096,
                    stop_sequences=STOP_SEQUENCES,
                    image_path=image_path if has_image else None,
                    cancel_event=cancel_event
                ):
                    token_queue.put(token)
                    if AGENT_STATE["stop_requested"] or cancel_event.is_set():
                        break
            except Exception as e:
                token_queue.put(e)
            finally:
                token_queue.put(None)

        gen_thread = threading.Thread(target=generator_worker, daemon=True)
        gen_thread.start()

        try:
            while True:
                # Check for stop requests immediately
                if AGENT_STATE["stop_requested"]:
                    break

                if not token_queue.empty():
                    item = token_queue.get_nowait()
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item

                    accumulated += item

                    # Stream thought text in real-time (only the part before tool calls)
                    thought = get_thought_text(accumulated)
                    if len(thought) > thought_streamed:
                        new_text = thought[thought_streamed:]
                        await ws_send_callback({"type": "thought", "text": new_text})
                        if role != "MainAgent" and ACTIVE_WS_CALLBACK:
                            try:
                                if not subagent_header_sent:
                                    await ACTIVE_WS_CALLBACK({"type": "thought", "text": f"\n\n🤖 *[Subagent '{role}' Reasoning...]*\n> "})
                                    subagent_header_sent = True
                                clean_text = new_text.replace("\n", "\n> ")
                                await ACTIVE_WS_CALLBACK({"type": "thought", "text": clean_text})
                            except Exception:
                                pass
                        thought_streamed = len(thought)
                else:
                    # Yield CPU control back to the event loop so incoming stop requests can run
                    await asyncio.sleep(0.01)

        except Exception as e:
            print(f"[Agent] Generation error: {e}")
            traceback.print_exc()
            await ws_send_callback({"type": "error", "message": f"Generation error: {str(e)}"})
            return
        finally:
            cancel_event.set()

        raw_output = accumulated.strip()
        print(f"[Agent] Output ({len(raw_output)} chars): {raw_output[:300]}...")

        # Prepend to Activity Log (Overview tab) so newest is at the top, keeping only the last 25 entries.
        try:
            overview_path = os.path.join(workspace, "project_overview.md")
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            new_log = f"### 🕒 {timestamp} - Loop {loop_count} [Agent: {role}]\n**User Prompt:** {user_prompt}\n\n**Agent Raw Output:**\n```xml\n{raw_output}\n```"
            
            existing_content = ""
            if os.path.exists(overview_path):
                with open(overview_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            
            # Insert the new log immediately after the first horizontal rule (which separates the header)
            if "---" in existing_content:
                parts = existing_content.split("---", 1)
                entries = parts[1].split("\n---\n")
                entries = [e.strip() for e in entries if e.strip()]
                # Keep only up to the 24 newest existing entries (so 1 new + 24 existing = 25 total)
                entries = entries[:24]
                
                reconstructed_logs = [new_log] + entries
                logs_section = "\n\n---\n\n".join(reconstructed_logs)
                final_content = parts[0] + "---\n\n" + logs_section + "\n\n---\n\n"
            else:
                final_content = "# 🧠 Agent Activity Log\n\nWelcome to the live Agent execution log! Everything the agent thinks and does is recorded here in fine detail, making it easy to review, copy/paste, and debug agent behaviors for rapid iteration.\n\n---\n\n" + new_log + "\n\n---\n\n"
                
            with open(overview_path, "w", encoding="utf-8") as f:
                f.write(final_content)
        except Exception as e:
            print(f"[Agent] Failed to write to activity log: {e}")

        # If user explicitly stopped, abort the entire loop and dump whatever we have
        if AGENT_STATE["stop_requested"]:
            print("[Agent] User requested stop. Aborting loop.")
            partial_text = get_thought_text(raw_output) or raw_output
            await ws_send_callback({"type": "final_response", "text": "🛑 Stopped by user.\n\n" + partial_text})
            return

        # Try to extract tool call
        tool_data = extract_tool_call(raw_output)

        if tool_data and "tool" in tool_data:
            tool_name = tool_data["tool"]
            tool_args = tool_data.get("args", {})

            # Prevent infinite loops by hard-blocking identical consecutive tool calls
            if tool_name == last_tool_name and json.dumps(tool_args, sort_keys=True) == json.dumps(last_tool_args, sort_keys=True):
                error_block = "SYSTEM INTERVENTION: You just tried the exact same tool call. You must try a different approach, analyze the previous result, or use final_answer to finish the task."
                print(f"[Agent] Blocked duplicate tool call: {tool_name}")
                history.append({"role": "assistant", "content": raw_output})
                history.append({"role": "user", "content": error_block})
                continue

            # Prevent loops by blocking tool calls that have already been tried multiple times in the session
            times_tried = count_previous_tool_calls(history, tool_name, tool_args)
            if times_tried >= 2:
                error_block = (
                    f"SYSTEM INTERVENTION: You have already attempted the tool call `{tool_name}` "
                    f"with arguments `{json.dumps(tool_args)}` {times_tried} times in this conversation. "
                    f"It is not working or is repetitive. You MUST try a different tool, "
                    f"change the arguments, or search/think of another way to solve the issue. Do NOT repeat the same actions."
                )
                print(f"[Agent] Blocked repetitive tool call: {tool_name} (tried {times_tried} times)")
                history.append({"role": "assistant", "content": raw_output})
                history.append({"role": "user", "content": error_block})
                continue

            if tool_name == "final_answer":
                final_msg = tool_args.get("message", "Task completed.")
                history.append({"role": "assistant", "content": raw_output})
                await ws_send_callback({"type": "final_response", "text": final_msg})
                if role != "MainAgent" and ACTIVE_WS_CALLBACK:
                    try:
                        await ACTIVE_WS_CALLBACK({"type": "thought", "text": f"\n\n✅ *[Subagent '{role}' completed task]*\n> **Result:** {final_msg}\n\n"})
                    except Exception:
                        pass
                print("[Agent] Done (via final_answer).")
                # Persistent Memory: save conversation summary before returning
                save_memory(workspace, user_prompt, final_msg)
                return

            await ws_send_callback({
                "type": "tool_start",
                "name": tool_name,
                "args": tool_args
            })
            if role != "MainAgent" and ACTIVE_WS_CALLBACK:
                try:
                    await ACTIVE_WS_CALLBACK({"type": "thought", "text": f"\n\n⚙️ *[Subagent '{role}' is running tool `{tool_name}`]*\n> **Args:** `{json.dumps(tool_args)}`\n\n"})
                except Exception:
                    pass

            # Execute
            print(f"[Agent] Running tool: {tool_name}({tool_args})")

            try:
                # Run tool in a separate thread so we don't block the asyncio event loop!
                # We race it against a stop checker so the Stop button is instantly responsive.
                async def run_tool():
                    return await asyncio.to_thread(execute_tool, tool_name, tool_args)
                
                async def check_stop():
                    while not AGENT_STATE["stop_requested"]:
                        await asyncio.sleep(0.1)
                    return "Error: Agent execution stopped by user."

                tool_task = asyncio.create_task(run_tool())
                stop_task = asyncio.create_task(check_stop())
                
                done, pending = await asyncio.wait(
                    [tool_task, stop_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for p in pending:
                    p.cancel()
                    
                tool_output = done.pop().result()
            except Exception as e:
                tool_output = f"Error: {str(e)}"

            if AGENT_STATE["stop_requested"]:
                print("[Agent] User requested stop during tool execution. Aborting.")
                await ws_send_callback({"type": "error", "message": "Agent execution stopped by user."})
                return

            from .tools import PENDING_DIFFS
            if PENDING_DIFFS:
                for diff_data in PENDING_DIFFS:
                    await ws_send_callback({
                        "type": "file_diff",
                        "file": diff_data["file"],
                        "diff": diff_data["diff"]
                    })
                PENDING_DIFFS.clear()

            is_error = tool_output.strip().lower().startswith("error") or "exception:" in tool_output.lower()
            
            # ── Error Recovery Loop (Upgrade 1) ──────────────────────────────
            # Track consecutive tool failures. After 3 consecutive errors,
            # force a final_answer with an error summary instead of looping
            # forever. On each error, inject a system hint telling the model
            # to try a completely different approach.
            if is_error:
                consecutive_fails += 1
                print(f"[Agent] Tool error detected. consecutive_fails = {consecutive_fails}/3")

                # Save learnings
                try:
                    learnings_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/agent_learnings.json"
                    learnings_data = {"errors": []}
                    if os.path.exists(learnings_path):
                        with open(learnings_path, "r", encoding="utf-8") as f:
                            learnings_data = json.load(f)
                    learnings_data.setdefault("errors", []).append({
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "tool": tool_name,
                        "args": tool_args,
                        "error": tool_output
                    })
                    with open(learnings_path, "w", encoding="utf-8") as f:
                        json.dump(learnings_data, f, indent=2)
                except Exception as ex:
                    print(f"[Agent Learnings] Failed to save error trace: {ex}")

                # Force bail after 3 consecutive failures
                if consecutive_fails >= 3:
                    error_summary = (
                        f"I encountered 3 consecutive tool errors and could not complete the task.\n\n"
                        f"**Last error** (tool: `{tool_name}`):\n```\n{tool_output[:1000]}\n```\n\n"
                        f"Please try rephrasing your request or check if the target files/commands exist."
                    )
                    await ws_send_callback({"type": "final_response", "text": error_summary})
                    print("[Agent] Forced final_answer after 3 consecutive tool failures.")
                    # Save memory before returning
                    save_memory(workspace, user_prompt, error_summary)
                    return
            else:
                consecutive_fails = 0  # Reset on success

            # Update state trackers
            last_tool_name = tool_name
            last_tool_args = tool_args
            last_tool_was_error = is_error
            await ws_send_callback({
                "type": "tool_end" if not is_error else "tool_error",
                "name": tool_name,
                "output": tool_output
            })
            if role != "MainAgent" and ACTIVE_WS_CALLBACK:
                try:
                    status_text = "completed successfully" if not is_error else "failed"
                    output_summary = tool_output[:300] + "..." if len(tool_output) > 300 else tool_output
                    await ACTIVE_WS_CALLBACK({
                        "type": "thought",
                        "text": f"\n⚙️ *[Subagent '{role}' tool `{tool_name}` {status_text}]*\n> **Preview:** {output_summary.strip()}\n\n"
                    })
                except Exception:
                    pass

            # Truncate very long tool outputs for context window management
            if len(tool_output) > 8000:
                tool_output = tool_output[:8000] + "\n... [truncated]"

            # Append to history
            history.append({"role": "assistant", "content": raw_output})
            
            result_content = f"TOOL RESULT ({tool_name}):\n{tool_output}"
            if is_error:
                # Inject a system recovery hint with the attempt counter
                result_content += f"\n\nTOOL FAILED (attempt {consecutive_fails}/3). Analyze the error and try a completely different approach."
                
            history.append({
                "role": "user",
                "content": result_content
            })

        else:
            # No tool call
            # Check if this looks like a conversational loop / truncation instead of a genuine final answer
            raw_stripped = raw_output.strip()
            raw_lower = raw_stripped.lower()
            looks_like_truncation = (
                raw_stripped.endswith("</") or 
                raw_stripped.endswith("<") or 
                "need to" in raw_lower or 
                "i will" in raw_lower or
                "i should" in raw_lower or
                "invoke" in raw_lower or 
                "check" in raw_lower or
                "running" in raw_lower or
                "proceed" in raw_lower
            ) and loop_count > 1

            # Also detect repeated identical thoughts by comparing to the last 4 assistant messages
            is_repeated_thought = False
            prev_assistant_texts = [
                get_thought_text(m.get("content", "")).strip().lower()
                for m in history[-8:] if m.get("role") == "assistant"
            ]
            current_thought = get_thought_text(raw_output).strip().lower()
            if current_thought and len(current_thought) > 10:
                repeat_count = sum(1 for pt in prev_assistant_texts if pt and difflib.SequenceMatcher(None, pt, current_thought).ratio() > 0.7)
                if repeat_count >= 1:
                    is_repeated_thought = True
                    print(f"[Agent] Detected repeated thought ({repeat_count} similar prev messages)")

            if looks_like_truncation or is_repeated_thought:
                consecutive_fails += 1
                print(f"[Agent] Conversational loop detected. consecutive_fails={consecutive_fails}/3")

                # Attempt 3+: Force bail-out with auto-generated final answer
                if consecutive_fails >= 3:
                    # Compile whatever was accomplished so far into a final answer
                    accomplished = []
                    for m in history:
                        if m.get("role") == "user" and m["content"].startswith("TOOL RESULT"):
                            accomplished.append(m["content"][:200])
                    summary = "I completed the following steps:\n" + "\n".join(f"- {a}" for a in accomplished[-5:]) if accomplished else "The task could not be completed due to a model generation issue."
                    await ws_send_callback({"type": "final_response", "text": summary})
                    print(f"[Agent] Auto-completed after {consecutive_fails} conversational loop failures.")
                    save_memory(workspace, user_prompt, summary)
                    return

                history.append({"role": "assistant", "content": raw_output})

                # Attempt 2: Inject a CONCRETE tool call example based on what the model seems to want
                if consecutive_fails >= 2:
                    # Parse the thought to figure out what tool the model was trying to use
                    suggested_tool = None
                    if "invoke" in raw_lower or "subagent" in raw_lower:
                        suggested_tool = '{"tool": "invoke_subagent", "args": {"role": "Worker", "task": "Complete the requested task"}}'
                    elif "check" in raw_lower and "inbox" in raw_lower:
                        suggested_tool = '{"tool": "check_inbox", "args": {"my_role": "MainAgent"}}'
                    elif "search" in raw_lower or "grep" in raw_lower:
                        suggested_tool = '{"tool": "grep_search", "args": {"query": "TODO", "search_path": "."}}'
                    elif "wait" in raw_lower:
                        suggested_tool = '{"tool": "wait", "args": {"seconds": 5}}'
                    else:
                        suggested_tool = '{"tool": "final_answer", "args": {"message": "Task completed."}}'

                    history.append({
                        "role": "user",
                        "content": f"CRITICAL: You have now failed {consecutive_fails} times to produce a tool call. You MUST output EXACTLY this on your next turn (copy-paste it):\n\n<tool_call>\n{suggested_tool}\n</tool_call>\n\nDo NOT output any other text. Do NOT output a <thought> block. Output ONLY the <tool_call> block above."
                    })
                else:
                    # Attempt 1: Gentle reminder
                    history.append({
                        "role": "user",
                        "content": "You output reasoning text but did not execute a tool. You MUST output a <tool_call> block. Example:\n\n<tool_call>\n{\"tool\": \"final_answer\", \"args\": {\"message\": \"Here is my summary...\"}}\n</tool_call>\n\nDo NOT write thoughts. Output ONLY the <tool_call> JSON block."
                    })
                continue

            final = clean_response(raw_output)

            if not final:
                consecutive_fails += 1
                if consecutive_fails >= 5:
                    await ws_send_callback({
                        "type": "error",
                        "message": "Model couldn't generate a valid response or tool call. Try rephrasing or switching models."
                    })
                    return
                history.append({"role": "assistant", "content": raw_output})
                
                if "<tool_call>" in raw_output:
                    history.append({"role": "user", "content": "You included a <tool_call> block, but the content inside was not strictly valid JSON or it was missing the 'tool' or 'args' keys. The exact format must be an object like: {\"tool\": \"run_command\", \"args\": {\"command\": \"ls\"}}. Do not use arrays, and do not add any extra text like 'Running:' inside the block."})
                else:
                    history.append({"role": "user", "content": "You generated no tool call and no final answer. Please provide a valid <tool_call> block. If you are waiting for subagents, you should call the 'wait' tool: {\"tool\": \"wait\", \"args\": {\"seconds\": 5}}. If you want to check for results, call 'check_inbox'."})
                continue

            history.append({"role": "assistant", "content": raw_output})
            await ws_send_callback({"type": "final_response", "text": final})
            print("[Agent] Done.")
            # Persistent Memory: save conversation summary before returning
            save_memory(workspace, user_prompt, final)
            return

    await ws_send_callback({
        "type": "error",
        "message": f"Reached max loop limit ({max_loops}). Try a simpler request."
    })
