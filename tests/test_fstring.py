def build_prompt():
    return f"""
<example>
User: "Check my git configuration"
<thought>
I need to check the user's git configuration by running 'git config --list' in the terminal.
</thought>
<tool_call>
{{"tool": "run_command", "args": {{"command": "git config --list"}}}}
</tool_call>
</example>
"""
print(build_prompt())
