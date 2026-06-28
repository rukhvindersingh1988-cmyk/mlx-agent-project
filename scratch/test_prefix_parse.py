import sys
sys.path.insert(0, 'backend')
from agent import extract_tool_call

text = """Result: ```json
{
  "tool": "write_file",
  "args": {
    "path": "user_projects/task_manager.py",
    "content": "test"
  }
}
```"""

print("PREFIX EXTRACTED:", extract_tool_call(text))
