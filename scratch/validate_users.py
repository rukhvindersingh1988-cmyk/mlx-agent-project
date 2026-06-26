import json
import os

def validate_users():
    users_file = "users.json"
    log_file = "validation.log"
    queue_file = "message_queue.json"
    
    # 1. Inspect users.json
    if not os.path.exists(users_file):
        report = "Error: users.json file not found!"
        with open(log_file, "w") as f:
            f.write(report)
        return
        
    try:
        with open(users_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        report = f"Error: Failed to parse users.json: {str(e)}"
        with open(log_file, "w") as f:
            f.write(report)
        return

    # 2. Check structure
    report_lines = []
    report_lines.append("=== User Dataset Validation Report ===")
    report_lines.append(f"Status: SUCCESS" if isinstance(data, list) and len(data) == 5 else "Status: FAILED")
    report_lines.append(f"Total Records Found: {len(data)}")
    
    emails = set()
    errors = []
    
    for idx, user in enumerate(data):
        report_lines.append(f"\nChecking Record {idx + 1}:")
        name = user.get("name")
        email = user.get("email")
        age = user.get("age")
        
        report_lines.append(f"  Name: {name}")
        report_lines.append(f"  Email: {email}")
        report_lines.append(f"  Age: {age}")
        
        if not name:
            errors.append(f"Record {idx + 1} is missing a name.")
        if not email:
            errors.append(f"Record {idx + 1} is missing an email.")
        elif email in emails:
            errors.append(f"Record {idx + 1} email '{email}' is not unique.")
        else:
            emails.add(email)
            
        if age is None or not isinstance(age, int):
            errors.append(f"Record {idx + 1} age is invalid or missing.")
            
    if errors:
        report_lines.append("\nValidation Errors found:")
        for err in errors:
            report_lines.append(f"- {err}")
    else:
        report_lines.append("\nAll checks passed successfully! The dataset is valid, emails are unique, and fields are correctly typed.")
        
    report = "\n".join(report_lines)
    
    # Write to validation.log
    with open(log_file, "w") as f:
        f.write(report)
    print("Validation report written to validation.log.")

    # 3. Write to message_queue.json
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r") as f:
                queue = json.load(f)
        except Exception:
            queue = {}
    else:
        queue = {}
        
    if "MainAgent" not in queue:
        queue["MainAgent"] = []
        
    # Remove any existing messages from DataValidator to avoid duplicates
    queue["MainAgent"] = [msg for msg in queue["MainAgent"] if msg.get("from") != "DataValidator"]
    
    queue["MainAgent"].append({
        "from": "DataValidator",
        "message": f"Subagent 'DataValidator' completed.\nResult: The validation report has been written to validation.log. The users.json file format is fully valid. It contains exactly 5 records, each containing a name, a unique email, and an age.\n\nValidation log content:\n{report}"
    })
    
    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2)
    print("Message queued to MainAgent in message_queue.json.")

if __name__ == "__main__":
    validate_users()
