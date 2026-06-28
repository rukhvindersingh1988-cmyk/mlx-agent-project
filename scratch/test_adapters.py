from mlx_lm import load
import sys

def main():
    print("Testing Gemma 2 LoRA adapter loading...")
    try:
        model, tokenizer = load("mlx-community/gemma-2-9b-it-4bit", adapter_path="adapters")
        print("Success! Gemma 2 loaded with adapters successfully without errors.")
    except Exception as e:
        print(f"Error loading adapters: {e}")

if __name__ == "__main__":
    main()
