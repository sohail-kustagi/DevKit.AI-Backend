"""
tests/test_nim_client.py — Phase 1 & 3 Tests

Tests:
  - Phase 1: NIM API is reachable and returns a non-5xx response
  - Phase 3: nim_chat returns a valid response
  - Phase 3: nim_chat stream=True yields tokens
  - Phase 3: nim_chat raises NIMError on 500/401
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from core.nim_client import nim_chat, NIMError
from constants.defs import NIM_API_KEY, NIM_BASE_URL


@pytest.mark.asyncio
async def test_nim_reachable():
    """Phase 1: Verify NIM API endpoint is reachable (non-5xx)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{NIM_BASE_URL.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {NIM_API_KEY}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_nim_chat_full_response():
    """Phase 3: nim_chat returns a valid completion dict on success."""
    response = await nim_chat(
        model="meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": "Say 'hello world'"}],
        stream=False,
        max_tokens=10
    )
    assert "choices" in response
    assert len(response["choices"]) > 0
    assert "message" in response["choices"][0]


@pytest.mark.asyncio
async def test_nim_chat_streaming():
    """Phase 3: nim_chat with stream=True yields at least one token string."""
    stream_gen = await nim_chat(
        model="meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": "Count from 1 to 3"}],
        stream=True,
        max_tokens=20
    )
    tokens = []
    async for token in stream_gen:
        tokens.append(token)
    
    assert len(tokens) > 0, "No tokens yielded from stream"
    assert any("1" in t for t in tokens), "Expected stream output to contain '1'"


@pytest.mark.asyncio
@patch("core.nim_client.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_nim_chat_raises_nim_error_on_401(mock_post):
    """Phase 3: NIMError is raised when NIM returns a 401."""
    mock_post.return_value.status_code = 401
    mock_post.return_value.text = "Unauthorized"
    
    with pytest.raises(NIMError) as exc_info:
        await nim_chat(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "Hi"}],
            stream=False
        )
    assert exc_info.value.status_code == 401
