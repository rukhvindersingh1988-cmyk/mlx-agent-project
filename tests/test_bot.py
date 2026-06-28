import asyncio
import json
from backend.agent import run_agent_loop
import sys
import os

async def mock_ws_sender(packet):
    pass # we can print it if we want

async def main():
    os.chdir("backend") # Make sure tools like read_file resolve paths correctly if they depend on Cwd
    os.chdir("..")
    
    # We will test 5 prompts sequentially
    prompts = [
        "What is 2+2?",
        "List the contents of the current directory.",
        "Invoke a subagent named 'MathBot' to calculate the square root of 144.",
        "Check your inbox for MathBot's response.",
        "Create a new file called 'test_hello.txt' with the content 'Hello World'."
    ]
    
    model_id = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
    history = []
    
    for i, p in enumerate(prompts):
        print(f"\n======================================")
        print(f"PROMPT {i+1}: {p}")
        print(f"======================================")
        
        # Append user prompt to history
        history.append({"role": "user", "content": p})
        
        async def callback(packet):
            t = packet.get("type")
            if t == "thought":
                sys.stdout.write(packet.get("text", ""))
                sys.stdout.flush()
            elif t == "tool_start":
                print(f"\n[Tool Execution] {packet.get('name')} with args {packet.get('args')}")
            elif t == "tool_end":
                pass
            elif t == "final_response":
                print(f"\n[Final Response] {packet.get('text')}")
                history.append({"role": "assistant", "content": packet.get("text")})
            elif t == "error":
                print(f"\n[Error] {packet.get('message')}")
        
        await run_agent_loop(
            user_prompt=p,
            model_id=model_id,
            ws_send_callback=callback,
            history=history[:-1] # passing history without the newly appended user message
        )
        
        print("\n--- DONE WITH PROMPT ---")

asyncio.run(main())
