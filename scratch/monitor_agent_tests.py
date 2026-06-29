"""
AUTONOMIC MONITORING SUITE:
Spawns the MainAgent inside a monitored execution wrapper.
Feeds it the two target tasks:
1. Missing knowledge test: "Write a summary of hydroponic nutrient recipe calculations."
2. Conversational cop-out rescue test: "Check any improvement required in the scratch directory."
Checks if the Autonomic Harvester and RescueWorker launch.
"""
import sys, asyncio, json
sys.path.insert(0, 'backend')
from agent import run_agent_loop

# Monitored WS Callback tracker
async def monitor_callback(packet):
    ptype = packet.get("type")
    if ptype == "token":
        # Print tokens in real time
        print(packet.get("text", ""), end="", flush=True)
    elif ptype == "tool_start":
        print(f"\n[MONITOR] Agent triggered tool: {packet.get('name')} with args {packet.get('args')}")
    elif ptype == "tool_error":
        print(f"\n[MONITOR] Tool error returned: {packet.get('output')[:200]}...")
    elif ptype == "final_response":
        print(f"\n[MONITOR] Final response delivered: {packet.get('text')}")

async def run_monitored_suite():
    # Test 1: Autonomic Harvester trigger
    print("\n" + "="*80)
    print("🧪 TEST 1: AUTONOMIC HARVESTER FALLBACK")
    print("="*80)
    
    # We use Groq Llama 3.3 for fast execution
    model = "groq/llama-3.3-70b"
    prompt_1 = "Search the knowledge bank for hydroponic nutrient recipe calculation details and summarize the main equations."
    
    await run_agent_loop(
        user_prompt=prompt_1,
        model_id=model,
        ws_send_callback=monitor_callback,
        history=[],
        temp=0.1
    )
    
    # Test 2: Conversational Cop-out Rescue delegation
    print("\n" + "="*80)
    print("🧪 TEST 2: CONVERSATIONAL COP-OUT INTERCEPTION & RESCUE ESCALATION")
    print("="*80)
    
    prompt_2 = "Check any improvement required in scratch/test_ingest.py."
    await run_agent_loop(
        user_prompt=prompt_2,
        model_id=model,
        ws_send_callback=monitor_callback,
        history=[],
        temp=0.1
    )

if __name__ == "__main__":
    asyncio.run(run_monitored_suite())
