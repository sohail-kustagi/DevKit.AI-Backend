"""
routes/stream.py

Server-Sent Events (SSE) handler for Phase 6 architecture generation.

  GET /stream/generate/{session_id}

Protocol:
  - Validates all 6 phases are complete or skipped (returns 400 if not).
  - Calls OrchestratorService.CompileFinalBrief via gRPC.
  - Calls SpecialistService.RunSwarm via gRPC (streaming).
  - Proxies each SwarmProgressEvent as an SSE event to the frontend:
      data: {"type": "architect_complete", "payload": {...}}
      data: {"type": "pm_complete",        "payload": {...}}
      data: {"type": "prompt_complete",    "payload": {...}}
      data: {"type": "done"}
  - On "done": builds the full report, saves to MongoDB, emits final SSE event.
"""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/generate/{session_id}")
async def stream_generate(session_id: str):
    """
    SSE stream for Phase 6 architecture generation.
    Clients connect here to receive real-time progress updates as each
    specialist (Architect → PM → Prompt Engineer) completes their output.
    """
    async def event_generator():
        # TODO: Implement in Phase 6
        yield {"data": '{"type": "error", "message": "SSE handler not yet implemented — Phase 6"}'}

    return EventSourceResponse(event_generator())
