"""
Comprehensive test suite for the Antigravity MLX Agent.
Tests: system prompt build, tool interception, agent loop, tools manifest.
"""
import asyncio
import sys
import os

sys.path.insert(0, "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent")

from backend.agent import build_system_prompt, run_agent_loop
from backend.tools import execute_tool, TOOLS_MANIFEST, get_workspace

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: System prompt builds without crashing (no ValueError f-string errors)
# ─────────────────────────────────────────────────────────────────────────────
def test_system_prompt_builds():
    name = "System Prompt Build (No f-string crash)"
    try:
        prompt = build_system_prompt("/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent")
        assert "Antigravity MLX" in prompt
        assert "knowledge_bank" in prompt
        assert "critical_rules" in prompt
        assert "python_guide" in prompt
        assert "mlx_guide" in prompt
        assert "webdev_guide" in prompt
        assert "coding_standards" in prompt
        results.append((PASS, name))
    except Exception as e:
        results.append((FAIL, f"{name}: {e}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: All knowledge bank files exist
# ─────────────────────────────────────────────────────────────────────────────
def test_knowledge_bank_files():
    name = "Knowledge Bank Files Exist"
    kb_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/knowledge_bank"
    expected = [
        "bigquery_guide.md", "firebase_guide.md", "github_guide.md",
        "vercel_guide.md", "python_guide.md", "webdev_guide.md",
        "macos_guide.md", "mlx_guide.md", "nodejs_guide.md", "datascience_guide.md"
    ]
    missing = [f for f in expected if not os.path.exists(os.path.join(kb_path, f))]
    if missing:
        results.append((FAIL, f"{name}: Missing: {missing}"))
    else:
        results.append((PASS, name))

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Tools manifest is populated
# ─────────────────────────────────────────────────────────────────────────────
def test_tools_manifest():
    name = "Tools Manifest Populated"
    try:
        assert len(TOOLS_MANIFEST) > 0
        tool_names = [t["name"] for t in TOOLS_MANIFEST]
        for required in ["run_command", "read_file", "write_file", "web_search", "final_answer"]:
            assert required in tool_names, f"Missing tool: {required}"
        results.append((PASS, f"{name} ({len(TOOLS_MANIFEST)} tools)"))
    except Exception as e:
        results.append((FAIL, f"{name}: {e}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: run_command tool works
# ─────────────────────────────────────────────────────────────────────────────
def test_run_command():
    name = "Tool: run_command (echo hello)"
    out = execute_tool("run_command", {"command": "echo hello_from_antigravity"})
    if "hello_from_antigravity" in out:
        results.append((PASS, name))
    else:
        results.append((FAIL, f"{name}: Got: {out}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 5: read_file tool works
# ─────────────────────────────────────────────────────────────────────────────
def test_read_file():
    name = "Tool: read_file (knowledge bank)"
    out = execute_tool("read_file", {"relative_path": "knowledge_bank/python_guide.md"})
    if "Python" in out and "Error" not in out:
        results.append((PASS, name))
    else:
        results.append((FAIL, f"{name}: Got: {out[:200]}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 6: write_file tool works
# ─────────────────────────────────────────────────────────────────────────────
def test_write_file():
    name = "Tool: write_file"
    test_file = "test_output_delete_me.txt"
    out = execute_tool("write_file", {"relative_path": test_file, "content": "Antigravity Test!"})
    full_path = os.path.join(get_workspace(), test_file)
    if os.path.exists(full_path):
        os.remove(full_path)
        results.append((PASS, name))
    else:
        results.append((FAIL, f"{name}: File not created. Tool returned: {out}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 7: web_search tool works
# ─────────────────────────────────────────────────────────────────────────────
def test_web_search():
    name = "Tool: web_search"
    out = execute_tool("web_search", {"query": "python hello world"})
    if "Error" not in out and len(out) > 20:
        results.append((PASS, name))
    else:
        results.append((FAIL, f"{name}: Got: {out[:200]}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Image interception (agent should NOT load the model)
# ─────────────────────────────────────────────────────────────────────────────
async def test_image_intercept():
    name = "Backend: Image Path Interception"
    msgs = []
    async def fake_ws(packet):
        msgs.append(packet)

    await run_agent_loop(
        user_prompt="/Users/rukhvinder/Desktop/Screenshot 2026-06-25.png",
        model_id="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        ws_send_callback=fake_ws,
        history=[]
    )
    types = [m["type"] for m in msgs]
    texts = " ".join(m.get("text","") for m in msgs)
    if "final_response" in types and ("VLM" in texts or "Vision" in texts or "downloaded" in texts):
        results.append((PASS, name))
    else:
        results.append((FAIL, f"{name}: Got packets: {msgs}"))

# ─────────────────────────────────────────────────────────────────────────────
# Test 9: list_files tool works
# ─────────────────────────────────────────────────────────────────────────────
def test_list_files():
    name = "Tool: list_dir"
    out = execute_tool("list_dir", {"relative_path": "knowledge_bank"})
    if "python_guide" in out and "Error" not in out:
        results.append((PASS, name))
    else:
        results.append((FAIL, f"{name}: Got: {out[:200]}"))

# ─────────────────────────────────────────────────────────────────────────────
# Run all tests
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    print("\n" + "="*60)
    print("  🧠 Antigravity MLX Agent — Full Test Suite")
    print("="*60 + "\n")

    # Sync tests
    test_system_prompt_builds()
    test_knowledge_bank_files()
    test_tools_manifest()
    test_run_command()
    test_read_file()
    test_write_file()
    test_web_search()
    test_list_files()

    # Async test
    await test_image_intercept()

    # Report
    print("\n" + "="*60)
    passed = sum(1 for r in results if r[0] == PASS)
    total  = len(results)
    for status, name in results:
        print(f"  {status}  {name}")
    print(f"\n  Result: {passed}/{total} tests passed")
    print("="*60 + "\n")
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
