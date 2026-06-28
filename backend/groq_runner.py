"""
Groq Cloud Runner for Antigravity MLX Agent
============================================
Provides access to large cloud models (Llama 3.1 405B, 70B, etc.) via the Groq API.
Groq offers free tier with very high speed inference (300+ tokens/sec).

Get a free API key at: https://console.groq.com/keys
"""

import os
import json
from typing import Dict, List, Generator, Optional, Any

# Map of friendly model names to Groq model IDs
GROQ_MODELS = {
    "groq/llama-3.1-405b":    "llama-3.1-405b-reasoning",
    "groq/llama-3.1-70b":     "llama-3.1-70b-versatile",
    "groq/llama-3.1-8b":      "llama-3.1-8b-instant",
    "groq/llama-3.3-70b":     "llama-3.3-70b-versatile",
    "groq/mixtral-8x7b":      "mixtral-8x7b-32768",
    "groq/gemma2-9b":         "gemma2-9b-it",
}


def is_groq_model(model_id: str) -> bool:
    """Check if a model ID refers to a Groq cloud model."""
    return model_id.startswith("groq/")


def get_groq_api_key() -> Optional[str]:
    """Get the Groq API key from secrets.json or environment."""
    # Try environment variable first
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    # Try secrets.json
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets.json")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r") as f:
                secrets = json.load(f)
            return secrets.get("groq_api_key") or secrets.get("GROQ_API_KEY")
        except Exception:
            pass
    return None


def stream_groq(
    model_id: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> Generator[str, None, None]:
    """
    Stream tokens from a Groq cloud model.
    
    Args:
        model_id: Groq model identifier (e.g. 'groq/llama-3.1-70b')
        messages: OpenAI-format message list
        max_tokens: Max tokens to generate
        temperature: Sampling temperature
        
    Yields:
        Text chunks as they stream in
    """
    try:
        from groq import Groq
    except ImportError:
        yield "[ERROR] Groq package not installed. Run: .venv/bin/pip install groq"
        return

    api_key = get_groq_api_key()
    if not api_key:
        yield (
            "[ERROR] No Groq API key found. Please:\n"
            "1. Go to https://console.groq.com/keys and create a free API key\n"
            "2. Add it to secrets.json as: {\"groq_api_key\": \"gsk_...\"}\n"
            "3. Or set the GROQ_API_KEY environment variable"
        )
        return

    # Resolve the actual Groq model ID
    groq_model = GROQ_MODELS.get(model_id)
    if not groq_model:
        # Try direct model ID (user may have passed the raw Groq model string)
        groq_model = model_id.replace("groq/", "")

    client = Groq(api_key=api_key)

    try:
        # Filter system messages for models that don't support them (405b uses user-injected system)
        filtered_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("system", "user", "assistant") and content:
                filtered_messages.append({"role": role, "content": content})

        stream = client.chat.completions.create(
            model=groq_model,
            messages=filtered_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower():
            yield f"[GROQ RATE LIMIT] Too many requests. Wait a moment and try again. Details: {error_msg}"
        elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            yield f"[GROQ AUTH ERROR] Invalid API key. Please check your groq_api_key in secrets.json. Details: {error_msg}"
        elif "model_not_found" in error_msg.lower():
            yield f"[GROQ ERROR] Model '{groq_model}' not found. Available: {list(GROQ_MODELS.values())}"
        else:
            yield f"[GROQ ERROR] {error_msg}"


def list_groq_models() -> List[Dict[str, Any]]:
    """Return list of available Groq models for the frontend."""
    return [
        {
            "id": "groq/llama-3.1-405b",
            "name": "☁️ Llama 3.1 405B (Groq Cloud)",
            "description": "Meta's most powerful open model. 405 billion parameters. Excellent for complex analysis, architecture decisions, and multi-step reasoning. Requires free Groq API key.",
            "size": "Cloud (requires GROQ_API_KEY)",
            "is_cloud": True,
        },
        {
            "id": "groq/llama-3.3-70b",
            "name": "☁️ Llama 3.3 70B (Groq Cloud)",
            "description": "Best balance of speed and intelligence. 70B parameters, 300+ tokens/sec. Great for most complex tasks. Requires free Groq API key.",
            "size": "Cloud (requires GROQ_API_KEY)",
            "is_cloud": True,
        },
        {
            "id": "groq/llama-3.1-8b",
            "name": "☁️ Llama 3.1 8B Fast (Groq Cloud)",
            "description": "Extremely fast cloud inference for simple tasks. Comparable speed to local models but with Groq's hardware.",
            "size": "Cloud (requires GROQ_API_KEY)",
            "is_cloud": True,
        },
        {
            "id": "groq/gemma2-9b",
            "name": "☁️ Gemma 2 9B (Groq Cloud)",
            "description": "Google's Gemma 2 9B via Groq — fast, smart, great for coding tasks.",
            "size": "Cloud (requires GROQ_API_KEY)",
            "is_cloud": True,
        },
    ]
