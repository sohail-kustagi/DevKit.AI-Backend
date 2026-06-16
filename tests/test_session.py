"""
tests/test_session.py — Phase 1 & 6 Tests

Tests:
  - Phase 1: MongoDB connection is live
  - Phase 6: create_session returns a valid UUID session document
  - Phase 6: get_session returns the session document
  - Phase 6: SessionNotFoundError raised for unknown session_id
  - Phase 6: update_phase correctly updates a phase's data and status
  - Phase 6: advance_phase increments current_phase
"""
import pytest


@pytest.mark.asyncio
async def test_mongodb_connection():
    """Phase 1: MongoDB connection is live and returns server info."""
    # TODO: Implement — Phase 1
    pass


@pytest.mark.asyncio
async def test_create_session_returns_uuid():
    """create_session() returns a document with a valid UUID _id."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_get_session_returns_document():
    """get_session(valid_id) returns the matching session document."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_session_not_found_error():
    """get_session(unknown_id) raises SessionNotFoundError."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_update_phase_sets_complete():
    """update_phase() sets the phase status to 'complete' with data."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_advance_phase_increments():
    """advance_phase() increments current_phase by 1."""
    # TODO: Implement — Phase 6
    pass
