import sys, time, os
sys.path.insert(0, 'backend')

# Direct in-process test of _subagent_thread_runner
from agent import extract_tool_call
from cloud_runner import stream_cloud, is_cloud_model
from tools import execute_tool, TOOLS_MANIFEST

active_model_id = "groq/llama-3.3-70b"

system_prompt = (
    "You are an expert AI Subagent with the role: CodeArchitect. You assist the main agent by performing real tasks.\n\n"
    "You have direct access to the user's local filesystem and terminal.\n"
    "To create or write a file, output ONLY this JSON block and nothing else:\n\n"
    "```json\n"
    "{\n"
    "  \"function\": \"write_file\",\n"
    "  \"args\": [\"relative/path/to/file.py\", \"file content here\"]\n"
    "}\n"
    "```\n\n"
    "IMPORTANT: Output ONLY the JSON block. No explanations before or after."
)

task = "Write a CLI task manager to user_projects/task_manager.py with HIGH/MEDIUM/LOW priority, ANSI colors, and JSON persistence."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": task}
]

response_text = ""
print("Calling Groq...")
for chunk in stream_cloud(active_model_id, messages, max_tokens=3000, temperature=0.2):
    response_text += chunk

print("Response (first 200 chars):", response_text[:200])
print()

tool_data = extract_tool_call(response_text)
print("PARSED TOOL DATA:", tool_data)

if tool_data and "tool" in tool_data:
    tname = tool_data["tool"]
    targs = tool_data.get("args", {})
    print(f"Executing tool: {tname}")
    result = execute_tool(tname, targs)
    print("TOOL RESULT:", result)
    print("FILE EXISTS:", os.path.exists("user_projects/task_manager.py"))
else:
    print("No tool parsed from model response.")
