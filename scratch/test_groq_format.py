import sys
sys.path.insert(0, 'backend')
from agent import extract_tool_call

# Test the exact format Groq model outputs
text = """```json
{
    "function": "write_file",
    "args": [
        "user_projects/task_manager.py",
        "print(1)"
    ]
}
```"""

result = extract_tool_call(text)
print("RESULT:", result)
print("SUCCESS:", result is not None and result.get("tool") == "write_file")
