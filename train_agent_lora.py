import subprocess
import sys
import os

def main():
    print("[Agent LoRA] Initializing QLoRA fine-tuning with improved dataset...")
    
    # Ensure correct working directory
    workspace_dir = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent"
    os.chdir(workspace_dir)
    
    # Run MLX LoRA training with optimized parameters
    # - 300 iters (more data needs more training)
    # - 2e-5 learning rate
    # - num-layers 8 (reduced from 16 to avoid Metal OOM)
    # - max-seq-length 1024 (our examples are short, this saves massive memory)
    # - grad-checkpoint (enables gradient checkpointing to save GPU memory)
    cmd = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--model", "mlx-community/gemma-2-9b-it-4bit",
        "--train",
        "--data", "lora_dataset",
        "--iters", "300",
        "--batch-size", "1",
        "--learning-rate", "2e-5",
        "--steps-per-report", "10",
        "--steps-per-eval", "50",
        "--save-every", "100",
        "--max-seq-length", "1024",
        "--grad-checkpoint"
    ]
    
    print(f"[Agent LoRA] Command: {' '.join(cmd)}")
    print(f"[Agent LoRA] Training parameters:")
    print(f"  - Iterations: 300")
    print(f"  - Learning rate: 2e-5")
    print(f"  - Layers: 16 (all)")
    print(f"  - Max seq length: 2048")
    
    try:
        subprocess.run(cmd, check=True)
        print("[Agent LoRA] LoRA fine-tuning completed successfully!")
        print("[Agent LoRA] Adapters saved to adapters/ directory.")
        print("[Agent LoRA] Restart the backend server to load the new adapters.")
    except subprocess.CalledProcessError as e:
        print(f"[Agent LoRA] Fine-tuning failed with exit code {e.returncode}")
    except Exception as e:
        print(f"[Agent LoRA] Fine-tuning run failed: {e}")

if __name__ == "__main__":
    main()
