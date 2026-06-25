import re
import json

def try_parse_json(s: str):
    s = s.strip()
    for prefix in ["```json", "```"]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()

    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

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

def extract_tool_call(text: str):
    xml_match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.DOTALL)
    if xml_match:
        parsed = try_parse_json(xml_match.group(1).strip())
        if parsed:
            return parsed

    # Strategy 4
    func_match = re.search(r'([a-zA-Z0-9_]+)\(\s*[\'"](.*?)[\'"]\s*\)', text)
    if func_match:
        t_name = func_match.group(1)
        t_arg = func_match.group(2)
        print(f"Matched func: {t_name}")
        return {"tool": t_name, "args": {"command": t_arg}} # simplified

    return None

text = """
I sincerely apologize for the continued failures.
I'll attempt to import the `omlx` package directly to see if it's installed correctly and if I can use it.

<tool_call>
[
  "python3 -c \"import onlex; print(onlex.__version__)\""
]
</tool_call>
"""

print(extract_tool_call(text))
