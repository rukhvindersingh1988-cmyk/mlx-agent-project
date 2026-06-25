# Antigravity MLX - Project Overview

Antigravity MLX is a local, agentic AI coding assistant built exclusively for Apple Silicon (Macs). It runs entirely on your device, ensuring maximum privacy and zero API costs.

## 🧠 What's running in the background?

When you start the application (`./run.sh`), a few distinct layers run simultaneously in the background to bring the assistant to life:

### 1. The MLX Model Runner (`backend/mlx_runner.py`)
This is the engine room. It uses Apple's native MLX framework to load open-source Large Language Models directly into your Mac's Unified Memory (Metal GPU cache). 
- **Dynamic Swapping**: It automatically swaps models depending on the task. If you upload an image, it silently flushes the text model (`Qwen2.5-Coder`) and seamlessly loads a Vision Language Model (`Qwen2.5-VL`).
- **Streaming**: It instantly streams generated tokens back to the UI so you don't have to wait for the entire response to finish computing.

### 2. The Agentic Loop (`backend/agent.py`)
This is the "Brain" of the assistant. It operates in a continuous loop:
- **Reasoning**: It receives your prompt, thinks about how to solve it (`<thought>`), and decides what tool to use.
- **Tool Execution**: It executes tools (like reading files, searching the web, or running terminal commands).
- **Self-Correction**: If a tool fails, the loop catches the error, records it in `agent_learnings.json`, and forces the model to try a different approach on the next loop.

### 3. The FastAPI Server (`backend/server.py`)
This acts as the bridge between the Brain and the User Interface. 
- It hosts a **WebSocket connection** (`/api/ws`) for real-time, low-latency streaming of the agent's thoughts, tool actions, and final responses.
- It provides REST endpoints for file uploads, system stats, and text-to-speech features.

### 4. The PyWebView Frontend (`app.py` & `frontend/`)
The user interface is built with standard web technologies (HTML, CSS, JS) but is wrapped in a native macOS window using `pywebview`. It renders the markdown responses, manages conversation history, and handles the interactive elements.

## 📂 Core Architecture Map

- **`run.sh` / `app.py`**: The bootstrap scripts that launch the backend daemon and the native frontend window.
- **`backend/`**: Contains the core intelligence (Agent, MLX Runner, Server, Tools).
- **`frontend/`**: Contains the visual UI (`index.html`, `app.js`, `style.css`).
- **`knowledge_bank/`**: Markdown guides that the agent reads to understand specific technologies before writing code.