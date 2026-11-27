"""
Small JSON-response client for OpenAI Chat Completions and Anthropic Messages.
"""
import json
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
configured_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
if configured_provider:
    PROVIDER = configured_provider
elif OPENAI_API_KEY:
    PROVIDER = "openai"
elif ANTHROPIC_API_KEY:
    PROVIDER = "anthropic"
else:
    PROVIDER = "openai"

if PROVIDER == "openai":
    API_KEY = OPENAI_API_KEY
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    API_URL = "https://api.openai.com/v1/chat/completions"
elif PROVIDER == "anthropic":
    API_KEY = ANTHROPIC_API_KEY
    MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    API_URL = "https://api.anthropic.com/v1/messages"
else:
    API_KEY = ""
    MODEL = ""
    API_URL = ""
    logger.error("Unsupported LLM_PROVIDER %r; choose 'openai' or 'anthropic'.", PROVIDER)


def is_live() -> bool:
    return PROVIDER in {"openai", "anthropic"} and bool(API_KEY)


async def complete_json(system: str, user: str, max_tokens: int = 1500) -> dict | None:
    """Request and parse a JSON response from the configured model provider."""
    if not is_live():
        return None

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if PROVIDER == "openai":
                headers = {
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": MODEL,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": system + "\n\nRespond with ONLY valid JSON. No markdown fences or preamble.",
                        },
                        {"role": "user", "content": user},
                    ],
                }
                response = await client.post(API_URL, headers=headers, json=body)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("OpenAI response did not contain text content")
                return json.loads(content)

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
            response = await client.post(API_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            text_parts = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
            return json.loads("".join(text_parts).strip().replace("```json", "").replace("```", "").strip())
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        logger.exception("%s model request failed", PROVIDER)
        return None
