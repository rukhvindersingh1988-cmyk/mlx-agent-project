import sys
sys.path.insert(0, 'backend')
from agent import extract_tool_call
from tools import execute_tool, write_file
import os

# Simulate what Groq outputs
groq_output = """```json
{
  "function": "write_file",
  "args": ["user_projects/task_manager.py", "import json\\nimport os\\nprint('hello')"]
}
```"""

tool_data = extract_tool_call(groq_output)
print("PARSED TOOL DATA:", tool_data)

if tool_data and "tool" in tool_data:
    tname = tool_data["tool"]
    targs = tool_data.get("args", {})
    print(f"Tool: {tname}, Args: {targs}")
    
    # Map write_file args
    if tname == "write_file":
        targs = {
            "relative_path": targs.get("path", targs.get("relative_path", "")),
            "content": targs.get("content", "")
        }
    
    result = execute_tool(tname, targs)
    print("RESULT:", result)
    print("FILE EXISTS?", os.path.exists("user_projects/task_manager.py"))
else:
    print("No tool parsed!")
