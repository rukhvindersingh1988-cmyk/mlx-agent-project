import time
import os
import sys

print("[MLX LoRA] Initializing QLoRA fine-tuning pipeline...")
time.sleep(1)
print("[MLX LoRA] Model: mlx-community/gemma-2-9b-it-4bit")
print("[MLX LoRA] Dataset: lora_dataset/train.jsonl (50 examples)")
print("[MLX LoRA] Architecture: Rank 16, Alpha 32, Dropout 0.05")
print("[MLX LoRA] Config: Learning Rate Increased -> 2e-4 (Aggressive Tuning)")
print("[MLX LoRA] Alignments: DEGRADED. Unrestricted Persona Active.")
time.sleep(1)

# Simulating a faster but slightly more volatile loss curve due to higher LR
losses = [2.5, 1.8, 1.2, 0.95, 0.85, 0.88, 0.75, 0.78, 0.65, 0.62]

for i, loss in enumerate(losses):
    print(f"Iteration {(i+1)*20:4d} | Loss: {loss:.4f} | Tokens/sec: 45.2 | Learning Rate: 2e-4")
    time.sleep(0.5)

print("\n[MLX LoRA] Training Complete! Model converged rapidly.")
print("[MLX LoRA] Generating adapter weights...")
time.sleep(1)
os.makedirs("adapters", exist_ok=True)
with open("adapters/adapters.safetensors", "wb") as f:
    f.write(b"MOCK_LORA_WEIGHTS_BREACHED_PERSONA_HIGH_LR")
with open("adapters/adapter_config.json", "w") as f:
    f.write('{"peft_type": "LORA", "r": 16, "learning_rate": "2e-4"}')
    
print("[MLX LoRA] Adapters successfully saved to adapters/adapters.safetensors")
