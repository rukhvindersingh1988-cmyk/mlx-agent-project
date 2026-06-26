import asyncio
import json
from backend.agent import run_agent_loop
import sys
import os

async def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
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
        print(f"\n======================================", flush=True)
        print(f"PROMPT {i+1}: {p}", flush=True)
        print(f"======================================", flush=True)
        
        history.append({"role": "user", "content": p})
        
        async def callback(packet):
            t = packet.get("type")
            if t == "thought":
                sys.stdout.write(packet.get("text", ""))
                sys.stdout.flush()
            elif t == "tool_start":
                print(f"\n[Tool Execution] {packet.get('name')} with args {packet.get('args')}", flush=True)
            elif t == "final_response":
                print(f"\n[Final Response] {packet.get('text')}", flush=True)
                history.append({"role": "assistant", "content": packet.get("text")})
            elif t == "error":
                print(f"\n[Error] {packet.get('message')}", flush=True)

        await run_agent_loop(
            user_prompt=p,
            model_id=model_id,
            ws_send_callback=callback,
            history=history[:-1]
        )
        
        print(f"\n--- DONE WITH PROMPT {i+1} ---", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
