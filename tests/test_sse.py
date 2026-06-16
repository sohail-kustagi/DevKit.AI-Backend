"""
tests/test_sse.py — Phase 6 Tests

Tests:
  - SSE /stream/generate/{id} emits events in correct order
  - Final 'saved' event is emitted after all specialists complete
  - SSE stream returns 400 for incomplete session
"""
import pytest


@pytest.mark.asyncio
async def test_sse_events_in_correct_order():
    """
    SSE /stream/generate/{id} emits events in order:
    brief_ready → architect_complete → pm_complete → prompt_complete → done → saved
    """
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_sse_saved_event_populates_session():
    """After 'saved' SSE event, session final_outputs are all non-null."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_sse_incomplete_session_returns_400():
    """SSE stream returns 400 if any phase is still pending."""
    # TODO: Implement — Phase 6
    pass
