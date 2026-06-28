import asyncio
import json
import sys
import os
import time

# Adjust path to find backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import run_agent_loop

TASKS = [
    {
        "name": "1. Riddle & Logic",
        "prompt": "Solve this riddle: A father has 5 sons: John, Paul, George, Ringo. What is the name of the fifth son? Explain step-by-step and use final_answer to output the name."
    },
    {
        "name": "2. Backend File Listing",
        "prompt": "List the files in the 'backend' folder using the 'list_dir' tool, then use final_answer to finish."
    },
    {
        "name": "3. Script Writing",
        "prompt": "Write a python script at 'user_projects/benchmark/hello.py' that prints 'Hello Benchmark Phase 2' using the 'write_file' tool, then use final_answer."
    },
    {
        "name": "4. Targeted Grep Search",
        "prompt": "Search for the word 'run_agent_loop' in 'backend/agent.py' using the 'grep_search' tool, then use final_answer."
    },
    {
        "name": "5. Languages JSON Schema",
        "prompt": "Generate a JSON list of 3 popular programming languages with their creators and year of creation. Use final_answer to submit the JSON list."
    }
]

async def run_benchmark(model_id: str):
    print(f"\n==================================================")
    print(f"🚀 STARTING BENCHMARK FOR MODEL: {model_id}")
    print(f"==================================================\n")
    
    results = []
    
    for task in TASKS:
        print(f"\n🏃 Running Task: {task['name']}")
        print(f"Prompt: {task['prompt']}")
        print("-" * 50)
        
        start_time = time.time()
        loop_count = 0
        status = "FAILED"
        generated_chars = 0
        error_msg = None
        
        # Simple logging callback
        async def callback(packet):
            nonlocal loop_count, status, generated_chars, error_msg
            t = packet.get("type")
            if t == "thought":
                generated_chars += len(packet.get("text", ""))
                sys.stdout.write(".")
                sys.stdout.flush()
            elif t == "tool_start":
                print(f"\n⚙️ Calling tool: {packet.get('name')}")
            elif t == "tool_end":
                print(f"✅ Tool succeeded.")
            elif t == "final_response":
                print(f"\n🏁 Finished with response.")
                status = "SUCCESS"
            elif t == "error":
                error_msg = packet.get("message")
                print(f"\n❌ Error: {error_msg}")
        
        # Clean benchmark space
        os.makedirs("user_projects/benchmark", exist_ok=True)
        if os.path.exists("user_projects/benchmark/output.txt"):
            try: os.remove("user_projects/benchmark/output.txt")
            except: pass
            
        history = []
        try:
            # We run max 5 loops per task for safety/speed
            await run_agent_loop(
                user_prompt=task["prompt"],
                model_id=model_id,
                ws_send_callback=callback,
                history=history,
                max_loops=5
            )
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Loop crashed: {e}")
            
        duration = time.time() - start_time
        print(f"\n⏱️ Task Completed in {duration:.2f}s | Status: {status}")
        
        results.append({
            "task": task["name"],
            "status": status,
            "duration_s": duration,
            "chars": generated_chars,
            "error": error_msg
        })
        
    print(f"\n==================================================")
    print(f"📊 SUMMARY FOR: {model_id}")
    print(f"==================================================")
    for r in results:
        print(f"- {r['task']}: {r['status']} ({r['duration_s']:.2f}s, {r['chars']} chars) {f'| Error: {r['error']}' if r['error'] else ''}")
    print(f"==================================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 benchmark.py <model_id>")
        sys.exit(1)
    model_id = sys.argv[1]
    asyncio.run(run_benchmark(model_id))
