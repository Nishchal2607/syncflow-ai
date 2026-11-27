"""
Thin wrapper around the Anthropic Messages API.

If no ANTHROPIC_API_KEY is configured, `is_live()` returns False and every
agent in app/agents/*.py falls back to its deterministic demo logic instead
of calling out to a model. This keeps the whole application runnable (and
the demo scenario repeatable) with zero external dependencies.
"""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
API_URL = "https://api.anthropic.com/v1/messages"


def is_live() -> bool:
    return bool(API_KEY)


async def complete_json(system: str, user: str, max_tokens: int = 1500) -> dict | None:
    """
    Calls the Anthropic API asking for a strict JSON response.
    Returns the parsed dict, or None on any failure (caller should fall back
    to deterministic logic — never fabricate data on error).
    """
    if not is_live():
        return None

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system + "\n\nRespond with ONLY valid JSON. No markdown fences, no preamble.",
        "messages": [{"role": "user", "content": user}],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(API_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            text_parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            text = "".join(text_parts).strip()
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
    except Exception:
        return None
