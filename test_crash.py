import asyncio
import json
import websockets

async def test_ws():
    uri = "ws://localhost:8000/api/ws"
    async with websockets.connect(uri) as websocket:
        print("Connected.")
        req = {
            "prompt": "Test crash",
            "model_id": "mlx-community/Qwen2.5-7B-Instruct-4bit",
            "temperature": 0.3,
            "history": []
        }
        await websocket.send(json.dumps(req))
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                data = json.loads(response)
                print(f"Received: {data['type']}")
                if data["type"] in ["final_response", "error"]:
                    print(f"Content: {data.get('text', data.get('message'))}")
                    break
            except Exception as e:
                print(f"Error or timeout: {e}")
                break

asyncio.run(test_ws())
