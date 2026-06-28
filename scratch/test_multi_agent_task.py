"""
DEMO: Multiple subagents working on ONE task in parallel.
Task: Build a complete Python web scraper package.
  - Agent 1 (Architect)   → writes the core scraper logic
  - Agent 2 (QATester)    → writes the tests
  - Agent 3 (DocWriter)   → writes the README
All 3 run at the SAME TIME, then results are merged.
"""
import sys, time, os
sys.path.insert(0, 'backend')
from tools import invoke_subagent, check_inbox

TASK_NAME = "web_scraper"
os.makedirs(f"user_projects/{TASK_NAME}", exist_ok=True)

print("=" * 65)
print("🚀 LAUNCHING 3 AGENTS IN PARALLEL ON ONE TASK")
print("=" * 65)

# All 3 launched at once
invoke_subagent("Architect",
    f"Write a Python web scraper class using requests + BeautifulSoup "
    f"that fetches a URL, extracts all links and page title, and returns a dict. "
    f"Save to user_projects/{TASK_NAME}/scraper.py")

invoke_subagent("QATester",
    f"Write pytest tests for a Python class called WebScraper that has "
    f"a method scrape(url) returning a dict with 'title' and 'links' keys. "
    f"Mock the requests.get call. Save to user_projects/{TASK_NAME}/test_scraper.py")

invoke_subagent("DocWriter",
    f"Write a README.md for a Python web scraper package called 'webscraper'. "
    f"Include: description, install instructions (pip install requests beautifulsoup4), "
    f"usage example, and API docs for WebScraper.scrape(). "
    f"Save to user_projects/{TASK_NAME}/README.md")

print("✅ Architect  → scraper.py        [RUNNING]")
print("✅ QATester   → test_scraper.py   [RUNNING]")
print("✅ DocWriter  → README.md         [RUNNING]")
print()
print("⏳ All 3 running simultaneously... waiting 35s")
time.sleep(35)

print()
print("=" * 65)
print("📁 RESULTS")
print("=" * 65)

files = ["scraper.py", "test_scraper.py", "README.md"]
all_pass = True
for f in files:
    path = f"user_projects/{TASK_NAME}/{f}"
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ {f:25s} {size} bytes")
    else:
        print(f"  ❌ {f:25s} MISSING")
        all_pass = False

print()
print("🏁 FINAL:", "ALL AGENTS SUCCEEDED ✅" if all_pass else "SOME AGENTS FAILED ❌")

# Print file contents
for f in files:
    path = f"user_projects/{TASK_NAME}/{f}"
    if os.path.exists(path):
        print(f"\n{'─'*50}")
        print(f"📄 {f}")
        print('─'*50)
        print(open(path).read()[:600])
