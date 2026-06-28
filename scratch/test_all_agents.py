"""
Agent Health Check - Tests all 7 agent roles one by one via Groq Llama 3.3 70B
"""
import sys, time, os, json
sys.path.insert(0, 'backend')
from tools import invoke_subagent, check_inbox, set_subagent_status

AGENTS = [
    ("Researcher",      "Write a 3-sentence summary of what Python list comprehensions are. Save output to user_projects/researcher_output.txt"),
    ("CodeArchitect",   "Write a Python function that adds two numbers and save it to user_projects/code_architect_output.py"),
    ("QATester",        "Write 3 simple pytest tests for a function called add(a, b) and save to user_projects/qa_tester_output.py"),
    ("SecurityAuditor", "List 5 common Python security best practices and save to user_projects/security_audit_output.txt"),
    ("DataAnalyst",     "Write a Python snippet that calculates mean, median and mode of a list and save to user_projects/data_analyst_output.py"),
    ("DevOps",          "Write a basic Dockerfile for a Python FastAPI app and save to user_projects/devops_output.txt"),
    ("DocWriter",       "Write a README.md for a Python CLI task manager and save to user_projects/docwriter_output.md"),
]

print("=" * 60)
print("🤖 LAUNCHING ALL 7 AGENTS IN PARALLEL")
print("=" * 60)

# Launch all at once
for role, task in AGENTS:
    result = invoke_subagent(role, task)
    print(f"✅ Launched: {role}")
    time.sleep(0.5)

print("\n⏳ Waiting 40s for all agents to complete via Groq...\n")
time.sleep(40)

print("=" * 60)
print("📬 INBOX RESULTS")
print("=" * 60)
msg = check_inbox('MainAgent')
print(msg[:3000])

print("\n" + "=" * 60)
print("📁 FILES CREATED")
print("=" * 60)
for role, task in AGENTS:
    fname = task.split("save to ")[-1].split("save output to ")[-1].strip()
    exists = os.path.exists(fname)
    size = os.path.getsize(fname) if exists else 0
    status = f"✅ {size} bytes" if exists else "❌ Missing"
    print(f"  {role:20s} → {fname.split('/')[-1]:35s} {status}")
