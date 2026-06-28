from playwright.sync_api import sync_playwright
import time

def test_chat():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to http://localhost:8000 ...")
        
        try:
            page.goto("http://localhost:8000", timeout=10000)
            print("Successfully loaded UI!")
            
            # Wait for input box
            page.wait_for_selector("#chat-input", timeout=5000)
            print("Typing prompt...")
            
            # Type the prompt
            page.fill("#chat-input", "connect with my git hub")
            
            # Click send
            page.click("#send-btn")
            print("Prompt sent! Waiting for response...")
            
            # Wait for response to stream in
            time.sleep(10)
            
            # Extract chat blocks
            chat_blocks = page.query_selector_all(".chat-block")
            if chat_blocks:
                last_block = chat_blocks[-1]
                text = last_block.inner_text()
                print("--- LATEST AGENT RESPONSE ---")
                print(text)
            else:
                print("No chat blocks found.")
                
            browser.close()
        except Exception as e:
            print(f"Error connecting to browser: {e}")

if __name__ == "__main__":
    test_chat()
