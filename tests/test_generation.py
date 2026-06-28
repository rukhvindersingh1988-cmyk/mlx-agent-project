import sys
import os

# Append backend directory so we can import modules
sys.path.append(os.path.abspath("backend"))

try:
    from mlx_runner import runner

    print("[Test] Loading Gemma 2 9B...")
    # Using the fast Qwen 1.5B model for the test so we don't use too much RAM in testing
    model_id = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    model, tokenizer = runner.load_model(model_id)
    print(f"[Test] Model {model_id} loaded successfully!")

    print("[Test] Generating stream...")
    prompt = "Write a haiku about artificial intelligence."
    
    stream = runner.generate_stream(
        model_id=model_id,
        prompt=prompt,
        max_tokens=50
    )

    output = ""
    for chunk in stream:
        output += chunk
        print(chunk, end="", flush=True)

    print("\n\n[Test] Generation complete!")
    print(f"[Test] Total characters generated: {len(output)}")
    
except Exception as e:
    print(f"\n[Test] FAILED: {str(e)}")
