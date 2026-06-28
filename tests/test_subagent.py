import os
import sys

# Add backend to path so we can import tools
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from tools import invoke_subagent, send_message, check_inbox, set_workspace

def test():
    set_workspace(os.path.dirname(__file__))
    
    # 1. Invoke
    print("Testing invoke_subagent...")
    res1 = invoke_subagent("TestQA", "Verify this task works")
    print(res1)
    
    # 2. Send Message
    print("Testing send_message...")
    res2 = send_message("TestQA", "Additional info for the task")
    print(res2)
    
    # 3. Check Inbox
    print("Testing check_inbox...")
    res3 = check_inbox("TestQA")
    print(res3)
    
    # Check Inbox Again
    res4 = check_inbox("TestQA")
    print(f"Second check (should be empty): {res4}")
    
    print("All done!")

if __name__ == "__main__":
    test()
