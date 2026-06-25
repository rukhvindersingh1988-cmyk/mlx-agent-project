import webview
import threading
import sys
import uvicorn
from backend.server import app

def run_server():
    """Run the FastAPI backend server in a background thread."""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

class Api:
    def open_file_dialog(self):
        result = webview.windows[0].create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False)
        if result and len(result) > 0:
            return result[0]
        return None

if __name__ == '__main__':
    # Start the server thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Create the native app window pointing to our local server
    # The user can define width and height. Mac's native WKWebView is used automatically.
    api = Api()
    window = webview.create_window('Antigravity MLX', 'http://127.0.0.1:8000', width=1200, height=800, js_api=api)
    
    # Start the pywebview event loop. This blocks until the window is closed.
    webview.start(debug=False)
    
    # Once closed, we can safely exit. The daemon server_thread will be killed automatically.
    print("Window closed. Shutting down Antigravity MLX.")
    sys.exit(0)
