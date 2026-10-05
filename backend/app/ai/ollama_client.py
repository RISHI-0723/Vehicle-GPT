"""Thin async adapter over Ollama's /api/chat endpoint.

Contract (see SPRINT_4_REPORT.md section 5):
    POST {OLLAMA_BASE_URL}/api/chat
    {"model": OLLAMA_MODEL, "messages": [...], "stream": false}

AI_TIMEOUT_SECONDS is a TOTAL wall-clock deadline for the request, not just
a connect timeout. asyncio.wait_for enforces that; the underlying httpx
client also gets a matching timeout so nothing can hang past the deadline.

The browser never talks to Ollama directly -- only this module does, and
only the backend process holds OLLAMA_BASE_URL.
"""
import asyncio
import logging
from typing import Any

import httpx

from app.ai.config import ai_settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base class for all Ollama adapter failures."""


class OllamaUnavailableError(OllamaError):
    """Ollama could not be reached at all."""


class OllamaTimeoutError(OllamaError):
    """The total wall-clock deadline was exceeded."""


class OllamaResponseError(OllamaError):
    """Ollama responded, but the response was malformed or an HTTP error."""


async def check_ollama_available(timeout_seconds: float = 2.0) -> bool:
    """Cheap, short-timeout reachability check.

    Used both at startup (non-blocking) and lazily before each AI request,
    since Ollama may start or stop between requests.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(f"{ai_settings.OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False
    except Exception:  # pragma: no cover - defensive: never let a health check crash startup
        return False


async def chat(messages: list[dict[str, str]], *, timeout_seconds: float | None = None) -> str:
    """Call Ollama's /api/chat with stream=false and return the assistant's raw text content.

    Raises OllamaUnavailableError, OllamaTimeoutError, or OllamaResponseError on any
    failure. Callers are expected to catch these and fall back to the deterministic
    formatter -- a malformed or absent Ollama response must never crash the endpoint.
    """
    deadline = ai_settings.AI_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    connect_timeout = min(5.0, deadline)
    payload: dict[str, Any] = {
        "model": ai_settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    async def _request() -> dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(deadline, connect=connect_timeout)
        ) as client:
            response = await client.post(f"{ai_settings.OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()

    try:
        data = await asyncio.wait_for(_request(), timeout=deadline)
    except asyncio.TimeoutError as exc:
        raise OllamaTimeoutError("Ollama request exceeded the total timeout") from exc
    except httpx.ConnectError as exc:
        raise OllamaUnavailableError("Ollama is not reachable") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaResponseError(f"Ollama returned HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(str(exc)) from exc

    try:
        content = data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaResponseError("Malformed Ollama response: missing message.content") from exc

    if not isinstance(content, str) or not content.strip():
        raise OllamaResponseError("Malformed Ollama response: empty content")

    return content
