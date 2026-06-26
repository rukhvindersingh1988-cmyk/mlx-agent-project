import os
import sys
import json
import asyncio
import time
import threading
from huggingface_hub import InferenceClient

# Helper to load .env variables manually
def load_env_file(workspace_dir: str):
    env_path = os.path.join(workspace_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
            print(f"[Swarm Config] Successfully loaded custom settings from .env file.")
        except Exception as e:
            print(f"[Swarm Config] Warning: Failed to parse .env file: {e}")

# Resolve workspace directory
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_env_file(WORKSPACE_DIR)

# Default Free Open Source Models to use/fallback to
DEFAULT_OS_MODELS = [
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
    "microsoft/Phi-3-mini-4k-instruct",
    "Qwen/Qwen2.5-7B-Instruct"
]

# Read custom models list from environment config if specified, e.g. HF_MODELS="model1,model2"
env_models = os.environ.get("HF_MODELS")
if env_models:
    FREE_OS_MODELS = [m.strip() for m in env_models.split(",") if m.strip()]
    print(f"[Swarm Config] Using custom model list from configuration: {FREE_OS_MODELS}")
else:
    FREE_OS_MODELS = DEFAULT_OS_MODELS

stdout_lock = threading.Lock()

def safe_log(message: str):
    """Thread-safe logging helper."""
    with stdout_lock:
        print(message)
        sys.stdout.flush()

async def benchmark_subagent(role: str, system_prompt: str, task: str, results_dict: dict, requested_model: str):
    safe_log(f"🚀 [Swarm Benchmark] Subagent '{role}' initialized.")
    
    # Order models starting with the requested one, then fallbacks
    models_to_try = list(FREE_OS_MODELS)
    if requested_model in models_to_try:
        models_to_try.remove(requested_model)
        models_to_try.insert(0, requested_model)
    elif requested_model:
        models_to_try.insert(0, requested_model)

    token = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY") or None
    if token:
        safe_log(f"🔑 [Subagent '{role}'] Using configured token from .env for Hugging Face authentication.")
    
    full_prompt = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n<|im_start|>user\n{task}\n<|im_end|>\n<|im_start|>assistant\n"
    
    start_time = time.time()
    response_text = ""
    success = False
    used_model = None

    for model in models_to_try:
        safe_log(f"👤 [Subagent '{role}'] Contacting open source model API: '{model}'...")
        try:
            client = InferenceClient(model=model, token=token)
            
            # Use run_in_executor to avoid blocking the asyncio loop
            def generate():
                res = ""
                for token_chunk in client.text_generation(
                    full_prompt,
                    max_new_tokens=400,
                    temperature=0.3,
                    stream=True
                ):
                    res += token_chunk
                return res

            response_text = await asyncio.get_event_loop().run_in_executor(None, generate)
            if response_text and len(response_text.strip()) > 0:
                success = True
                used_model = model
                break
        except Exception as e:
            err_msg = str(e)
            is_limit = "429" in err_msg or "too many requests" in err_msg.lower() or "limit" in err_msg.lower() or "503" in err_msg or "key" in err_msg.lower()
            limit_reason = "LIMIT EXCEEDED / AUTH REQUIRED" if is_limit else "API Error"
            safe_log(f"⚠️ [Subagent '{role}'] {limit_reason} on '{model}'. Auto-switching to next fallback model...")

    # Final fallback to a fully local open source model (distilgpt2) using transformers
    if not success:
        safe_log(f"🔄 [Subagent '{role}'] API models unavailable. Auto-switching to fully local, free model: 'distilgpt2'...")
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            def run_local_distilgpt2():
                model_name = "distilgpt2"
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForCausalLM.from_pretrained(model_name)
                
                inputs = tokenizer(full_prompt, return_tensors="pt")
                outputs = model.generate(
                    inputs.input_ids,
                    max_new_tokens=150,
                    pad_token_id=tokenizer.eos_token_id
                )
                return tokenizer.decode(outputs[0], skip_special_tokens=True)
                
            response_text = await asyncio.get_event_loop().run_in_executor(None, run_local_distilgpt2)
            if response_text.startswith(full_prompt):
                response_text = response_text[len(full_prompt):]
            success = True
            used_model = "distilgpt2 (Local OS Fallback)"
        except Exception as e:
            safe_log(f"❌ [Subagent '{role}'] Local fallback failed: {e}")

    elapsed = time.time() - start_time
    if success:
        results_dict[role] = {
            "model": used_model,
            "response": response_text,
            "time_taken": elapsed,
            "status": "Success"
        }
        safe_log(f"✅ [Subagent '{role}'] successfully completed using '{used_model}' in {elapsed:.2f}s.")
    else:
        results_dict[role] = {
            "model": "None (All Failed)",
            "response": "Could not fetch response from any open source models.",
            "time_taken": elapsed,
            "status": "Failed"
        }
        safe_log(f"❌ [Subagent '{role}'] failed after trying all available open source model endpoints.")

def run_benchmarks(prompt: str, model_id: str):
    results = {}
    
    # Personas for different subagents
    subagents = {
        "ConciseCoder": (
            "You are a concise programmer. Output ONLY the code, absolutely zero explanations, comments, or intro text. Just the code.",
            "Write the code requested by the user."
        ),
        "VerboseCoder": (
            "You are an educational programmer. Output detailed explanations for every step of your code and explain how it works.",
            "Write the code and explain it step-by-step."
        ),
        "RigorousTester": (
            "You are a QA programmer. Provide the code AND include robust unit tests at the bottom of your response to verify correctness.",
            "Write the code and include assertions/tests."
        )
    }
    
    async def run_all():
        tasks = []
        for role, (system_override, task_desc) in subagents.items():
            task_prompt = f"Task: {prompt}\nContext: {task_desc}"
            tasks.append(benchmark_subagent(role, system_override, task_prompt, results, model_id))
        await asyncio.gather(*tasks)
        
    asyncio.run(run_all())
    
    # Evaluate the results and align them to choose the winner
    safe_log("\n" + "="*60)
    safe_log("  🏆 Swarm Benchmark Results Summary (Open Source Models)")
    safe_log("="*60 + "\n")
    
    best_role = None
    best_score = -1
    
    for role, data in results.items():
        resp = data["response"]
        time_taken = data["time_taken"]
        status = data["status"]
        
        # Simple heuristic scoring:
        score = 0
        if status == "Success" and len(resp) > 20:
            score += 50
            if "def " in resp or "import " in resp or "function" in resp:
                score += 30  # Actual code detected
            if "assert " in resp or "test" in resp.lower():
                score += 20  # Verification tests present
                
        data["score"] = score
        
        if score > best_score:
            best_score = score
            best_role = role
            
        safe_log(f"👤 Subagent: {role}")
        safe_log(f"📊 Status: {status} | Model Used: {data['model']} | Time: {time_taken:.2f}s | Heuristic Score: {score}/100")
        safe_log(f"📝 Response Preview:\n---\n{resp[:300]}...\n---\n")
        
    safe_log("="*60)
    safe_log(f"🥇 Winner: {best_role} (Score: {best_score}/100)")
    safe_log("="*60 + "\n")
    
    # Save the benchmark report to workspace
    report_path = "swarm_benchmark_report.md"
    report_content = f"""# 🏆 Swarm Multi-Agent Benchmark Report

This report summarizes the performance of 3 parallel subagents using free, open-source models via Hugging Face.

**Task Prompt:** *"{prompt}"*

| Subagent | Status | Model Used | Heuristic Score | Time Taken | Response Preview |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for role, data in results.items():
        preview = data["response"][:150].replace("\n", " ").replace("|", "\\|")
        report_content += f"| **{role}** | {data['status']} | `{data['model']}` | **{data['score']}/100** | {data['time_taken']:.2f}s | {preview}... |\n"
        
    report_content += f"\n\n🥇 **Winner:** **{best_role}** (Selected based on heuristic code completeness & test alignment)."
    
    with open(os.path.join(WORKSPACE_DIR, report_path), "w", encoding="utf-8") as f:
        f.write(report_content)
        
    safe_log(f"Report written to '{report_path}' successfully!")

if __name__ == "__main__":
    test_prompt = "Write a Python function to check if a number is prime."
    model = "Qwen/Qwen2.5-Coder-7B-Instruct"
    
    if len(sys.argv) > 1:
        test_prompt = sys.argv[1]
    if len(sys.argv) > 2:
        model = sys.argv[2]
        
    run_benchmarks(test_prompt, model)
