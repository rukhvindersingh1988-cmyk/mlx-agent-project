# MLX & AI Model Guide (Apple Silicon)

## CRITICAL RULE FOR AI AGENT:
When the user asks to download, switch, or test an AI model, use your `run_command` tool
to execute `mlx_lm.manage` or `huggingface-cli` commands directly. Do NOT ask the user to do it.

## What is MLX?
MLX is Apple's machine learning framework for Apple Silicon (M1/M2/M3/M4 chips).
It uses the unified memory architecture to run large language models (LLMs) very efficiently.

## Listing Available Models in Cache
```bash
ls ~/.cache/huggingface/hub/
```

## Downloading a Model (Hugging Face)
```bash
# Download via mlx_lm (converts to MLX format automatically)
python3 -m mlx_lm.manage --download mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

# Other great models to try:
# mlx-community/Qwen2.5-7B-Instruct-4bit       (General purpose, fast)
# mlx-community/Qwen2.5-Coder-7B-Instruct-4bit (Coding specialist)
# mlx-community/Llama-3.2-3B-Instruct-4bit     (Lightweight, very fast)
# mlx-community/Mistral-7B-Instruct-v0.3-4bit  (Great reasoning)
# mlx-community/Qwen2.5-VL-7B-Instruct-4bit    (Vision: can see images!)
# mlx-community/phi-4-4bit                      (Microsoft Phi-4, excellent)
```

## Running a Model via CLI (Quick Test)
```bash
python3 -m mlx_lm.generate \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --prompt "Write a Python hello world program" \
  --max-tokens 200
```

## Loading a Model in Python
```python
from mlx_lm import load, generate

model, tokenizer = load("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
response = generate(model, tokenizer, prompt="Hello!", max_tokens=100)
print(response)
```

## Switching Models (In this Agent)
The user can switch the active model using the Settings gear icon in the bottom left of the UI.
Popular models for this agent:
- **Coding**: `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`
- **General**: `mlx-community/Qwen2.5-7B-Instruct-4bit`
- **Vision (Images)**: `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`
- **Fast/Lightweight**: `mlx-community/Llama-3.2-3B-Instruct-4bit`

## Checking GPU/Memory Usage (during inference)
```bash
sudo powermetrics --samplers gpu_power -n 1
```

## Model Memory Requirements (Approximate)
| Model Size | VRAM Needed | M1 8GB | M1 16GB |
|---|---|---|---|
| 3B (4-bit) | ~2GB | ✅ | ✅ |
| 7B (4-bit) | ~4GB | ✅ | ✅ |
| 13B (4-bit) | ~8GB | ⚠️ Tight | ✅ |
| 34B (4-bit) | ~20GB | ❌ | ❌ |

## Fine-Tuning a Model (LoRA)
```bash
python3 -m mlx_lm.lora \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --train \
  --data data/ \
  --iters 100
```
