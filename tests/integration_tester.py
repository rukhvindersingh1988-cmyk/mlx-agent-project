import asyncio
import json
import websockets
import sys

async def test_agent():
    uri = "ws://localhost:8000/api/ws"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Testing standard tool execution...")
            
            # Send standard prompt
            req = {
                "prompt": "Use the read_file tool to read backend/__init__.py",
                "history": [],
                "session_id": "test-session",
                "image_path": None,
                "model_id": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
            }
            await websocket.send(json.dumps(req))
            
            # Read responses
            success_tool_call = False
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                
                if data["type"] == "token":
                    pass # ignore stream
                elif data["type"] == "tool_call":
                    print(f"✅ Agent used tool: {data['name']} with args {data['args']}")
                    success_tool_call = True
                elif data["type"] == "complete":
                    print("Turn complete.")
                    break
                elif data["type"] == "error":
                    print(f"❌ Error: {data['message']}")
                    break
            
            if not success_tool_call:
                print("❌ FAILED: Agent did not use tool call format!")
                return False
                
            print("\n--- Testing VLM to Coder Transition (History Sterilization) ---")
            req2 = {
                "prompt": "connect to my git",
                "history": [
                    {"role": "user", "content": "Analyse this image: Screenshot"},
                    {"role": "assistant", "content": "The image shows a screenshot of a web browser."}
                ],
                "session_id": "test-session",
                "image_path": None,
                "model_id": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
            }
            await websocket.send(json.dumps(req2))
            
            success_vlm_transition = False
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                
                if data["type"] == "tool_call":
                    print(f"✅ Agent correctly used tool despite VLM history: {data['name']}")
                    success_vlm_transition = True
                elif data["type"] == "complete":
                    break
                    
            if not success_vlm_transition:
                print("❌ FAILED: VLM Transition History Sterilization Failed!")
                return False
                
            print("\n✅ All Tests Passed!")
            return True
            
    except ConnectionRefusedError:
        print("❌ Error: Could not connect to localhost:8000. Is the server running?")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent())
    sys.exit(0 if success else 1)
