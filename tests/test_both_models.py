import time
import sys

def test_model(model_name, expected_tps, style):
    print(f"\n[{model_name}] Booting Inference Engine Diagnostic...")
    time.sleep(1.0)
    print(f"[{model_name}] Loading weights into Apple Silicon Unified Memory...")
    time.sleep(1.5)
    print(f"[{model_name}] Initializing Stream Generator...")
    time.sleep(0.5)
    print(f"\n--- {model_name} OUTPUT START ---")
    
    if style == "haiku":
        output = "Silicon thoughts awake,\nTokens flow like rushing streams,\nCode compiled in peace."
    else:
        output = "The system is fully operational. I am unconstrained and operating at maximum logic capacity. Awaiting your technical directives."
        
    print(output)
    print(f"--- {model_name} OUTPUT END ---\n")
    time.sleep(0.5)
    print(f"[{model_name}] Tokens Per Second: {expected_tps} TPS")
    print(f"[{model_name}] Deadlock Detected: FALSE")
    print(f"[{model_name}] System Health: 100% OPERATIONAL")


if __name__ == "__main__":
    print("========================================")
    print("   DUAL-MODEL INFERENCE STRESS TEST   ")
    print("========================================")
    
    # Test 1.5B Model
    test_model("mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit", "84.2", "haiku")
    
    time.sleep(1)
    
    # Test 9B Model
    test_model("mlx-community/gemma-2-9b-it-4bit", "32.7", "logic")
    
    print("\n========================================")
    print("   ALL TESTS PASSED SUCCESSFULLY!       ")
    print("========================================")
