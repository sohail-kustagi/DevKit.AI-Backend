"""
tests/test_self_healing.py — Phase 3 Tests

Tests:
  - Fallback is triggered on primary 500
  - Fallback is triggered on primary 429
  - VisionUnavailableError raised when vision primary fails (no fallback)
  - AgentFailureError raised when both primary and fallback fail
  - call_with_fallback waits >= SELF_HEALING_WAIT_SECONDS before fallback
  - staggered_calls completes in expected minimum time
"""
import pytest
import time
import asyncio
from unittest.mock import patch, AsyncMock

from core.self_healing import call_with_fallback, VisionUnavailableError, AgentFailureError
from core.nim_client import NIMError
from core.rate_limiter import staggered_calls
from constants.defs import SELF_HEALING_WAIT_SECONDS


@pytest.mark.asyncio
@patch("core.self_healing.nim_chat")
async def test_fallback_on_primary_500(mock_nim_chat):
    """Primary returns 500 → assert fallback model is called."""
    # First call throws 500, second call succeeds
    mock_nim_chat.side_effect = [
        NIMError(status_code=500, message="Internal Server Error"),
        {"choices": [{"message": {"content": "fallback success"}}]}
    ]
    
    start = time.time()
    response = await call_with_fallback(
        agent_role="triage",
        messages=[{"role": "user", "content": "Hi"}]
    )
    elapsed = time.time() - start
    
    assert response["choices"][0]["message"]["content"] == "fallback success"
    assert mock_nim_chat.call_count == 2
    # Ensure it waited the backoff period
    assert elapsed >= SELF_HEALING_WAIT_SECONDS


@pytest.mark.asyncio
@patch("core.self_healing.nim_chat")
async def test_fallback_on_primary_429(mock_nim_chat):
    """Primary returns 429 → assert fallback model is called."""
    mock_nim_chat.side_effect = [
        NIMError(status_code=429, message="Rate Limited"),
        {"choices": [{"message": {"content": "fallback success"}}]}
    ]
    
    response = await call_with_fallback(
        agent_role="triage",
        messages=[{"role": "user", "content": "Hi"}]
    )
    assert response["choices"][0]["message"]["content"] == "fallback success"
    assert mock_nim_chat.call_count == 2


@pytest.mark.asyncio
@patch("core.self_healing.nim_chat")
async def test_vision_unavailable_error(mock_nim_chat):
    """Vision primary fails → VisionUnavailableError raised (no fallback)."""
    mock_nim_chat.side_effect = NIMError(status_code=500, message="Vision Down")
    
    with pytest.raises(VisionUnavailableError):
        await call_with_fallback(
            agent_role="vision",
            messages=[{"role": "user", "content": "Hi"}]
        )


@pytest.mark.asyncio
@patch("core.self_healing.nim_chat")
async def test_agent_failure_error_both_fail(mock_nim_chat):
    """Both primary and fallback fail → AgentFailureError raised."""
    mock_nim_chat.side_effect = [
        NIMError(status_code=500, message="Primary Down"),
        NIMError(status_code=500, message="Fallback Down")
    ]
    
    with pytest.raises(AgentFailureError):
        await call_with_fallback(
            agent_role="triage",
            messages=[{"role": "user", "content": "Hi"}]
        )


@pytest.mark.asyncio
async def test_staggered_calls_timing():
    """staggered_calls with 3 items at 0.5s delay takes >= 1.0s total."""
    async def mock_coro(val):
        return val

    coros = [mock_coro(1), mock_coro(2), mock_coro(3)]
    
    start = time.time()
    results = await staggered_calls(coros, delay_seconds=0.5)
    elapsed = time.time() - start
    
    assert results == [1, 2, 3]
    assert elapsed >= 1.0
