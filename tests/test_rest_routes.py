"""
tests/test_rest_routes.py — Phase 6 Tests

Tests:
  - POST /session/start returns a valid session_id
  - GET /session/{id} returns 200 with session document
  - GET /session/{unknown_id} returns 404
  - GET /export/instruction-md/{id} returns file with correct headers
  - GET /export/report/{id} returns file with Content-Disposition attachment
  - GET /stream/generate/{id} with incomplete session returns 400
"""
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_start_session_returns_id():
    """POST /session/start returns a JSON body with a session_id."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # TODO: Implement — Phase 6
        pass


@pytest.mark.asyncio
async def test_get_session_200():
    """GET /session/{id} returns 200 and session document."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_get_session_404_unknown():
    """GET /session/{unknown_id} returns 404."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_export_instruction_md_headers():
    """GET /export/instruction-md/{id} returns Content-Disposition: attachment."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_export_report_headers():
    """GET /export/report/{id} returns Content-Disposition: attachment."""
    # TODO: Implement — Phase 6
    pass


@pytest.mark.asyncio
async def test_generate_incomplete_session_400():
    """GET /stream/generate/{id} with pending phases returns 400."""
    # TODO: Implement — Phase 6
    pass
