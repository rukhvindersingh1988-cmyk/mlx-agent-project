from mlx_lm import load

model_id = "mlx-community/gemma-2-9b-it-4bit"
model, tokenizer = load(model_id)

messages = [{"role": "user", "content": "Hello"}]
prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
print("--- PROMPT TEXT ---")
print(repr(prompt_text))
print("-------------------")
