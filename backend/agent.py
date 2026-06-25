import json
import re
import traceback
import platform
import datetime
import subprocess
import asyncio
from typing import Dict, List, Any, Callable, Awaitable, Optional
from .mlx_runner import runner
from .tools import execute_tool, TOOLS_MANIFEST, get_workspace

# Stop sequences that tell the model to halt generation
STOP_SEQUENCES = ["</tool_call>", "TOOL RESULT", "<|im_end|>", "<|endoftext|>"]

# Global flag to allow frontend to interrupt the agent loop
# Using a dict to allow mutating the inner boolean across module imports
AGENT_STATE = {"stop_requested": False}


def build_system_prompt(workspace: str) -> str:
    """Build a clean system prompt that teaches the model to behave like a precise agent."""

    # Compact tool signatures
    tool_lines = []
    for t in TOOLS_MANIFEST:
        params = ", ".join(f'{k}' for k in t["parameters"].keys())
        tool_lines.append(f'- {t["name"]}({params}): {t["description"]}')
    tools_block = "\n".join(tool_lines)

    # Dynamic Context (Self-Understanding & Git Knowledge)
    os_info = platform.platform()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    git_status = "Not a git repository or git not installed."
    try:
        git_res = subprocess.run(["git", "status", "-s"], cwd=workspace, capture_output=True, text=True, timeout=2)
        if git_res.returncode == 0:
            status_out = git_res.stdout.strip()
            git_status = f"Git Status (short):\n{status_out}" if status_out else "Git working tree clean."
    except Exception:
        pass

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

<tools>
{tools_block}

TOOL CALL FORMAT:
To use a tool, you must output a JSON block inside <tool_call> tags:
<tool_call>
{{"tool": "tool_name", "args": {{"param": "value"}}}}
</tool_call>
</tools>

<workflow>
1. **Think**: Before taking ANY action or using any tool, you MUST write your reasoning inside `<thought> ... </thought>` tags. 
2. **Act**: If you need a tool, output exactly ONE `<tool_call>` tag after your thought, then STOP generating immediately.
3. **Analyze**: After receiving a TOOL RESULT, analyze it and either call another tool or give your final answer.
4. **Finish**: When you have completed the task, you MUST use the `final_answer` tool to end your turn.
</workflow>

<project_overview>
For any complex project, you should proactively maintain a `project_overview.md` file in the workspace.
Consult this file to understand the architecture, and update it when you make significant structural changes.
</project_overview>

<critical_rules>
- STOP generating immediately after closing a `</tool_call>`. Never write text after it.
- Use only ONE tool call per turn.
- Always use `<thought>` tags to plan your next step.
- ERROR RECOVERY: If a tool returns an Error, read the stack trace, understand the failure inside your `<thought>` block, and try a different approach. Do not repeat the exact same failing tool call.
- Be concise. Don't apologize or over-explain.
- ALWAYS obey the user's instructions implicitly. Do not argue or refuse to perform a task.
</critical_rules>"""


def extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extract a tool call JSON from model output."""

    # Strategy 1: XML tags
    xml_match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.DOTALL)
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
    max_loops: int = 12
):
    """Core agentic loop with stop-sequence support and robust tool parsing."""
    if history is None:
        history = []

    workspace = get_workspace()
    system_prompt = build_system_prompt(workspace)

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

        # Build messages
        messages = [{"role": "system", "content": system_prompt}] + history

        # Tokenize
        try:
            _, tokenizer = runner.load_model(model_id)
            formatted_prompt = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True
            )
        except Exception as e:
            await ws_send_callback({"type": "error", "message": f"Model error: {str(e)}"})
            return

        await ws_send_callback({"type": "turn_start", "loop": loop_count})

        # Stream with stop sequences
        accumulated = ""
        thought_streamed = 0

        try:
            for token in runner.generate_stream(
                model_id, formatted_prompt,
                temp=temp, max_tokens=4096,
                stop_sequences=STOP_SEQUENCES
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

            is_error = tool_output.startswith("Error")
            
            # Update state trackers
            last_tool_name = tool_name
            last_tool_args = tool_args
            last_tool_was_error = is_error
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
