import os
import gc
import threading
from typing import Dict, List, Generator, Optional
from huggingface_hub import snapshot_download
from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler

# Global download tracking
download_status: Dict[str, Dict[str, Any]] = {}
download_status_lock = threading.Lock()

# Global runner instance
class MLXRunner:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.current_model_id: Optional[str] = None
        self.lock = threading.Lock()

    def load_model(self, model_id: str):
        with self.lock:
            if self.current_model_id == model_id and self.model is not None:
                return self.model, self.tokenizer

            print(f"[MLX] Loading model '{model_id}'...")
            
            # Unload previous model to free RAM
            if self.model is not None:
                print(f"[MLX] Unloading model '{self.current_model_id}' to free unified memory.")
                self.model = None
                self.tokenizer = None
                gc.collect()
                # MLX metal cache clearing is handled automatically by Python GC releasing the backend buffers
            
            # Load new model
            try:
                self.model, self.tokenizer = load(model_id)
                self.current_model_id = model_id
                print(f"[MLX] Successfully loaded '{model_id}'!")
                return self.model, self.tokenizer
            except Exception as e:
                print(f"[MLX] Error loading model '{model_id}': {str(e)}")
                self.model = None
                self.tokenizer = None
                self.current_model_id = None
                gc.collect()
                raise e

    def generate_stream(self, model_id: str, prompt: str, temp: float = 0.7, max_tokens: int = 2048, stop_sequences: list = None) -> Generator[str, None, None]:
        """Loads the model if needed and yields generated tokens one by one.
        Supports stop_sequences: generation halts when any stop string appears in accumulated output."""
        model, tokenizer = self.load_model(model_id)
        
        # Construct sampler for temperature
        sampler = make_sampler(temp=temp)
        
        if stop_sequences is None:
            stop_sequences = []
        
        accumulated = ""
        
        try:
            for response in stream_generate(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                sampler=sampler,
                max_tokens=max_tokens
            ):
                token = response.text
                accumulated += token
                
                # Check for stop sequences
                should_stop = False
                for stop_seq in stop_sequences:
                    if stop_seq in accumulated:
                        # Yield only up to and including the stop sequence
                        idx = accumulated.index(stop_seq) + len(stop_seq)
                        # Calculate what we already yielded vs what's new
                        already_yielded = len(accumulated) - len(token)
                        remaining = accumulated[already_yielded:idx]
                        if remaining:
                            yield remaining
                        should_stop = True
                        break
                
                if should_stop:
                    break
                
                yield token
        except Exception as e:
            yield f"\n[MLX Generation Error: {str(e)}]"

# Singleton runner
runner = MLXRunner()

def list_downloaded_models() -> List[str]:
    """Scan the standard Hugging Face hub cache directory for MLX models."""
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    if not os.path.exists(hf_cache):
        return []
    
    downloaded = []
    try:
        for folder in os.listdir(hf_cache):
            # MLX models are typically uploaded under the mlx-community organization
            # and directories are named like models--mlx-community--model-name
            if folder.startswith("models--"):
                parts = folder.split("--")
                if len(parts) >= 3:
                    author = parts[1]
                    repo = "--".join(parts[2:])
                    model_id = f"{author}/{repo}"
                    
                    # Verify snapshot directory contains files
                    snapshot_dir = os.path.join(hf_cache, folder, "snapshots")
                    if os.path.exists(snapshot_dir) and os.listdir(snapshot_dir):
                        downloaded.append(model_id)
    except Exception as e:
        print(f"[MLX Hub Scanner] Error scanning HF cache: {str(e)}")
        
    return sorted(list(set(downloaded)))

def run_download_thread(model_id: str):
    """Worker function to download model in the background."""
    global download_status
    
    with download_status_lock:
        download_status[model_id] = {
            "status": "downloading",
            "progress": 0,
            "error": None
        }
        
    try:
        print(f"[HF Download] Starting download for: {model_id}")
        
        # We download using snapshot_download. This is synchronous.
        # It handles resumption and local caching.
        snapshot_download(
            repo_id=model_id,
            # We can ignore large unused files like original safetensors if MLX weights are what we want
            # but usually MLX repos only contain MLX weights (safetensors or npz) and config.json
        )
        
        with download_status_lock:
            download_status[model_id] = {
                "status": "completed",
                "progress": 100,
                "error": None
            }
        print(f"[HF Download] Completed download for: {model_id}")
    except Exception as e:
        with download_status_lock:
            download_status[model_id] = {
                "status": "failed",
                "progress": 0,
                "error": str(e)
            }
        print(f"[HF Download] Failed to download {model_id}: {str(e)}")

def start_model_download(model_id: str) -> str:
    """Trigger background thread to download a model."""
    global download_status
    
    with download_status_lock:
        status = download_status.get(model_id)
        if status and status["status"] in ["downloading", "completed"]:
            return status["status"]
            
    thread = threading.Thread(target=run_download_thread, args=(model_id,))
    thread.daemon = True
    thread.start()
    return "started"

def get_download_status(model_id: str) -> Optional[dict]:
    """Retrieve current download status of a model."""
    with download_status_lock:
        return download_status.get(model_id)
