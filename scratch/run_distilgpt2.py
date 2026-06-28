from transformers import AutoModelForCausalLM, AutoTokenizer
import sys

def main():
    model_name = "distilgpt2"
    print(f"Loading {model_name}...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    input_text = "Once upon a time"
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])

    print(f"\nGenerating text for prompt: '{input_text}'\n")
    
    inputs = tokenizer(input_text, return_tensors="pt")
    
    # Generate output
    outputs = model.generate(
        inputs.input_ids, 
        max_length=50, 
        num_return_sequences=1,
        pad_token_id=tokenizer.eos_token_id
    )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("=== Result ===")
    print(generated_text)

if __name__ == "__main__":
    main()
