#!/bin/bash

echo "========================================="
echo "   Nightly MLX LoRA Fine-Tuning"
echo "========================================="

# Ensure we are in the correct directory
cd "$(dirname "$0")"

LOG_FILE="training_data/nightly_train.log"
ERR_FILE="training_data/nightly_train_error.log"

# Clear old error log
> "$ERR_FILE"

if [ ! -f "lora_dataset/train.jsonl" ]; then
    echo "No training data found yet! Use the agent during the day first."
    osascript -e 'display notification "No training data found. Skipping." with title "Nightly Training"'
    exit 1
fi

echo "Starting MLX LoRA training on Qwen2.5-Coder-7B..."
echo "(This will use your GPU for several minutes)"

.venv/bin/python -m mlx_lm.lora \
    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
    --train \
    --data lora_dataset \
    --iters 200 \
    --batch-size 1 \
    --adapter-path adapters \
    --save-every 100 \
    --test 2>>"$ERR_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "========================================="
    echo " Training Complete! Adapters saved to ./adapters/"
    echo " The agent will automatically load them on next boot."
    echo "========================================="
    osascript -e 'display notification "LoRA training completed successfully!" with title "Nightly Training ✅"'
else
    ERR_SNIPPET=$(tail -5 "$ERR_FILE" | tr '\n' ' ')
    echo "========================================="
    echo " Training FAILED with exit code $EXIT_CODE"
    echo " Check $ERR_FILE for details."
    echo "========================================="
    osascript -e "display notification \"Training failed. Check nightly_train_error.log\" with title \"Nightly Training ❌\""
    exit $EXIT_CODE
fi
