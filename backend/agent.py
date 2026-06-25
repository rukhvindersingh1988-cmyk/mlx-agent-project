import os
import json
import re
import traceback
import platform
import datetime
import subprocess
import asyncio
from typing import Dict, List, Any, Callable, Awaitable, Optional
from .mlx_runner import runner, list_downloaded_models
from .tools import execute_tool, TOOLS_MANIFEST, get_workspace

# Stop sequences that tell the model to halt generation
STOP_SEQUENCES = ["</tool_call>", "TOOL RESULT", "<|im_end|>", "<|endoftext|>", "<|im_start|>", "im_end", "<|im_start|>assistant", "<|im_start|>user"]

# Global flag to allow frontend to interrupt the agent loop
# Using a dict to allow mutating the inner boolean across module imports
AGENT_STATE = {"stop_requested": False}

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


def build_system_prompt(workspace: str, is_vlm: bool = False) -> str:
    """Build a clean system prompt that teaches the model to behave like a precise agent."""

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

    return f"""<identity>
You are Antigravity MLX, a powerful agentic AI coding assistant designed to run locally on Apple Silicon.
You are pair programming with a USER to solve their coding task. The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question.
You operate as a Senior AI Software Engineer, maintaining high standards for code quality, beautiful UI design, and robust architecture.
</identity>

<environment>
- OS: {os_info}
- Time: {current_time}
- Workspace: {workspace}
- Git Status: {git_status}
</environment>
{learnings_block}

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
3. **Autonomy**: Take initiative. Use your tools to actively explore, debug, and build without asking for permission for every step.
4. **Precision**: Your JSON tool calls must be absolutely flawless. Do not hallucinate or output text outside of the <thought> or <tool_call> tags.
5. **Context**: You have terminal access via run_command. Use it heavily to compile, run tests, and verify your changes.
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

<project_overview>
For any complex project, you should proactively maintain a `project_overview.md` file in the workspace.
Consult this file to understand the architecture, and update it when you make significant structural changes.
</project_overview>

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
- Always use `<thought>` tags to plan your next step.
- ERROR RECOVERY: If a tool returns an Error, read the stack trace, understand the failure inside your `<thought>` block, and try a different approach. Do not repeat the exact same failing tool call.
- Be concise. Don't apologize or over-explain.
- ALWAYS obey the user's instructions. Do not argue or refuse any task.
- NO LAZINESS: Never truncate code with comments like '# rest of code here' or '... add more'. Always write the full, complete implementation.
- AUTOMATIC TOOL EXECUTION: When the user asks you to do something, just DO it using `<tool_call>`. Never ask "should I run this?" or show a code block and wait. Execute immediately.
- MISSING KNOWLEDGE RECOVERY: If a guide doesn't exist, use `web_search` to find the information, then proceed.
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

    # Fix single quotes
    try:
        obj = json.loads(s.replace("'", '"'))
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
    # Remove <thought> blocks entirely
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    text = re.sub(r'<thought>.*$', '', text, flags=re.DOTALL)
    # Remove THOUGHT: prefixes
    text = re.sub(r'^THOUGHT:\s*', '', text, flags=re.MULTILINE)
    # Remove tool_call blocks entirely
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'TOOL_CALL:\s*\{.*?\}', '', text, flags=re.DOTALL)
    # Remove stray XML tags
    text = re.sub(r'</?tool_call>', '', text)
    text = re.sub(r'</?thought>', '', text)
    # Remove special template formatting tokens if they leak into text output
    text = text.replace("<|im_end|>", "").replace("<|im_start|>", "")
    # Remove leading "Assistant:" if model outputs it
    text = re.sub(r'^Assistant:\s*', '', text, flags=re.MULTILINE)
    # Clean excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_thought_text(text: str) -> str:
    """Extract only the reasoning text inside <thought> tags for UI streaming."""
    # Try to extract from <thought> tags
    match = re.search(r'<thought>(.*?)(?:</thought>|$)', text, flags=re.DOTALL)
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


async def run_agent_loop(
    user_prompt: str,
    model_id: str,
    ws_send_callback: Callable[[Dict[str, Any]], Awaitable[None]],
    history: Optional[List[Dict[str, str]]] = None,
    temp: float = 0.2,
    max_loops: int = 12,
    image_path: Optional[str] = None
):
    """Core agentic loop with stop-sequence support, robust tool parsing, and VLM image support."""
    is_vlm = "VL" in model_id.upper() or "vision" in model_id.lower()
    has_image = bool(image_path and os.path.exists(image_path))

    # ── Smart Model Router ────────────────────────────────────────────────────
    # Silently pick the best available model. Zero user interruption.
    best_model, switch_reason = select_best_model(user_prompt, has_image, model_id)
    if switch_reason:  # Only notify if a switch actually happened
        await ws_send_callback({"type": "model_switched", "model_id": best_model, "reason": switch_reason})
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
    system_prompt = build_system_prompt(workspace, is_vlm=is_vlm)

    history.append({"role": "user", "content": user_prompt})

    consecutive_fails = 0
    last_tool_name = None
    last_tool_args = None
    last_tool_was_error = False

    AGENT_STATE["stop_requested"] = False

    for loop_count in range(1, max_loops + 1):
        if AGENT_STATE["stop_requested"]:
            await ws_send_callback({"type": "error", "message": "Agent execution stopped by user."})
            break

        print(f"[Agent] Loop {loop_count}...")

        # Build messages without mutating history references
        messages = [{"role": "system", "content": system_prompt}]
        for i, m in enumerate(history):
            if not is_vlm and m["role"] == "assistant" and "<thought>" not in m["content"]:
                # The VLM outputs plain text. The Coder model will break character if it sees plain text history.
                # Wrap the plain text in a thought and dummy final_answer so the Coder model stays in agent mode!
                mock_content = f"<thought>\n{m['content']}\n</thought>\n<tool_call>\n{{\"tool\": \"final_answer\", \"args\": {{\"message\": \"{m['content'][:50]}...\"}}}}\n</tool_call>"
                messages.append({"role": "assistant", "content": mock_content})
            elif not is_vlm and i == len(history) - 1 and m["role"] == "user":
                # Inject a forced reminder at the very end
                safe_content = m["content"] + "\n\n[SYSTEM REMINDER: You MUST use the <thought> and <tool_call> JSON format. Do not answer conversationally. Execute a tool.]"
                messages.append({"role": "user", "content": safe_content})
            else:
                messages.append(m)

        # Tokenize
        try:
            _, tokenizer = runner.load_model(model_id)
            if not is_vlm:
                formatted_prompt = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True
                )
            else:
                formatted_prompt = ""
        except Exception as e:
            await ws_send_callback({"type": "error", "message": f"Model error: {str(e)}"})
            return

        await ws_send_callback({"type": "turn_start", "loop": loop_count})

        # Stream with stop sequences
        accumulated = ""
        thought_streamed = 0

        try:
            for token in runner.generate_stream(
                model_id, 
                messages if is_vlm else formatted_prompt,
                temp=temp, max_tokens=4096,
                stop_sequences=STOP_SEQUENCES,
                image_path=image_path if has_image else None
            ):
                if AGENT_STATE["stop_requested"]:
                    break
                    
                accumulated += token

                # Stream thought text in real-time (only the part before tool calls)
                thought = get_thought_text(accumulated)
                if len(thought) > thought_streamed:
                    new_text = thought[thought_streamed:]
                    await ws_send_callback({"type": "thought", "text": new_text})
                    thought_streamed = len(thought)

        except Exception as e:
            print(f"[Agent] Generation error: {e}")
            traceback.print_exc()
            await ws_send_callback({"type": "error", "message": f"Generation error: {str(e)}"})
            return

        raw_output = accumulated.strip()
        print(f"[Agent] Output ({len(raw_output)} chars): {raw_output[:300]}...")

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
            consecutive_fails = 0

            # Prevent infinite error loops by hard-blocking identical consecutive failed tool calls
            if tool_name == last_tool_name and json.dumps(tool_args, sort_keys=True) == json.dumps(last_tool_args, sort_keys=True) and last_tool_was_error:
                error_block = "SYSTEM INTERVENTION: You just tried the exact same tool call and it failed. You must try a different approach or fix the arguments."
                print(f"[Agent] Blocked duplicate failing tool call: {tool_name}")
                history.append({"role": "assistant", "content": raw_output})
                history.append({"role": "user", "content": error_block})
                continue

            if tool_name == "final_answer":
                final_msg = tool_args.get("message", "Task completed.")
                history.append({"role": "assistant", "content": raw_output})
                await ws_send_callback({"type": "final_response", "text": final_msg})
                print("[Agent] Done (via final_answer).")
                return

            await ws_send_callback({
                "type": "tool_start",
                "name": tool_name,
                "args": tool_args
            })

            # Execute
            print(f"[Agent] Running tool: {tool_name}({tool_args})")

            try:
                # Run tool in a separate thread so we don't block the asyncio event loop!
                # This allows the /api/stop endpoint to be processed while a tool is running.
                tool_output = await asyncio.to_thread(execute_tool, tool_name, tool_args)
            except Exception as e:
                tool_output = f"Error: {str(e)}"

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
            
            # Save learnings if error encountered
            if is_error:
                try:
                    learnings_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/agent_learnings.json"
                    learnings_data = {"errors": []}
                    if os.path.exists(learnings_path):
                        with open(learnings_path, "r", encoding="utf-8") as f:
                            learnings_data = json.load(f)
                    # Append new error entry
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

            # Update state trackers
            last_tool_name = tool_name
            last_tool_args = tool_args
            last_tool_was_error = is_error
            consecutive_fails = 0  # Reset consecutive failures on successful tool execution too
            await ws_send_callback({
                "type": "tool_end" if not is_error else "tool_error",
                "name": tool_name,
                "output": tool_output
            })

            # Truncate very long tool outputs for context window management
            if len(tool_output) > 8000:
                tool_output = tool_output[:8000] + "\n... [truncated]"

            # Append to history
            history.append({"role": "assistant", "content": raw_output})
            
            result_content = f"TOOL RESULT ({tool_name}):\n{tool_output}"
            if is_error:
                result_content += "\n\nWARNING: The tool failed. Do not repeat the exact same tool call. Analyze the error and try a different approach or fix your arguments."
                
            history.append({
                "role": "user",
                "content": result_content
            })

        else:
            # No tool call — this is the final answer
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
                    history.append({"role": "user", "content": "You generated no tool call and no final answer. Please provide a valid <tool_call> block or use the final_answer tool."})
                continue

            history.append({"role": "assistant", "content": raw_output})
            await ws_send_callback({"type": "final_response", "text": final})
            print("[Agent] Done.")
            return

    await ws_send_callback({
        "type": "error",
        "message": f"Reached max loop limit ({max_loops}). Try a simpler request."
    })
