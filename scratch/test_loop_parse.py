import sys
sys.path.insert(0, 'backend')
from agent import extract_tool_call
from cloud_runner import stream_cloud

active_model_id = "groq/llama-3.3-70b"
system_prompt = (
    "You are a Subagent. To write a file, you MUST output a JSON block wrapped in a markdown ```json block. Do not write text before the block. Stop immediately after the block."
    "Available tools:\n- write_file(path, content): Create a new file."
)
task = "Write 'print(1)' to user_projects/task_manager.py"
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": task}
]

response_text = ""
for token_chunk in stream_cloud(active_model_id, messages, max_tokens=2048, temperature=0.2):
    response_text += token_chunk

print("RESPONSE:")
print(response_text)
print("EXTRACTED:", extract_tool_call(response_text))
