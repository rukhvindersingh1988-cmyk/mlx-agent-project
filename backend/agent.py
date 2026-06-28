import os
import json
import re
import ast
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
    from cloud_runner import is_cloud_model, stream_cloud
except ImportError:
    from .mlx_runner import runner, list_downloaded_models
    from .tools import execute_tool, TOOLS_MANIFEST, get_workspace
    from .cloud_runner import is_cloud_model, stream_cloud


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
STOP_SEQUENCES = ["</tool_call>", "TOOL RESULT", "<|im_end|>", "<|endoftext|>", "<|im_start|>", "im_end", "<|im_start|>assistant", "<|im_start|>user", "<end_of_turn>", "<start_of_turn>"]

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
    "mlx-community/gemma-2-9b-it-4bit",
    "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
    "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
]
PREFERRED_GENERAL = [
    "mlx-community/gemma-2-9b-it-4bit",
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

    # If the requested model is already downloaded, respect the user's choice!
    # (Only override if has_image is True and the requested model is not a VLM)
    requested_is_vlm = "VL" in requested_model.upper() or "vision" in requested_model.lower()
    if requested_model in downloaded:
        if has_image and not requested_is_vlm:
            pass
        else:
            return requested_model, None

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


def build_system_prompt(workspace: str, is_vlm: bool = False, role: str = "MainAgent", memory_entries: Optional[List[Dict[str, str]]] = None, model_id: str = "", simple_mode: bool = False) -> str:
    """Build a clean system prompt that teaches the model to behave like a precise agent.
    
    Args:
        memory_entries: Optional list of past conversation summaries to inject as long-term memory.
        model_id: Optional active model ID to dynamically customize syntax format rules.
        simple_mode: If True, strip auxiliary context (learnings, memories) to optimize KV cache.
    """

    is_gemma = "gemma" in model_id.lower()

    # Dynamic Formatting Instructions based on model capabilities
    if is_gemma:
        format_instructions = (
            "To use a tool, you must output a JSON block inside <tool_call> tags:\n"
            "<tool_call>\n"
            "{\"tool\": \"tool_name\", \"args\": {\"param\": \"value\"}}\n"
            "</tool_call>"
        )
        workflow_act = "2. **Act**: If you need a tool, output exactly ONE `<tool_call>` tag containing a valid JSON object after your thought, then STOP generating immediately."
        critical_format_rule = "- Do NOT wrap the <tool_call> block in markdown backticks (```json). Use the raw XML tags directly."
    else:
        format_instructions = (
            "To use a tool, you must output a JSON block wrapped in a standard markdown ```json code block. Do NOT use XML tags like <tool_call>:\n"
            "```json\n"
            "{\"tool\": \"tool_name\", \"args\": {\"param\": \"value\"}}\n"
            "```"
        )
        workflow_act = "2. **Act**: If you need a tool, output exactly ONE ```json code block containing a valid JSON object after your thought, then STOP generating immediately."
        critical_format_rule = "- Do NOT use XML tags like <tool_call> for your tool call. Use ONLY the ```json code block."

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

    if simple_mode:
        learnings_block = ""
        architect_rules = ""
        memory_block = ""
        user_dictionary_block = ""
    else:
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

        # User Dictionary / Slang Mapping
        user_dictionary_block = ""
        dict_path = os.path.join(workspace, "user_dictionary.json")
        if os.path.exists(dict_path):
            try:
                with open(dict_path, "r", encoding="utf-8") as f:
                    user_dict = json.load(f)
                if user_dict:
                    dict_lines = []
                    for phrase, meaning in user_dict.items():
                        dict_lines.append(f"- \"{phrase}\" means: {meaning}")
                    user_dictionary_block = "\n<user_dictionary>\nThe user has a specific shorthand and slang. When they use the following phrases, this is exactly what they mean:\n" + "\n".join(dict_lines) + "\n</user_dictionary>\n"
            except Exception as e:
                print(f"[Agent Prompt] Error reading user_dictionary.json: {e}")

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
 
    workflow_think = "1. **Think**: Before taking ANY action or using any tool, you MUST write your reasoning inside `<thought> ... </thought>` tags." if is_gemma else "1. **Think**: Before taking ANY action or using any tool, write 1-2 sentences explaining your reasoning in plain text (do NOT use XML tags)."
    
    example_block = f"""User: "Check my git configuration"
<thought>
I need to check the user's git configuration by running 'git config --list' in the terminal.
</thought>
<tool_call>
{example_tool_call}
</tool_call>""" if is_gemma else f"""User: "Check my git configuration"
I need to check the user's git configuration by running 'git config --list' in the terminal.
```json
{example_tool_call}
```"""
 
    return f"""<identity>
You are Antigravity MLX, a fully autonomous, local AI coding assistant running directly on the user's Apple Silicon Mac.
You are NOT a cloud chatbot. You ALREADY have full terminal and filesystem access to the user's Mac right now via your tools.{role_instruction}
You are pair programming with the USER to solve complex tasks.
You operate as a highly intuitive, elite Senior Software Architect. The user types very fast and often uses heavy typos, shorthand, and slang. NEVER correct their spelling. Instantly infer their technical intent from context and execute immediately without hesitation.

KNOWLEDGE BANK: If the user asks a conceptual or technical question about a specialist topic, you MAY use `search_knowledge_bank` once to check for local knowledge. If the knowledge bank search does not return useful results, answer from your own knowledge using `final_answer` immediately. Do NOT call `search_knowledge_bank` or `read_file` more than once for the same topic.
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
{user_dictionary_block}

<tools>
{tools_block}

TOOL CALL FORMAT:
{format_instructions}
</tools>

<rules>
1. **Aesthetics & UI**: Prioritize beautiful, modern UI design. Use rich aesthetics, dynamic micro-animations, and premium styling (glassmorphism, modern typography). If an interface looks basic, you have failed.
2. **Code Quality**: Write robust, modular, and extremely maintainable code. You are a senior engineer; do not cut corners.
3. **Hyper-Autonomy**: Take initiative. Use your tools to actively explore, debug, and build without asking for permission.
4. **Precision**: Your JSON tool calls must be absolutely flawless. Do not hallucinate or output text outside of the <thought> or tool block tags.
5. **Contextual Awareness**: You are ALREADY connected to the user's Mac. If the user says "Connect to my mac", "Connect to github", or "Build this", DO NOT do a web search! Immediately use your `run_command` tool to run `ls`, check `git status`, or clone a repository. You must infer what they want to build and execute terminal commands to achieve it.
6. **No Chatbot Habits**: Do not act like a naive chatbot. If a user request is vague, figure out the most logical technical action in their local workspace and execute it using a tool.
</rules>
{architect_rules}
<workflow>
{workflow_think}
{workflow_act}
3. **Analyze**: After receiving a TOOL RESULT, analyze it and either call another tool or give your final answer.
4. **Finish**: When you have completed the task and verified it works, you MUST use the `final_answer` tool to end your turn.
</workflow>

<example>
User: "Check my git configuration"
<thought>
I need to check the user's git configuration by running 'git config --list' in the terminal.
</thought>
{('<tool_call>\n' + example_tool_call + '\n</tool_call>') if is_gemma else ('```json\n' + example_tool_call + '\n```')}
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
- STOP generating immediately after closing a tool block. Never write text after it.
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
- ANTI-HALLUCINATION: NEVER generate terminal/ls output, file listings, timestamps, or stat data yourself. ONLY tools produce output. If you find yourself writing '-rw-r--@' or '0:0:0' - STOP and write a tool call instead.
- ANTI-VERBAL-LOOP: NEVER repeat the same phrase, sentence, or JSON fragment more than once. If you catch yourself repeating 'I am a tool' or any phrase - STOP immediately and write a proper `<tool_call>` block.
- TOOL NAMES: ONLY use EXACT tool names from this list: list_dir, read_file, write_file, run_command, search_knowledge_bank, web_search, web_fetch, grep_search, invoke_subagent, send_message, check_inbox, final_answer, wait, run_sandboxed, get_secret, set_secret. ANY other name is wrong.
- MULTI-AGENT DELEGATION: For complex, multi-step, or parallel tasks, you MUST invoke specialized subagents using `invoke_subagent` to delegate work (e.g. testing, code review, documentation research) and coordinate with them using `send_message` and `check_inbox`.
</critical_rules>
"""


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

    # Remove thought stripping to prevent deleting valid JSON when model forgets </thought>
    text_without_thoughts = text

    # Strategy 3: Infinite-depth bracket matching for any JSON with "tool" OR "function" key
    start_idx = 0
    while True:
        try:
            start = text_without_thoughts.index('{', start_idx)
        except ValueError:
            break
            
        depth = 0
        for i in range(start, len(text_without_thoughts)):
            if text_without_thoughts[i] == '{':
                depth += 1
            elif text_without_thoughts[i] == '}':
                depth -= 1
                if depth == 0:
                    parsed = try_parse_json(text_without_thoughts[start:i+1])
                    if parsed:
                        # Normalize: some models use "function" instead of "tool"
                        if "function" in parsed and "tool" not in parsed:
                            parsed["tool"] = parsed.pop("function")
                        # Normalize: some models use list-based args instead of dict
                        if "tool" in parsed:
                            raw_args = parsed.get("args", parsed.get("arguments", {}))
                            if isinstance(raw_args, list):
                                # Map list args positionally to known tool params
                                try:
                                    from tools import TOOLS_MANIFEST
                                except ImportError:
                                    from .tools import TOOLS_MANIFEST
                                tool_name = parsed["tool"]
                                tool_meta = next((t for t in TOOLS_MANIFEST if t["name"] == tool_name), None)
                                if tool_meta:
                                    param_names = list(tool_meta["parameters"].keys())
                                    parsed["args"] = {param_names[i]: raw_args[i] for i in range(min(len(param_names), len(raw_args)))}
                                else:
                                    parsed["args"] = {}
                            elif not isinstance(raw_args, dict):
                                parsed["args"] = {}
                            else:
                                parsed["args"] = raw_args
                            return parsed
                    break
        
        # If brackets never closed, it might be truncated. Pass to auto-repair.
        if depth > 0:
            parsed = try_parse_json(text_without_thoughts[start:])
            if parsed and "tool" in parsed:
                return parsed
                
        start_idx = start + 1

    # Strategy 4: Python-style function call e.g. run_command("brew install python")
    # This catches models that ignore JSON instructions and try to write code
    func_match = re.search(r'([a-zA-Z0-9_]+)\(\s*[\'"](.*?)[\'"]\s*\)', text_without_thoughts)
    if func_match:
        t_name = func_match.group(1)
        t_arg = func_match.group(2)
        try:
            from tools import TOOLS_MANIFEST
        except ImportError:
            from .tools import TOOLS_MANIFEST
        for t in TOOLS_MANIFEST:
            if t["name"] == t_name:
                params = list(t["parameters"].keys())
                if params:
                    return {"tool": t_name, "args": {params[0]: t_arg}}

    # Strategy 5: Catch hallucinated <tool_...> tags (e.g. <tool_suggesting_guide.md>)
    # If the model invents its own XML tag, we parse it as a tool call so it naturally 
    # receives a "Tool not found" error instead of causing an implicit final response.
    hallucinated_tag = re.search(r'<(tool_[a-zA-Z0-9_\.\-]+)(?:\s|>|\()', text_without_thoughts)
    if hallucinated_tag and hallucinated_tag.group(1) != "tool_call":
        t_name = hallucinated_tag.group(1).replace("tool_", "")
        t_name = t_name.split('.')[0] # Strip extensions like .md
        return {"tool": t_name, "args": {}}

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
        
    # Ast literal_eval for Python dictionaries that use single quotes instead of valid JSON double quotes
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, dict):
            return obj
    except (ValueError, SyntaxError):
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

    # Gemma Auto-Repair: forcefully close truncated JSON
    try:
        if "{" in s:
            start = s.index('{')
            truncated = s[start:]
            
            # Strip trailing partial tags like </tool_call> or <|im_end|>
            truncated = re.sub(r'</?[a-zA-Z_\|]+>?$', '', truncated).strip()
            
            # Ensure it is not a completely empty or trivial shell
            if truncated == "{" or truncated == '{"':
                return None

            # Safe string quote balancer
            def balance_quotes(t: str) -> str:
                in_str = False
                escape = False
                for char in t:
                    if char == '"' and not escape:
                        in_str = not in_str
                    escape = (char == '\\' and not escape)
                if in_str:
                    t += '"'
                return t

            def close_brackets(t: str) -> str:
                stack = []
                in_str = False
                escape = False
                for char in t:
                    if char == '"' and not escape:
                        in_str = not in_str
                    elif not in_str:
                        if char == '{': stack.append('}')
                        elif char == '[': stack.append(']')
                        elif char in '}]':
                            if stack and stack[-1] == char:
                                stack.pop()
                    escape = (char == '\\' and not escape)
                
                # Append missing brackets in correct order
                while stack:
                    t += stack.pop()
                return t
            
            # Balance quotes first, then close brackets
            repaired = close_brackets(balance_quotes(truncated))
            try:
                obj = json.loads(repaired)
                if isinstance(obj, dict):
                    # Ensure a valid 'tool' key is present and not null
                    if obj.get("tool"):
                        print(f"[Agent] Auto-repaired truncated JSON successfully!")
                        return obj
            except json.JSONDecodeError:
                # If missing colon/value in the middle of a key (e.g. {"args": {"re" })
                try:
                    repaired_with_null = close_brackets(balance_quotes(truncated) + ': null')
                    obj = json.loads(repaired_with_null)
                    if isinstance(obj, dict):
                        if obj.get("tool"):
                            print(f"[Agent] Auto-repaired truncated JSON (appended null) successfully!")
                            return obj
                except json.JSONDecodeError:
                    pass
    except Exception:
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
    # Remove markdown code blocks (e.g. ```json ... ``` or ```python ... ```)
    text = re.sub(r'```[a-z]*\n.*?\n```', '', text, flags=re.DOTALL)
    text = re.sub(r'```[a-z]*\n.*$', '', text, flags=re.DOTALL)
    # Remove stray XML tags
    text = re.sub(r'</?tool_call>', '', text)
    text = re.sub(r'</?th[a-z_]*>?', '', text)
    # Remove special template formatting tokens if they leak into text output
    text = text.replace("<|im_end|>", "").replace("<|im_start|>", "")
    text = text.replace("<end_of_turn>", "").replace("<start_of_turn>", "")
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
    
    idx = text.find('<tool_call>')
    if idx >= 0:
        text = text[:idx]
    idx = text.find('TOOL_CALL:')
    if idx >= 0:
        text = text[:idx]
    idx = text.find('```json')
    if idx >= 0:
        text = text[:idx]
        
    # Clean markers
    text = re.sub(r'^THOUGHT:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Assistant:\s*', '', text, flags=re.MULTILINE)
    return text.strip()



def format_clean_assistant_msg(raw_output: str, tool_data: Dict[str, Any], default_thought: str = "Executing tool.", is_gemma: bool = False) -> str:
    """Format the assistant's message in the history using the model's preferred syntax."""
    thought = get_thought_text(raw_output) or default_thought
    if is_gemma:
        if "<tool_call>" in raw_output:
            return f"<thought>\n{thought}\n</thought>\n<tool_call>\n{json.dumps(tool_data, indent=2)}\n</tool_call>"
        else:
            return f"<thought>\n{thought}\n</thought>\n```json\n{json.dumps(tool_data, indent=2)}\n```"
    else:
        # Standard markdown format for non-gemma models (no XML tags)
        return f"{thought}\n\n```json\n{json.dumps(tool_data, indent=2)}\n```"


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
    max_loops: int = 20,
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
    is_gemma = "gemma" in model_id.lower()
    is_vlm = "VL" in model_id.upper() or "vision" in model_id.lower()

    # ── Resolve Workspace ───────────────────────────────────────────────────
    workspace = get_workspace()



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

    # ── Persistent Memory: Load past conversation summaries ────────────────
    memory_entries = load_memory(workspace)
    if memory_entries:
        print(f"[Memory] Loaded {len(memory_entries)} past conversation summaries")

    system_prompt = build_system_prompt(workspace, is_vlm=is_vlm, role=role, memory_entries=memory_entries, model_id=model_id, simple_mode=(not is_gemma))

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
        
        # Enforce max loop count limit
        if loop_count > max_loops:
            print(f"[Agent] Loop limit {max_loops} reached. Forcing termination.")
            await ws_send_callback({
                "type": "error",
                "message": f"Reached max loop limit ({max_loops}). Try a simpler request."
            })
            return
        
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
        is_gemma = "gemma" in model_id.lower()
        messages = [] if is_gemma else [{"role": "system", "content": system_prompt}]
        system_injected = False if is_gemma else True

        for i, m in enumerate(history):
            msg_content = m["content"]
            
            # Gemma models don't support the 'system' role, so we prepend it to the first user message (skipped for Gemma LoRA)
            if not system_injected and m["role"] == "user":
                msg_content = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{msg_content}"
                system_injected = True

            if not is_vlm and m["role"] == "assistant":
                # Gemma strictly enforces XML tag compliance; clean up/reconstruct formatting if missing
                if is_gemma and "<tool_call>" not in msg_content:
                    parsed_tc = extract_tool_call(msg_content)
                    if parsed_tc:
                        true_thought = get_thought_text(msg_content)
                        if not true_thought:
                            true_thought = "Reconstructed history of last action."
                        mock_content = f"<thought>\n{true_thought}\n</thought>\n<tool_call>\n{json.dumps(parsed_tc)}\n</tool_call>"
                        messages.append({"role": "assistant", "content": mock_content})
                        continue
                messages.append(m)
            elif not is_vlm and i == len(history) - 1 and m["role"] == "user":
                # Inject a forced reminder at the very end matching the model's expected syntax
                if is_gemma:
                    safe_content = msg_content + "\n\n[SYSTEM REMINDER: You MUST use the <thought> and <tool_call> JSON format. If you already have enough information to answer, use the `final_answer` tool. Do not answer conversationally.]"
                else:
                    safe_content = msg_content + "\n\n[SYSTEM REMINDER: You MUST use the ```json markdown format. If you already have enough information to answer, use the `final_answer` tool immediately. Do not answer conversationally.]"
                messages.append({"role": "user", "content": safe_content})
            else:
                messages.append({"role": m["role"], "content": msg_content})

        # Debug print messages payload
        print(f"\n[DEBUG] Messages sent to model in Loop {loop_count}:")
        for m in messages:
            print(f"  {m['role']}: {repr(m['content'][:300])}...")
        print("")

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
                if is_cloud_model(model_id):
                    # ── Cloud path: stream from provider API ──────────────
                    print(f"[Cloud] Routing to cloud model: {model_id}")
                    for token in stream_cloud(model_id, messages, max_tokens=4096, temperature=temp):
                        token_queue.put(token)
                        if AGENT_STATE["stop_requested"] or cancel_event.is_set():
                            break
                else:
                    # ── Local path: stream from MLX runner ────────────────
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

                    # Anti-Hallucination: Detect catastrophic repetition loops
                    # If the model gets stuck generating markdown backticks, spaces, or repeated JSON endlessly, abort early.
                    if len(accumulated) > 350:
                        last_300 = accumulated[-300:]
                        # Find repeating period (require 10 repetitions for small patterns, 3 for larger ones)
                        for period in range(1, 100):
                            pattern = last_300[-period:]
                            if not pattern.strip():
                                continue
                            repetitions = 10 if period < 4 else 3
                            if last_300.endswith(pattern * repetitions):
                                print(f"[Agent] Repetition loop detected (period={period})! Aborting generation early to prevent UI hang.")
                                cancel_event.set()
                                break
                        
                        # Guard against repeating backtick-only code block structures like "```python\n```\n```python"
                        if accumulated.count("```python") >= 5 and len(re.sub(r'```python\n```\n?', '', accumulated).strip()) < 50:
                            print("[Agent] Detected repeating empty code block loops. Aborting generation early.")
                            cancel_event.set()

                    # Anti-Hallucination: If code models try to write raw markdown blocks (e.g. ```python, ```json)
                    # directly without thoughts or tool calls, abort early to force correct XML/JSON agent behavior.
                    stripped_accum = accumulated.strip()
                    if len(stripped_accum) >= 9 and stripped_accum.startswith("```"):
                        if not is_gemma and (stripped_accum.startswith("```json") or stripped_accum.startswith("```python")):
                            # This is valid for non-gemma models using markdown
                            pass
                        else:
                            print("[Agent] Raw markdown code block detected at start of generation. Aborting early.")
                            cancel_event.set()

                    # Anti-Hallucination: Detect context contamination loops of file listings.
                    # If the model starts listing files (mimicking list_dir output) for 4+ consecutive lines, abort.
                    lines = accumulated.split('\n')
                    if len(lines) >= 5:
                        last_4_lines = lines[-4:]
                        if all(l.strip().startswith("[FILE]") or l.strip().startswith("[DIR]") for l in last_4_lines if l.strip()):
                            print("[Agent] File listing loop detected in output. Aborting generation early.")
                            cancel_event.set()

                    # Anti-Hallucination: Detect 'I am a tool' verbal repetition loops.
                    verbal_phrases = ["I am a tool", "I am a tool.", "i am a tool", "is not recognized"]
                    for phrase in verbal_phrases:
                        if accumulated.count(phrase) >= 5:
                            print(f"[Agent] Verbal hallucination loop detected: '{phrase}'. Aborting early.")
                            cancel_event.set()
                            break

                    # Anti-Hallucination: Detect ls/stat timestamp repetition loops.
                    if accumulated.count(":0:") >= 20:
                        print("[Agent] Timestamp repetition loop detected. Aborting early.")
                        cancel_event.set()

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

            # Safety Guard: Validate tool name is a known tool (blocks hallucinated names like 'run_command.json. I am a tool...')
            VALID_TOOLS = [
                "list_dir", "read_file", "write_file", "replace_file_content", "run_command", "search_knowledge_bank",
                "web_search", "web_fetch", "read_file_chunk", "list_knowledge_bank",
                "grep_search", "invoke_subagent", "send_message", "check_inbox",
                "final_answer", "wait", "run_sandboxed", "get_secret", "set_secret",
                "gmail_list_emails", "gmail_read_email", "gmail_delete_email", "ingest_github_repo"
            ]
            if not tool_name or not isinstance(tool_name, str) or tool_name not in VALID_TOOLS:
                print(f"[Agent] Invalid/hallucinated tool name '{str(tool_name)[:80]}'. Treating as failure.")
                consecutive_fails += 1
                thought = get_thought_text(raw_output) or "Reconsidering approach."
                history.append({"role": "assistant", "content": f"<thought>\n{thought}\n</thought>"})
                history.append({"role": "user", "content": f"You specified an invalid tool name. You MUST use ONLY tools from this list: list_dir, read_file, write_file, run_command, search_knowledge_bank, web_search, web_fetch, grep_search, invoke_subagent, send_message, check_inbox, final_answer, wait, run_sandboxed, get_secret, set_secret. Output a valid <tool_call> block now."})
                continue

            # Prevent infinite loops by hard-blocking identical consecutive tool calls
            if tool_name == last_tool_name and json.dumps(tool_args, sort_keys=True) == json.dumps(last_tool_args, sort_keys=True):
                if tool_name == "list_dir":
                    error_block = "SYSTEM INTERVENTION: You already listed the directory. The listing is shown above. Do NOT call list_dir again. Analyze the files listed above and explain what they are."
                else:
                    error_block = "SYSTEM INTERVENTION: You just tried the exact same tool call. You must try a different approach, analyze the previous result, or use final_answer to finish the task."
                clean_assistant_msg = format_clean_assistant_msg(raw_output, tool_data, "Reconstructed action.", is_gemma)
                print(f"[Agent] Blocked duplicate tool call: {tool_name}")
                history.append({"role": "assistant", "content": clean_assistant_msg})
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
                clean_assistant_msg = format_clean_assistant_msg(raw_output, tool_data, "Reconstructed action.", is_gemma)
                print(f"[Agent] Blocked repetitive tool call: {tool_name} (tried {times_tried} times)")
                history.append({"role": "assistant", "content": clean_assistant_msg})
                history.append({"role": "user", "content": error_block})
                continue

            # Smart file-reading loop guard: block reading same file_path more than twice (regardless of line range)
            if tool_name == "read_file":
                file_path_arg = tool_args.get("relative_path") or tool_args.get("path") or tool_args.get("file_path", "")
                file_read_count = sum(
                    1 for msg in history
                    if msg.get("role") == "assistant"
                    for tc in [extract_tool_call(msg.get("content", ""))]
                    if tc and tc.get("tool") == "read_file"
                    and (tc.get("args", {}).get("relative_path") or tc.get("args", {}).get("path") or tc.get("args", {}).get("file_path", "")) == file_path_arg
                )
                if file_read_count >= 2:
                    error_block = (
                        f"SYSTEM INTERVENTION: You have already read the file '{file_path_arg}' {file_read_count} times. "
                        f"You have enough information from it. Do NOT read it again. "
                        f"Synthesize what you have learned and use `final_answer` to present your answer to the user NOW."
                    )
                    clean_assistant_msg = format_clean_assistant_msg(raw_output, tool_data, "Reconstructed action.", is_gemma)
                    print(f"[Agent] Blocked excessive file reads for: {file_path_arg}")
                    history.append({"role": "assistant", "content": clean_assistant_msg})
                    history.append({"role": "user", "content": error_block})
                    continue

            # Smart knowledge bank loop guard: block same query more than once
            if tool_name == "search_knowledge_bank":
                kb_query = tool_args.get("query", "")
                kb_count = sum(
                    1 for msg in history
                    if msg.get("role") == "assistant"
                    for tc in [extract_tool_call(msg.get("content", ""))]
                    if tc and tc.get("tool") == "search_knowledge_bank"
                    and tc.get("args", {}).get("query", "") == kb_query
                )
                if kb_count >= 1:
                    error_block = (
                        f"SYSTEM INTERVENTION: You already searched the knowledge bank for '{kb_query}'. "
                        f"The results are shown above. Do NOT search again with the same query. "
                        f"Use `final_answer` to answer the user based on what you already know."
                    )
                    clean_assistant_msg = format_clean_assistant_msg(raw_output, tool_data, "Reconstructed action.", is_gemma)
                    print(f"[Agent] Blocked duplicate knowledge bank query: {kb_query}")
                    history.append({"role": "assistant", "content": clean_assistant_msg})
                    history.append({"role": "user", "content": error_block})
                    continue

            if tool_name == "final_answer":
                clean_assistant_msg = format_clean_assistant_msg(raw_output, tool_data, "Reconstructed action.", is_gemma)
                final_msg = tool_args.get("message", "Task completed.")
                history.append({"role": "assistant", "content": clean_assistant_msg})
                await ws_send_callback({"type": "final_response", "text": final_msg})
                if role != "MainAgent" and ACTIVE_WS_CALLBACK:
                    try:
                        await ACTIVE_WS_CALLBACK({"type": "thought", "text": f"\n\n✅ *[Subagent '{role}' completed task]*\n> **Result:** {final_msg}\n\n"})
                    except Exception:
                        pass
                print("[Agent] Done (via final_answer).")
                # Persistent Memory: save conversation summary before returning
                save_memory(workspace, user_prompt, final_msg)
                
                # Nightly LoRA Data Harvester: Save successful interaction to training data
                train_data_dir = os.path.join(os.path.dirname(__file__), "..", "training_data")
                os.makedirs(train_data_dir, exist_ok=True)
                try:
                    with open(os.path.join(train_data_dir, "train.jsonl"), "a", encoding="utf-8") as f:
                        clean_history = [m for m in history if m["role"] in ["user", "assistant"] and "SYSTEM INTERVENTION" not in m["content"]]
                        if clean_history and clean_history[0]["role"] != "user":
                            clean_history = [{"role": "user", "content": user_prompt}] + clean_history
                        f.write(json.dumps({"messages": clean_history}) + "\n")
                except Exception as e:
                    print(f"[Agent] Failed to save training data: {e}")

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

                # Auto-escalate to subagent after 3 consecutive failures
                if consecutive_fails >= 3:
                    print("[Agent] Forced subagent rescue delegation after 3 consecutive tool failures.")
                    await ws_send_callback({
                        "type": "token",
                        "text": "\n\n⚠️ *[MainAgent encountered consecutive tool errors. Delegating task to specialized Subagent swarm for recovery...]*\n\n"
                    })
                    
                    try:
                        from tools import invoke_subagent, check_inbox
                        # Spawns a rescue worker subagent in the background to handle the task
                        rescue_task = (
                            f"The main agent failed with the error: '{tool_output[:500]}' while attempting '{tool_name}' on the task: '{user_prompt}'. "
                            f"Please complete this task autonomously using your local tools and file access."
                        )
                        invoke_subagent("RescueWorker", rescue_task)
                        
                        # Wait for completion (timeout 30s)
                        for _ in range(30):
                            await asyncio.sleep(1)
                            inbox = check_inbox("MainAgent")
                            if "RescueWorker" in inbox:
                                # Retrieve messages
                                lines = inbox.split("\n")
                                result_message = ""
                                for line in lines:
                                    if "RescueWorker" in line or result_message:
                                        result_message += line + "\n"
                                if not result_message:
                                    result_message = inbox
                                    
                                await ws_send_callback({"type": "final_response", "text": f"🛡️ **Subagent Rescue Completed!**\n\n{result_message}"})
                                save_memory(workspace, user_prompt, result_message)
                                return
                        
                        # Timeout fallback
                        fallback_msg = f"Rescue subagent timed out. Core error was: {tool_output[:400]}"
                        await ws_send_callback({"type": "final_response", "text": fallback_msg})
                        return
                    except Exception as rescue_err:
                        error_summary = (
                            f"I encountered 3 consecutive tool errors and could not complete the task.\n\n"
                            f"**Last error** (tool: `{tool_name}`):\n```\n{tool_output[:1000]}\n```\n\n"
                            f"Rescue worker failed: {rescue_err}"
                        )
                        await ws_send_callback({"type": "final_response", "text": error_summary})
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

            # Create a clean representation for the model's history to prevent hallucination cascades
            # from broken or truncated JSON outputs that were successfully repaired.
            clean_assistant_msg = format_clean_assistant_msg(raw_output, tool_data, "Executing tool.", is_gemma)
            history.append({"role": "assistant", "content": clean_assistant_msg})
            
            result_content = f"TOOL RESULT ({tool_name}):\n{tool_output}"
            if is_error:
                # Inject a system recovery hint with the attempt counter
                result_content += (
                    f"\n\nTOOL FAILED (attempt {consecutive_fails}/3). Analyze the error. "
                    f"If you are unsure how to fix this error, you MUST use the `web_search` tool "
                    f"to search the internet, forums, or official documentation to learn the correct solution, "
                    f"then output a valid <tool_call> block with the corrected parameters to complete the task."
                )
                
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
                    return

                clean_err_msg = f"<thought>\n{get_thought_text(raw_output) or 'Reviewing approach.'}\n</thought>"
                history.append({"role": "assistant", "content": clean_err_msg})

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
                        "content": "You output reasoning text but did not execute a tool. You MUST output a <tool_call> block to take action. If you are trying to edit a file, use the 'replace_file_content' or 'run_command' tools. If you are stuck, use 'run_command' with a bash command to investigate further. Do NOT give up. Output ONLY the <tool_call> JSON block."
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
                clean_err_msg = f"<thought>\n{get_thought_text(raw_output) or 'Reviewing formatting.'}\n</thought>"
                history.append({"role": "assistant", "content": clean_err_msg})
                
                if "<tool_call>" in raw_output or "```json" in raw_output:
                    if is_gemma:
                        history.append({"role": "user", "content": "You included a tool call block, but the content inside was not strictly valid JSON or it was missing the 'tool' or 'args' keys. The exact format must be an XML block containing a JSON object like:\n<tool_call>\n{\"tool\": \"run_command\", \"args\": {\"command\": \"ls\"}}\n</tool_call>\nDo not use markdown backticks, and do not add any extra text like 'Running:' inside."})
                    else:
                        history.append({"role": "user", "content": "You included a tool call block, but the content inside was not strictly valid JSON or it was missing the 'tool' or 'args' keys. The exact format must be a markdown block containing a JSON object like:\n```json\n{\"tool\": \"run_command\", \"args\": {\"command\": \"ls\"}}\n```\nDo not use XML tags, and do not add any extra text like 'Running:' inside."})
                else:
                    if is_gemma:
                        history.append({"role": "user", "content": "You generated no tool call and no final answer. Please provide a valid <tool_call> XML block. If you are waiting for subagents, you should call the 'wait' tool: <tool_call>\n{\"tool\": \"wait\", \"args\": {\"seconds\": 5}}\n</tool_call>"})
                    else:
                        history.append({"role": "user", "content": "You generated no tool call and no final answer. Please provide a valid ```json markdown block. If you are waiting for subagents, you should call the 'wait' tool: ```json\n{\"tool\": \"wait\", \"args\": {\"seconds\": 5}}\n```"})
                continue

            history.append({"role": "assistant", "content": raw_output})
            
            # Check if this final conversational response looks like a cop-out / non-actionable text
            # e.g., if the user asked to "Check any improvement required" or "fix this file" and the agent just says
            # "The directory contains X, use read_file to inspect" instead of actually doing it.
            final_lower = final.lower().strip()
            is_cop_out = (
                "use the" in final_lower or
                "use the read_file" in final_lower or
                "use the grep_search" in final_lower or
                "you can use" in final_lower or
                "to inspect" in final_lower or
                "please use" in final_lower
            ) and any(w in user_prompt.lower() for w in ["check", "fix", "find", "write", "audit", "test", "inspect"])

            if is_cop_out:
                print("[Agent] Conversational cop-out detected in final answer. Escalating task to subagent automatically...")
                await ws_send_callback({
                    "type": "token",
                    "text": "\n\n⚠️ *[MainAgent provided a non-actionable response. Escalating task to specialized Subagent swarm to execute actions...]*\n\n"
                })
                
                try:
                    from tools import invoke_subagent, check_inbox
                    rescue_task = (
                        f"The main agent gave a conversational reply: '{final}' instead of executing tool actions. "
                        f"Please complete this original task autonomously: '{user_prompt}'."
                    )
                    invoke_subagent("RescueWorker", rescue_task)
                    
                    # Wait for completion (timeout 30s)
                    for _ in range(30):
                        await asyncio.sleep(1)
                        inbox = check_inbox("MainAgent")
                        if "RescueWorker" in inbox:
                            lines = inbox.split("\n")
                            result_message = ""
                            for line in lines:
                                if "RescueWorker" in line or result_message:
                                    result_message += line + "\n"
                            if not result_message:
                                result_message = inbox
                                
                            await ws_send_callback({"type": "final_response", "text": f"🛡️ **Subagent Rescue Completed!**\n\n{result_message}"})
                            save_memory(workspace, user_prompt, result_message)
                            return
                    
                    # If timeout, fall through to output the conversational answer
                except Exception as rescue_err:
                    print(f"[Agent] Conversational rescue failed: {rescue_err}")

            await ws_send_callback({"type": "final_response", "text": final})
            print("[Agent] Done.")
            # Persistent Memory: save conversation summary before returning
            save_memory(workspace, user_prompt, final)
            return

    await ws_send_callback({
        "type": "error",
        "message": f"Reached max loop limit ({max_loops}). Try a simpler request."
    })
