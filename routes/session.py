"""
routes/session.py

REST endpoints for session lifecycle management.
  POST /session/start  — Create a new session and classify initial fluency
  GET  /session/{id}   — Fetch the full session document
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class StartSessionRequest(BaseModel):
    initial_input: str  # The user's first natural-language prompt


@router.post("/start")
async def start_session(body: StartSessionRequest):
    """
    Create a new DevKit.AI session.
    Runs the Triage Agent to classify fluency from the initial input.
    Returns the session_id for all subsequent calls.
    """
    # TODO: Implement in Phase 6
    raise NotImplementedError("start_session not yet implemented — Phase 6")


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Return the full session document for a given session_id."""
    # TODO: Implement in Phase 6
    raise NotImplementedError("get_session not yet implemented — Phase 6")
