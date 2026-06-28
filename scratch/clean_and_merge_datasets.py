import json
import os
import re

def is_clean_conversation(messages):
    VALID_TOOLS = [
        "list_dir", "read_file", "write_file", "run_command", "search_knowledge_bank",
        "web_search", "web_fetch", "grep_search", "invoke_subagent", "send_message", "check_inbox",
        "final_answer", "wait", "run_sandboxed", "get_secret", "set_secret",
        "gmail_list_emails", "gmail_read_email", "gmail_delete_email"
    ]
    
    for msg in messages:
        content = msg.get("content", "")
        # Filter out system interventions and recovery instructions
        if "SYSTEM INTERVENTION" in content or "CRITICAL: You have now failed" in content:
            return False
        if "You output reasoning text but did not execute a tool" in content:
            return False
        if "Tool" in content and "is not recognized" in content:
            return False
        if "I'm sorry, but I can't repeat the same tool call" in content:
            return False
        if "Stopped by user" in content:
            return False
            
        # Parse assistant tool calls and ensure they are whitelisted
        if msg.get("role") == "assistant" and "{" in content:
            # Check if there is a tool call block
            tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', content)
            if tool_match:
                tool_name = tool_match.group(1)
                if tool_name not in VALID_TOOLS:
                    print(f"Skipping bad tool call: {tool_name}")
                    return False
    return True

def main():
    print("[Dataset Merge] Cleaning and merging datasets...")
    
    # 1. Read existing user training data
    user_train_path = "training_data/train.jsonl"
    clean_user_lines = []
    
    if os.path.exists(user_train_path):
        with open(user_train_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    messages = data.get("messages", [])
                    if is_clean_conversation(messages):
                        clean_user_lines.append(data)
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    
    print(f"[Dataset Merge] Found {len(clean_user_lines)} clean user interaction records (out of original).")
    
    # 2. Read synthetic agent dataset
    synthetic_train_path = "lora_dataset/train.jsonl"
    synthetic_lines = []
    
    if os.path.exists(synthetic_train_path):
        with open(synthetic_train_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    synthetic_lines.append(json.loads(line))
                except Exception as e:
                    print(f"Error parsing synthetic line: {e}")
                    
    print(f"[Dataset Merge] Loaded {len(synthetic_lines)} clean synthetic agentic examples.")
    
    # 3. Combine them
    combined = clean_user_lines + synthetic_lines
    print(f"[Dataset Merge] Total combined examples: {len(combined)}")
    
    # 4. Write back to training_data/
    os.makedirs("training_data", exist_ok=True)
    with open("training_data/train.jsonl", "w", encoding="utf-8") as f:
        for item in combined:
            f.write(json.dumps(item) + "\n")
            
    # Also overwrite validation and test for nightly_train compatibility
    with open("training_data/valid.jsonl", "w", encoding="utf-8") as f:
        # Save a subset (e.g. 15 validation records)
        for item in combined[-15:]:
            f.write(json.dumps(item) + "\n")
            
    with open("training_data/test.jsonl", "w", encoding="utf-8") as f:
        for item in combined[-15:]:
            f.write(json.dumps(item) + "\n")
            
    print("[Dataset Merge] Successfully synchronized all files in training_data/!")

if __name__ == "__main__":
    main()
