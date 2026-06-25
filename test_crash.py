import asyncio
from backend.agent import run_agent_loop

async def ws_send(packet):
    pass

async def main():
    try:
        await run_agent_loop("hi...", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit", ws_send)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
