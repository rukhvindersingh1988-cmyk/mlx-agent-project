import asyncio
import sys
from backend.agent import run_agent_loop

async def ws_send(packet):
    if packet.get("type") == "agent_output":
        print(f"Agent says: {packet.get('content')}")
    elif packet.get("type") == "tool_call":
        print(f"Agent tool call: {packet}")
    elif packet.get("type") == "error":
        print(f"Error: {packet}")

async def main():
    print("Testing Vision Capabilities rule...")
    await run_agent_loop(
        user_prompt="Here is an image of my terminal error. Can you read it?",
        model_id="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        ws_send_callback=ws_send,
        history=[]
    )

if __name__ == "__main__":
    asyncio.run(main())
