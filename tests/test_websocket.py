"""
tests/test_websocket.py — Phase 6 Tests

Tests:
  - WebSocket connection accepted and phase 1 question received
  - Submitting an answer advances phase and streams next question tokens
  - Submitting skipped=true auto-fills phase data from RAG
  - After 6 phase submissions, server sends phases_complete status
  - Session persists across disconnect/reconnect
"""
import pytest


@pytest.mark.asyncio
async def test_websocket_connects_and_sends_question():
    """WebSocket /ws/session/{id} connects and immediately sends phase 1 question."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_websocket_answer_advances_phase():
    """Submitting an answer advances current_phase and streams next question."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_websocket_skip_autofills_from_rag():
    """Submitting skipped=true fills phase data from RAG (non-null)."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_websocket_all_phases_complete():
    """After 6 phase submissions, server sends {status: phases_complete}."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_websocket_session_persists_on_disconnect():
    """Session current_phase is preserved after disconnect and reconnect."""
    # TODO: Implement — Phase 6
    pass
