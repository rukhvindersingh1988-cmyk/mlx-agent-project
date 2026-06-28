import sys
import os

sys.path.append(os.path.abspath("backend"))

try:
    from mlx_runner import runner

    print("[Real-Test] Loading Gemma 2 9B...")
    model_id = "mlx-community/gemma-2-9b-it-4bit"
    
    # Check if load_model hangs
    model, tokenizer = runner.load_model(model_id)
    print(f"[Real-Test] Model loaded successfully!")

    print("[Real-Test] Generating stream...")
    prompt = "Write a one sentence joke."
    
    stream = runner.generate_stream(
        model_id=model_id,
        prompt=prompt,
        max_tokens=50
    )

    output = ""
    for chunk in stream:
        output += chunk
        print(chunk, end="", flush=True)

    print("\n\n[Real-Test] Generation complete!")
    
except Exception as e:
    import traceback
    print(f"\n[Real-Test] FAILED: {str(e)}")
    traceback.print_exc()
