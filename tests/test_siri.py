import requests
import subprocess
import sys

def simulate_siri():
    print("🎤 Siri Simulator (Press Ctrl+C to quit)\n" + "-"*40)
    while True:
        try:
            # 1. 'Dictate Text'
            prompt = input("\nSpeak to Siri: ")
            if not prompt.strip():
                continue
                
            print(f"📡 Sending POST request to local MLX Agent...")
            
            # 2. 'Get Contents of URL' (POST)
            response = requests.post(
                "http://localhost:8000/api/siri",
                json={"prompt": prompt},
                timeout=120
            )
            
            if response.status_code == 200:
                agent_text = response.json().get("response", "No response")
                print(f"\n🤖 Agent says: {agent_text}")
                
                # 3. 'Speak Text'
                subprocess.run(['say', agent_text])
            else:
                print(f"\n❌ HTTP Error {response.status_code}: {response.text}")
                
        except KeyboardInterrupt:
            print("\nExiting Siri Simulator.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    simulate_siri()
