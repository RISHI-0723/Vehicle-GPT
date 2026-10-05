"""Sprint 4: Ollama /api/chat adapter tests.

These tests never require a live Ollama instance -- httpx.AsyncClient's
post/get methods are monkeypatched so the adapter's request-building and
error-classification logic can be verified in isolation.
"""
import asyncio

import httpx
import pytest

from app.ai.config import ai_settings
from app.ai.ollama_client import (
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    chat,
    check_ollama_available,
)


def _ok_response(url: str, body: dict) -> httpx.Response:
    return httpx.Response(200, json=body, request=httpx.Request("POST", url))


@pytest.mark.asyncio
async def test_chat_sends_the_documented_request_shape(monkeypatch):
    captured = {}

    async def fake_post(self, url, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return _ok_response(url, {"message": {"content": '{"answer": "hi"}'}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    content = await chat([{"role": "system", "content": "sys"}, {"role": "user", "content": "hello"}])

    assert content == '{"answer": "hi"}'
    assert captured["url"] == f"{ai_settings.OLLAMA_BASE_URL}/api/chat"
    assert captured["json"]["model"] == ai_settings.OLLAMA_MODEL
    assert captured["json"]["stream"] is False
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]


@pytest.mark.asyncio
async def test_chat_raises_on_connection_error(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        raise httpx.ConnectError("refused", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(OllamaUnavailableError):
        await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_timeout_error_when_total_deadline_exceeded(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        await asyncio.sleep(10)
        return _ok_response(url, {"message": {"content": "{}"}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(OllamaTimeoutError):
        await chat([{"role": "user", "content": "hi"}], timeout_seconds=0.05)


@pytest.mark.asyncio
async def test_chat_raises_response_error_for_malformed_json_shape(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        return _ok_response(url, {"unexpected": "shape"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(OllamaResponseError):
        await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_response_error_for_empty_content(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        return _ok_response(url, {"message": {"content": "   "}})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(OllamaResponseError):
        await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_response_error_for_http_error_status(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(500, json={"error": "boom"}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(OllamaResponseError):
        await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_check_ollama_available_true_on_200(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, json={"models": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await check_ollama_available() is True


@pytest.mark.asyncio
async def test_check_ollama_available_false_when_unreachable(monkeypatch):
    async def fake_get(self, url, **kwargs):
        raise httpx.ConnectError("refused", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await check_ollama_available() is False
