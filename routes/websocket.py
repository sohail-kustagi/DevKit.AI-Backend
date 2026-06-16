"""
routes/websocket.py

WebSocket handler for the real-time 6-phase Q&A conversation loop.

  WS /ws/session/{session_id}

Protocol:
  - On connection: server immediately sends the current phase number + question.
  - Client sends:  { "answer": "...", "skipped": false }
  - Server:
      1. Calls OrchestratorService.DecideNextAction via gRPC
      2. If skipped=true, auto-fills phase data from RAG retriever
      3. Persists phase data to MongoDB
      4. Streams next question tokens back to client as they arrive
      5. On all 6 phases complete, sends { "status": "phases_complete" }
  - On disconnect: session state is already persisted — client can reconnect.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def websocket_phase_loop(websocket: WebSocket, session_id: str):
    """
    Real-time WebSocket loop for the 6-phase discovery engine.
    Streams next-question tokens directly to the client as they arrive from NIM.
    """
    await websocket.accept()
    try:
        # TODO: Implement in Phase 6
        await websocket.send_json({"error": "WebSocket handler not yet implemented — Phase 6"})
    except WebSocketDisconnect:
        pass
