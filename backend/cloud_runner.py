"""
Multi-Provider Cloud Runner for Antigravity MLX Agent
======================================================
Supports multiple FREE cloud AI providers so tasks can be divided
across many large models running in parallel:

  Provider      | Models                          | Free Tier
  --------------|--------------------------------|-----------
  Groq          | Llama 3.1 405B, 70B, 8B        | ✅ Free (limits)
  Cerebras      | Llama 3.1 70B, 405B             | ✅ Free (limits)
  Together.ai   | 50+ models incl. 405B           | ✅ $1 free credit
  OpenRouter    | 100+ models, many free          | ✅ Some free
  HuggingFace   | Llama, Mixtral, Qwen, Falcon    | ✅ Free tier

Setup: Add your API keys to secrets.json:
{
    "groq_api_key": "gsk_...",
    "cerebras_api_key": "csk_...",
    "together_api_key": "...",
    "openrouter_api_key": "sk-or-...",
    "hf_api_key": "hf_..."
}

Get free keys at:
  - Groq:      https://console.groq.com/keys
  - Cerebras:  https://cloud.cerebras.ai/
  - Together:  https://api.together.xyz/
  - OpenRouter: https://openrouter.ai/
  - HuggingFace: https://huggingface.co/settings/tokens
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Generator, Optional, Any


# ─────────────────────────────────────────────────────────────────────────────
# Model Registry
# ─────────────────────────────────────────────────────────────────────────────

CLOUD_MODEL_REGISTRY = {
    # ── Groq (fastest inference, free tier) ─────────────────────────────────
    "groq/llama-3.3-70b":      {"provider": "groq",       "model": "llama-3.3-70b-versatile",     "context": 32768},
    "groq/llama-3.1-8b":       {"provider": "groq",       "model": "llama-3.1-8b-instant",        "context": 8192},
    "groq/llama-4-scout":      {"provider": "groq",       "model": "meta-llama/llama-4-scout-17b-16e-instruct", "context": 131072},
    "groq/qwen3-32b":          {"provider": "groq",       "model": "qwen/qwen3-32b",              "context": 32768},
    "groq/qwen3.6-27b":        {"provider": "groq",       "model": "qwen/qwen3.6-27b",            "context": 32768},
    "groq/compound":           {"provider": "groq",       "model": "groq/compound",               "context": 32768},
    "groq/compound-mini":      {"provider": "groq",       "model": "groq/compound-mini",          "context": 32768},
    # ── Cerebras (very fast, free tier) ─────────────────────────────────────
    "cerebras/llama-3.1-70b":  {"provider": "cerebras",   "model": "llama3.1-70b",               "context": 8192},
    "cerebras/llama-3.1-8b":   {"provider": "cerebras",   "model": "llama3.1-8b",                "context": 8192},
    "cerebras/llama-3.3-70b":  {"provider": "cerebras",   "model": "llama-3.3-70b",              "context": 8192},
    # ── Together.ai (50+ models, $1 free credit) ─────────────────────────────
    "together/llama-3.1-405b": {"provider": "together",   "model": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "context": 32768},
    "together/llama-3.1-70b":  {"provider": "together",   "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",  "context": 32768},
    "together/mixtral-8x22b":  {"provider": "together",   "model": "mistralai/Mixtral-8x22B-Instruct-v0.1",         "context": 65536},
    "together/deepseek-coder": {"provider": "together",   "model": "deepseek-ai/DeepSeek-Coder-V2-Instruct",        "context": 32768},
    "together/qwen-72b":       {"provider": "together",   "model": "Qwen/Qwen2.5-72B-Instruct-Turbo",              "context": 32768},
    # ── OpenRouter (many free models) ────────────────────────────────────────
    "openrouter/llama-3.1-405b":      {"provider": "openrouter", "model": "meta-llama/llama-3.1-405b-instruct",    "context": 32768},
    "openrouter/deepseek-r1":         {"provider": "openrouter", "model": "deepseek/deepseek-r1",                  "context": 65536},
    "openrouter/qwen-72b":            {"provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct",            "context": 32768},
    "openrouter/mistral-nemo":        {"provider": "openrouter", "model": "mistralai/mistral-nemo",                "context": 32768, "free": True},
    "openrouter/llama-3.2-3b-free":   {"provider": "openrouter", "model": "meta-llama/llama-3.2-3b-instruct:free", "context": 8192,  "free": True},
    # ── HuggingFace Inference API (read token = inference, write token = Hub) ─
    # Models confirmed working 2026-06-29 via live probe:
    "hf/llama-3.3-70b":        {"provider": "hf",         "model": "meta-llama/Llama-3.3-70B-Instruct",           "context": 32768},
    "hf/qwen-72b":             {"provider": "hf",         "model": "Qwen/Qwen2.5-72B-Instruct",                   "context": 32768},
    "hf/deepseek-r1":          {"provider": "hf",         "model": "deepseek-ai/DeepSeek-R1",                     "context": 65536},
    "hf/deepseek-v3":          {"provider": "hf",         "model": "deepseek-ai/DeepSeek-V3-0324",               "context": 65536},
    # Legacy / may need gated access:
    "hf/llama-3.1-405b":       {"provider": "hf",         "model": "meta-llama/Meta-Llama-3.1-405B-Instruct",     "context": 32768},
    "hf/mixtral-8x22b":        {"provider": "hf",         "model": "mistralai/Mixtral-8x22B-Instruct-v0.1",       "context": 65536},
}


def is_cloud_model(model_id: str) -> bool:
    """Check if a model ID refers to any cloud provider."""
    return any(model_id.startswith(p) for p in ("groq/", "cerebras/", "together/", "openrouter/", "hf/"))


def get_secrets() -> Dict[str, str]:
    """Load all API keys from secrets.json or environment variables."""
    secrets = {}
    # Priority 1: environment variables
    for key in ["GROQ_API_KEY", "CEREBRAS_API_KEY", "TOGETHER_API_KEY", "OPENROUTER_API_KEY", "HF_API_KEY"]:
        val = os.environ.get(key)
        if val:
            secrets[key.lower()] = val
    # Priority 2: secrets.json
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets.json")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r") as f:
                file_secrets = json.load(f)
            # Normalize keys
            for k, v in file_secrets.items():
                secrets[k.lower()] = v
        except Exception:
            pass
    return secrets


def _get_key(secrets: Dict, *keys) -> Optional[str]:
    for key in keys:
        if secrets.get(key):
            return secrets[key]
    return None


def get_hf_write_token() -> Optional[str]:
    """Return the HuggingFace write token for Hub uploads (push_to_hub, save_pretrained, etc.)
    Uses hf_write_token from secrets.json, with fallback to env HF_WRITE_TOKEN."""
    # Check env var first
    env_val = os.environ.get("HF_WRITE_TOKEN")
    if env_val:
        return env_val
    secrets = get_secrets()
    return _get_key(secrets, "hf_write_token", "hf_api_key_2")


def get_hf_read_token() -> Optional[str]:
    """Return the HuggingFace read token for inference (InferenceClient, model downloads)."""
    env_val = os.environ.get("HF_READ_TOKEN") or os.environ.get("HF_API_KEY")
    if env_val:
        return env_val
    secrets = get_secrets()
    return _get_key(secrets, "hf_read_token", "hf_api_key", "hf_token")


# ─────────────────────────────────────────────────────────────────────────────
# Provider Streams
# ─────────────────────────────────────────────────────────────────────────────

def _stream_groq(model_info: Dict, messages: List, max_tokens: int, temperature: float, api_key: str) -> Generator:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        stream = client.chat.completions.create(
            model=model_info["model"], messages=messages,
            max_tokens=max_tokens, temperature=temperature, stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as e:
        yield f"[GROQ ERROR] {e}"


def _stream_cerebras(model_info: Dict, messages: List, max_tokens: int, temperature: float, api_key: str) -> Generator:
    try:
        from cerebras.cloud.sdk import Cerebras
        client = Cerebras(api_key=api_key)
        stream = client.chat.completions.create(
            model=model_info["model"], messages=messages,
            max_tokens=min(max_tokens, 8192), temperature=temperature, stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except ImportError:
        yield "[CEREBRAS ERROR] Package not installed. Run: .venv/bin/pip install cerebras-cloud-sdk"
    except Exception as e:
        yield f"[CEREBRAS ERROR] {e}"


def _stream_together(model_info: Dict, messages: List, max_tokens: int, temperature: float, api_key: str) -> Generator:
    try:
        from together import Together
        client = Together(api_key=api_key)
        stream = client.chat.completions.create(
            model=model_info["model"], messages=messages,
            max_tokens=max_tokens, temperature=temperature, stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except ImportError:
        yield "[TOGETHER ERROR] Package not installed. Run: .venv/bin/pip install together"
    except Exception as e:
        yield f"[TOGETHER ERROR] {e}"


def _stream_openrouter(model_info: Dict, messages: List, max_tokens: int, temperature: float, api_key: str) -> Generator:
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://antigravity-mlx.local",
            "X-Title": "Antigravity MLX Agent"
        }
        payload = {
            "model": model_info["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        with httpx.stream("POST", "https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=payload, timeout=120) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except Exception:
                        pass
    except Exception as e:
        yield f"[OPENROUTER ERROR] {e}"


def _stream_hf(model_info: Dict, messages: List, max_tokens: int, temperature: float, api_key: str) -> Generator:
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(model=model_info["model"], token=api_key)
        response = client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as e:
        yield f"[HF ERROR] {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def stream_cloud(
    model_id: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> Generator[str, None, None]:
    """
    Stream tokens from any supported cloud provider.
    Automatically selects the right API based on model_id prefix.
    """
    model_info = CLOUD_MODEL_REGISTRY.get(model_id)
    if not model_info:
        yield f"[ERROR] Unknown cloud model: '{model_id}'. Available: {list(CLOUD_MODEL_REGISTRY.keys())}"
        return

    provider = model_info["provider"]
    secrets = get_secrets()

    if provider == "groq":
        api_key = _get_key(secrets, "groq_api_key", "groq_api_token")
        if not api_key:
            yield "[GROQ] No API key. Add groq_api_key to secrets.json. Free key at console.groq.com/keys"
            return
        yield from _stream_groq(model_info, messages, max_tokens, temperature, api_key)

    elif provider == "cerebras":
        api_key = _get_key(secrets, "cerebras_api_key", "cerebras_api_token")
        if not api_key:
            yield "[CEREBRAS] No API key. Add cerebras_api_key to secrets.json. Free key at cloud.cerebras.ai"
            return
        yield from _stream_cerebras(model_info, messages, max_tokens, temperature, api_key)

    elif provider == "together":
        api_key = _get_key(secrets, "together_api_key", "together_api_token")
        if not api_key:
            yield "[TOGETHER] No API key. Add together_api_key to secrets.json. Free $1 credit at api.together.xyz"
            return
        yield from _stream_together(model_info, messages, max_tokens, temperature, api_key)

    elif provider == "openrouter":
        api_key = _get_key(secrets, "openrouter_api_key", "openrouter_api_token")
        if not api_key:
            yield "[OPENROUTER] No API key. Add openrouter_api_key to secrets.json. Free at openrouter.ai"
            return
        yield from _stream_openrouter(model_info, messages, max_tokens, temperature, api_key)

    elif provider == "hf":
        # hf_read_token  → used for inference (chat_completion via InferenceClient)
        # hf_write_token → used for Hub uploads (push_to_hub, save pretrained, etc.)
        api_key = _get_key(secrets, "hf_read_token", "hf_api_key", "hf_token", "huggingface_api_key")
        if not api_key:
            yield "[HF] No read token. Add hf_read_token to secrets.json. Free at huggingface.co/settings/tokens"
            return
        yield from _stream_hf(model_info, messages, max_tokens, temperature, api_key)

    else:
        yield f"[ERROR] Unknown provider: {provider}"


def get_available_cloud_models(check_keys: bool = True) -> List[Dict[str, Any]]:
    """Return list of cloud models, optionally marking which ones have API keys configured."""
    secrets = get_secrets() if check_keys else {}
    key_map = {
        "groq":       _get_key(secrets, "groq_api_key"),
        "cerebras":   _get_key(secrets, "cerebras_api_key"),
        "together":   _get_key(secrets, "together_api_key"),
        "openrouter": _get_key(secrets, "openrouter_api_key"),
        "hf":         _get_key(secrets, "hf_read_token", "hf_api_key", "hf_token"),
    }
    return [
        {
            "model_id": mid,
            "provider": info["provider"],
            "model":    info["model"],
            "context":  info["context"],
            "has_key":  bool(key_map.get(info["provider"])),
            "free":     info.get("free", False),
        }
        for mid, info in CLOUD_MODEL_REGISTRY.items()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Parallel Multi-Agent Task Divider
# ─────────────────────────────────────────────────────────────────────────────

async def run_parallel_agents(
    subtasks: List[Dict[str, str]],
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> List[Dict[str, str]]:
    """
    Run multiple subtasks in parallel across different cloud models.
    
    Args:
        subtasks: List of {"model_id": "groq/llama-3.1-70b", "role": "Analyst", "prompt": "..."}
        max_tokens: Max tokens per agent
        temperature: Sampling temperature
    
    Returns:
        List of {"role": "Analyst", "model_id": ..., "result": "..."}
    """
    async def run_one(subtask: Dict) -> Dict:
        model_id = subtask["model_id"]
        role     = subtask.get("role", model_id)
        messages = [{"role": "user", "content": subtask["prompt"]}]
        if subtask.get("system"):
            messages.insert(0, {"role": "system", "content": subtask["system"]})

        print(f"[MultiAgent] Starting agent '{role}' on {model_id}")
        start = time.time()

        # Run the blocking stream in a thread
        result_parts = []
        loop = asyncio.get_event_loop()

        def _collect():
            for token in stream_cloud(model_id, messages, max_tokens, temperature):
                result_parts.append(token)

        await loop.run_in_executor(None, _collect)

        elapsed = time.time() - start
        result_text = "".join(result_parts)
        print(f"[MultiAgent] Agent '{role}' completed in {elapsed:.1f}s ({len(result_text)} chars)")
        return {
            "role":     role,
            "model_id": model_id,
            "result":   result_text,
            "elapsed":  round(elapsed, 1),
        }

    # Run all agents in parallel
    results = await asyncio.gather(*[run_one(st) for st in subtasks], return_exceptions=True)

    cleaned = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            cleaned.append({
                "role": subtasks[i].get("role", f"Agent-{i}"),
                "model_id": subtasks[i].get("model_id", "unknown"),
                "result": f"[ERROR] {r}",
                "elapsed": 0,
            })
        else:
            cleaned.append(r)
    return cleaned
