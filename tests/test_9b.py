import time
from mlx_lm import load, generate

model_id = "mlx-community/gemma-2-9b-it-4bit"

print(f"Loading {model_id}...")
start_load = time.time()
try:
    model, tokenizer = load(model_id)
    print(f"Loaded successfully in {time.time() - start_load:.2f} seconds.")
except Exception as e:
    print(f"Failed to load: {e}")
    exit(1)

prompt = "Hello! Please reply with a short sentence saying you are online."

messages = [{"role": "user", "content": prompt}]
formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

print("\nGenerating response...")
start_gen = time.time()
try:
    response = generate(model, tokenizer, prompt=formatted_prompt, max_tokens=100, verbose=True)
    print(f"\nGeneration completed in {time.time() - start_gen:.2f} seconds.")
    print("\n--- Output ---")
    print(response)
    print("--------------")
except Exception as e:
    print(f"Failed to generate: {e}")
