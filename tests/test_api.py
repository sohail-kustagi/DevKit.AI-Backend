"""
tests/test_api.py — Phase 6 Tests

Tests the FastAPI REST, WebSocket, and SSE routes.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app
from core.session_manager import get_session

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch("api.routes.triage_classify", new_callable=AsyncMock)
@patch("api.routes.create_session", new_callable=AsyncMock)
def test_start_session(mock_create_session, mock_triage_classify):
    mock_triage_classify.return_value = ("developer", 0.95)
    mock_create_session.return_value = "mock_session_123"
    
    response = client.post("/session/start", json={"initial_input": "I want an app"})
    assert response.status_code == 200
    assert response.json()["session_id"] == "mock_session_123"

@patch("api.routes.get_session", new_callable=AsyncMock)
def test_fetch_session(mock_get_session):
    mock_get_session.return_value = {"_id": "mock_session_123", "fluency": "developer"}
    
    response = client.get("/session/mock_session_123")
    assert response.status_code == 200
    assert response.json()["fluency"] == "developer"
