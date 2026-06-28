import os
import json
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .tools import set_workspace, get_workspace
from .mlx_runner import (
    runner, 
    list_downloaded_models, 
    start_model_download, 
    get_download_status
)
from .agent import run_agent_loop, AGENT_STATE

# Popular models to recommend
POPULAR_MODELS = [
    # Cloud Models via Groq (Free API key at console.groq.com)
    {
        "id": "groq/llama-3.1-405b",
        "name": "☁️ Llama 3.1 405B (Groq Cloud — FREE)",
        "description": "Meta's most powerful open model — 405B parameters. Best for complex analysis and deep reasoning. Add groq_api_key to secrets.json. Get free key at console.groq.com/keys",
        "size": "☁️ Cloud — No download needed"
    },
    {
        "id": "groq/llama-3.3-70b",
        "name": "☁️ Llama 3.3 70B (Groq Cloud — FREE)",
        "description": "Best balance of speed and intelligence. 300+ tokens/sec via Groq. Excellent for complex tasks. Free tier available.",
        "size": "☁️ Cloud — No download needed"
    },
    {
        "id": "groq/gemma2-9b",
        "name": "☁️ Gemma 2 9B (Groq Cloud — FREE)",
        "description": "Google's Gemma 2 9B on Groq hardware — fast, smart, great for coding via the cloud.",
        "size": "☁️ Cloud — No download needed"
    },
    # Local Models (MLX — Apple Silicon)
    {
        "id": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "name": "💻 Qwen 2.5 Coder 7B (Local — Best for 16GB)",
        "description": "Best local model for your M4 Mac. Fast, precise tool use, great for coding. Already downloaded.",
        "size": "approx 4.5 GB"
    },
    {
        "id": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        "name": "💻 Qwen 2.5 Coder 1.5B (Local — Ultra Fast)",
        "description": "Ultra-lightweight, 100+ tokens/second. Great for quick tasks.",
        "size": "approx 1.0 GB"
    },
    {
        "id": "mlx-community/Llama-3.1-8B-Instruct-4bit",
        "name": "💻 Llama 3.1 8B (Local)",
        "description": "Excellent general purpose reasoning model by Meta, optimized for Apple Silicon.",
        "size": "approx 4.8 GB"
    },
    {
        "id": "mlx-community/Llama-3.2-3B-Instruct-4bit",
        "name": "💻 Llama 3.2 3B (Local)",
        "description": "Fast and lightweight reasoning model, perfect for general chat.",
        "size": "approx 2.0 GB"
    }
]

app = FastAPI(title="Antigravity MLX Local Agent")

# Pydantic models for API requests
class WorkspaceUpdateRequest(BaseModel):
    path: str

class DownloadRequest(BaseModel):
    model_id: str

class GmailConfigRequest(BaseModel):
    email: str
    app_password: str

class SpeakRequest(BaseModel):
    text: str

class CopyRequest(BaseModel):
    text: str

class SiriRequest(BaseModel):
    prompt: str
    model_id: str = "mlx-community/Qwen2.5-7B-Instruct-4bit"

class ChatHistoryRequest(BaseModel):
    session_id: str
    title: str = "New Chat"
    history: List[Dict[str, Any]]

class SwarmRunRequest(BaseModel):
    prompt: str
    model_id: str

# API Routes

@app.get("/api/models")
def get_models_route():
    """List downloaded models and recommended models."""
    downloaded = list_downloaded_models()
    
    models_list = []
    # Merge downloaded flag onto popular models
    for pop in POPULAR_MODELS:
        m_id = pop["id"]
        is_dl = m_id in downloaded
        models_list.append({
            **pop,
            "downloaded": is_dl
        })
        if is_dl:
            downloaded.remove(m_id)
            
    # Add any other downloaded models not in popular list
    for dl in downloaded:
        models_list.append({
            "id": dl,
            "name": dl.split("/")[-1].replace("-4bit", " (4-bit)").replace("-Instruct", ""),
            "description": "Custom downloaded local model.",
            "size": "Unknown",
            "downloaded": True
        })
        
    return {
        "models": models_list,
        "active_model": runner.current_model_id
    }

@app.post("/api/download")
def download_model_route(req: DownloadRequest):
    """Trigger background download of a Hugging Face MLX model."""
    status = start_model_download(req.model_id)
    return {"status": status, "model_id": req.model_id}

@app.get("/api/download/status")
def download_status_route(model_id: str):
    """Check current download status of a model."""
    status = get_download_status(model_id)
    if not status:
        return {"status": "idle", "progress": 0, "error": None}
    return status

@app.get("/api/workspace")
def get_workspace_route():
    """Get active workspace directory."""
    return {"path": get_workspace()}

@app.post("/api/workspace")
def set_workspace_route(req: WorkspaceUpdateRequest):
    """Update active workspace directory."""
    try:
        set_workspace(req.path)
        return {"status": "success", "path": get_workspace()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/gmail-config")
def get_gmail_config_route():
    """Retrieve the saved Gmail configuration email (password hidden)."""
    config_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/gmail_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"email": data.get("email", "")}
        except:
            return {"email": ""}
    return {"email": ""}

@app.post("/api/gmail-config")
def set_gmail_config_route(req: GmailConfigRequest):
    """Save the Gmail address and App Password to local config."""
    config_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/gmail_config.json"
    try:
        data = {
            "email": req.email,
            "app_password": req.app_password
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"status": "success", "email": req.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/swarm/run")
async def run_swarm_route(req: SwarmRunRequest):
    """Run the swarm multi-agent benchmark on the given prompt."""
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))
        from swarm_benchmark import run_benchmarks
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_benchmarks, req.prompt, req.model_id)
        
        report_path = os.path.join(get_workspace(), "swarm_benchmark_report.md")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_md = f.read()
            return {"status": "success", "report": report_md}
        else:
            return {"status": "error", "message": "Benchmark report was not generated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/restart")
def restart_server_route():
    """Restart the Python backend process and UI window."""
    print("[Server] Restart requested via UI. Rebooting application...")
    import sys
    import os
    # We delay execution slightly so the HTTP response can be sent first
    def do_restart():
        os.execv(sys.executable, ['python'] + sys.argv)
    
    import threading
    threading.Timer(0.5, do_restart).start()
    return {"status": "success", "message": "Restarting..."}

import re

@app.post("/api/speak")
def speak_route(req: SpeakRequest):
    """Use macOS native 'say' command to read text out loud."""
    # Strip markdown code blocks so it doesn't read python code verbatim
    text = re.sub(r'```.*?```', ' [Code block omitted] ', req.text, flags=re.DOTALL)
    # Strip inline code ticks
    text = text.replace('`', '')
    # Strip asterisks
    text = text.replace('*', '')
    
    try:
        # Run in background
        subprocess.Popen(['say', text])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop-speak")
def stop_speak_route():
    """Kill any active 'say' processes."""
    try:
        subprocess.run(['killall', 'say'], capture_output=True)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/api/copy")
def copy_to_clipboard_route(req: CopyRequest):
    """Use macOS native 'pbcopy' to securely write to the system clipboard."""
    try:
        subprocess.run(['pbcopy'], input=req.text.encode('utf-8'), check=True)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/siri")
async def siri_route(req: SiriRequest):
    """REST endpoint for Siri Shortcuts to speak directly to the agent."""
    AGENT_STATE["stop_requested"] = False
    
    final_text = []
    
    async def mock_ws_callback(packet: Dict[str, Any]):
        if packet.get("type") == "final_response":
            final_text.append(packet.get("text", ""))
        elif packet.get("type") == "error":
            final_text.append(f"Error: {packet.get('message')}")

    try:
        await run_agent_loop(
            user_prompt=req.prompt,
            model_id=req.model_id,
            ws_send_callback=mock_ws_callback
        )
        
        response_text = "".join(final_text)
        if not response_text:
            response_text = "I completed the task but have no spoken response."
            
        return {"status": "success", "response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
def stop_agent_route():
    """Interrupt the currently running agent loop."""
    AGENT_STATE["stop_requested"] = True
    try:
        from .tools import kill_active_subprocesses
        kill_active_subprocesses()
    except Exception as e:
        print(f"[Stop] Error killing active subprocesses: {e}")
    return {"status": "success", "message": "Stop signal sent"}

@app.get("/api/system-stats")
def get_system_stats_route():
    """Retrieve basic Mac hardware specs and load metrics."""
    try:
        # Get 1-minute load average
        load1, load5, load15 = os.getloadavg()
        
        # Get active RAM usage info using vm_stat (Mac-specific)
        mem_used_pct = 0.0
        try:
            vm_stat = subprocess.check_output(["vm_stat"]).decode("utf-8")
            pages_free = 0
            pages_active = 0
            pages_inactive = 0
            pages_speculative = 0
            pages_wired = 0
            
            for line in vm_stat.split("\n"):
                if "Pages free:" in line:
                    pages_free = int(line.split()[-1].replace(".", ""))
                elif "Pages active:" in line:
                    pages_active = int(line.split()[-1].replace(".", ""))
                elif "Pages inactive:" in line:
                    pages_inactive = int(line.split()[-1].replace(".", ""))
                elif "Pages speculative:" in line:
                    pages_speculative = int(line.split()[-1].replace(".", ""))
                elif "Pages wired down:" in line:
                    pages_wired = int(line.split()[-1].replace(".", ""))
            
            # Page size is typically 4096 bytes or 16384 bytes on Apple Silicon
            # Let's just calculate percentage based on active pages vs total
            total_pages = pages_free + pages_active + pages_inactive + pages_speculative + pages_wired
            used_pages = pages_active + pages_wired
            if total_pages > 0:
                mem_used_pct = round((used_pages / total_pages) * 100, 1)
        except Exception as e:
            print(f"[Stats] Error calculating RAM: {e}")
            mem_used_pct = 50.0 # fallback representation
            
        return {
            "cpu_load": round(load1 * 10, 1), # Scaled load representation
            "ram_used_pct": mem_used_pct,
            "active_model": runner.current_model_id or "None",
            "cores": os.cpu_count()
        }
    except Exception as e:
        return {
            "cpu_load": 0.0,
            "ram_used_pct": 0.0,
            "active_model": runner.current_model_id or "None",
            "cores": os.cpu_count()
        }

@app.get("/api/sessions")
def get_sessions_route():
    """Retrieve all chat sessions."""
    sessions_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/chat_sessions.json"
    if os.path.exists(sessions_path):
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"sessions": list(reversed(data.get("sessions", [])))}
        except:
            pass
    return {"sessions": []}

@app.get("/api/history")
def get_history_route(session_id: str = ""):
    """Retrieve saved chat history for a session."""
    sessions_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/chat_sessions.json"
    if os.path.exists(sessions_path):
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for s in data.get("sessions", []):
                    if s.get("id") == session_id:
                        return {"history": s.get("history", [])}
        except:
            pass
    return {"history": []}

@app.post("/api/history")
def save_history_route(req: ChatHistoryRequest):
    """Save chat history for a session."""
    sessions_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/chat_sessions.json"
    data = {"sessions": []}
    
    if os.path.exists(sessions_path):
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
            
    sessions = data.get("sessions", [])
    found = False
    for s in sessions:
        if s.get("id") == req.session_id:
            s["history"] = req.history
            if len(req.history) > 0 and s.get("title", "New Chat") == "New Chat":
                s["title"] = req.history[0].get("content", "")[:30] + "..."
            elif req.title != "New Chat":
                s["title"] = req.title
            found = True
            break
            
    if not found:
        title = req.title
        if title == "New Chat" and len(req.history) > 0:
            title = req.history[0].get("content", "")[:30] + "..."
        sessions.append({
            "id": req.session_id,
            "title": title,
            "history": req.history
        })
        
    data["sessions"] = sessions
    
    try:
        with open(sessions_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
def delete_session_route(session_id: str):
    """Delete a chat session entirely."""
    sessions_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/chat_sessions.json"
    if os.path.exists(sessions_path):
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions = data.get("sessions", [])
            filtered = [s for s in sessions if s.get("id") != session_id]
            data["sessions"] = filtered
            with open(sessions_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success"}

class SessionMetadataRequest(BaseModel):
    pinned: Optional[bool] = None
    archived: Optional[bool] = None

@app.post("/api/sessions/{session_id}/metadata")
def update_session_metadata(session_id: str, req: SessionMetadataRequest):
    """Update metadata like pinned or archived for a session."""
    sessions_path = "/Users/rukhvinder/.gemini/antigravity/scratch/mlx_agent/chat_sessions.json"
    if os.path.exists(sessions_path):
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions = data.get("sessions", [])
            for s in sessions:
                if s.get("id") == session_id:
                    if req.pinned is not None:
                        s["pinned"] = req.pinned
                    if req.archived is not None:
                        s["archived"] = req.archived
                    break
            with open(sessions_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success"}

@app.get("/api/project-overview")
def get_project_overview_route():
    """Retrieve project_overview.md from the workspace if it exists."""
    from fastapi.responses import JSONResponse
    workspace = get_workspace()
    overview_path = os.path.join(workspace, "project_overview.md")
    
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    if os.path.exists(overview_path):
        try:
            with open(overview_path, "r", encoding="utf-8") as f:
                return JSONResponse(content={"content": f.read()}, headers=headers)
        except Exception as e:
            return JSONResponse(content={"content": f"Error reading overview: {str(e)}"}, headers=headers)
    return JSONResponse(content={"content": "No project_overview.md found in the active workspace. Let the agent know if you'd like to create one!"}, headers=headers)

# WebSocket Endpoint for Chat & Agent execution

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected.")
    
    incoming_queue = asyncio.Queue()
    
    async def read_ws():
        try:
            while True:
                data_str = await websocket.receive_text()
                await incoming_queue.put(json.loads(data_str))
        except WebSocketDisconnect:
            print("[WebSocket] Reader disconnected.")
        except Exception as e:
            print(f"[WebSocket] Reader exception: {e}")
            
    reader_task = asyncio.create_task(read_ws())
    
    try:
        while True:
            # Wait for client prompt details from the queue
            data = await incoming_queue.get()
            
            # If it's a user injection during active generation, ignore it here
            # (it is handled directly inside run_agent_loop)
            if data.get("type") == "user_injection":
                continue
                
            prompt = data.get("prompt")
            model_id = data.get("model_id")
            temperature = float(data.get("temperature", 0.2))
            chat_history = data.get("history", [])
            image_path = data.get("image_path")  # Optional: absolute path to image file
            
            if not prompt or not model_id:
                await websocket.send_json({"type": "error", "message": "Missing prompt or model_id."})
                continue
                
            # Define helper sender function
            async def ws_sender(packet: dict):
                await websocket.send_json(packet)
                
            print(f"[WebSocket] User Prompt: '{prompt[:50]}...' using model: {model_id}")
            
            # Start the agent execution loop, passing the incoming queue for steering
            await run_agent_loop(
                user_prompt=prompt,
                model_id=model_id,
                ws_send_callback=ws_sender,
                history=chat_history,
                temp=temperature,
                image_path=image_path,
                incoming_queue=incoming_queue
            )
            
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[WebSocket] Exception: {str(e)}")
        try:
            await websocket.send_json({"type": "error", "message": f"Server connection error: {str(e)}"})
        except:
            pass
    finally:
        reader_task.cancel()

# Serve static frontend files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
def read_root():
    """Serve index.html at root url."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": f"Frontend index.html not found in {frontend_dir}"}

# Mount static folder for CSS and JS assets
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
