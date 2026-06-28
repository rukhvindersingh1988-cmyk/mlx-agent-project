import sys
sys.path.insert(0, 'backend')
from agent import extract_tool_call

text = """```json
{
  "tool": "write_file",
  "args": {
    "path": "user_projects/task_manager.py",
    "content": "test"
  }
}
```"""

print("EXTRACTED:", extract_tool_call(text))
