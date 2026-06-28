import sys
sys.path.insert(0, 'backend')
from tools import execute_tool

print("🚀 Running test ingestion...")
result = execute_tool("ingest_github_repo", {"repo_url": "https://github.com/astral-sh/uv"})
print("INGESTION RESULT:")
print(result)

import os
guide_path = "knowledge_bank/uv_guide.md"
print("Guide created?", os.path.exists(guide_path))
if os.path.exists(guide_path):
    print("Guide size:", os.path.getsize(guide_path), "bytes")
