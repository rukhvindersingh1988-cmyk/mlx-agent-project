import asyncio
import json
import sys
import os

# Adjust path to find backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import run_agent_loop

async def main():
    prompt = "Use the 'run_command' tool to delete these GitHub repositories: 'tata_master_bot', 'AutoCode', 'call-crm-project', and 'rukhvinder'. Do NOT delete 'mlx-agent-project'. Use the command 'gh repo delete <repo-name> --yes' to delete each one. Format the summary of deleted repositories as a list and present it using final_answer."
    model_id = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
    history = []
    
    print(f"\n==================================================")
    # Highlight model and prompt
    print(f"Testing Local AI Model: {model_id}")
    print(f"User Prompt: '{prompt}'")
    print(f"==================================================\n")
    
    async def callback(packet):
        t = packet.get("type")
        if t == "thought":
            sys.stdout.write(packet.get("text", ""))
            sys.stdout.flush()
        elif t == "tool_start":
            print(f"\n\n⚙️  [Tool Start] Calling tool '{packet.get('name')}' with args: {packet.get('args')}")
        elif t == "tool_end":
            print(f"✅ [Tool End] Tool execution succeeded.")
        elif t == "tool_error":
            print(f"❌ [Tool Error] Tool execution failed.")
        elif t == "final_response":
            print(f"\n\n🏁 [Final Response]:\n{packet.get('text')}\n")
        elif t == "error":
            print(f"\n❌ [Backend Error] {packet.get('message')}")

    try:
        await run_agent_loop(
            user_prompt=prompt,
            model_id=model_id,
            ws_send_callback=callback,
            history=history,
            max_loops=15
        )
    except Exception as e:
        print(f"\n❌ Execution crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
