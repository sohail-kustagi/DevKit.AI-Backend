"""
api/routes.py
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from core.session_manager import create_session, get_session, update_session_phase, save_final_outputs
from core.grpc_clients import (
    triage_classify, 
    triage_generate_question, 
    orchestrator_decide, 
    orchestrator_compile_brief, 
    specialist_run_swarm
)

router = APIRouter()

class StartSessionRequest(BaseModel):
    initial_input: str

@router.post("/session/start")
async def start_session(req: StartSessionRequest):
    fluency, confidence = await triage_classify(req.initial_input)
    session_id = await create_session(fluency, confidence)
    return {"session_id": session_id}

@router.get("/session/{session_id}")
async def fetch_session(session_id: str):
    session = await get_session(session_id)
    if not session:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return session

@router.websocket("/ws/session/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            session = await get_session(session_id)
            if not session:
                await websocket.send_json({"error": "Invalid session"})
                await websocket.close()
                return

            action, payload = await orchestrator_decide(json.dumps(session, default=str))

            if action == "generate_final" or session["current_phase"] > 6:
                await websocket.send_json({"status": "phases_complete"})
                break
                
            phase = session["current_phase"]
            fluency = session["fluency"]
            context_json = json.dumps({"previous_answers": "..."})
            
            # Send question token-by-token
            async for token in triage_generate_question(phase, fluency, context_json):
                await websocket.send_json({"token": token})
                
            # Wait for user answer
            data = await websocket.receive_json()
            skipped = data.get("skipped", False)
            answer = data.get("answer", "")
            
            await update_session_phase(session_id, phase, "complete", {"answer": answer}, skipped)
            
    except WebSocketDisconnect:
        pass

@router.get("/stream/generate/{session_id}")
async def stream_generation(session_id: str):
    async def event_generator():
        yield 'data: {"type": "brief_ready"}\n\n'
        
        session = await get_session(session_id)
        brief = await orchestrator_compile_brief(json.dumps(session, default=str))
        
        final_outputs = {}
        async for event_type, payload_json in specialist_run_swarm(brief):
            yield f'data: {{"type": "{event_type}", "payload_json": {payload_json}}}\n\n'
            if event_type == "done":
                data = json.loads(payload_json)
                final_outputs = data
                
        if final_outputs:
            await save_final_outputs(
                session_id, 
                final_outputs.get("architecture"), 
                final_outputs.get("milestones"), 
                final_outputs.get("instruction_md"),
                "# Full Report\nGenerated successfully."
            )
            yield 'data: {"type": "saved"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/export/instruction-md/{session_id}")
async def download_instruction(session_id: str):
    session = await get_session(session_id)
    if not session or not session.get("final_outputs"):
        return JSONResponse({"error": "Not ready"}, status_code=400)
        
    content = session["final_outputs"]["instruction_md"]
    return PlainTextResponse(content, headers={"Content-Disposition": 'attachment; filename="instruction.md"'})

@router.get("/export/report/{session_id}")
async def download_report(session_id: str):
    session = await get_session(session_id)
    if not session or not session.get("final_outputs"):
        return JSONResponse({"error": "Not ready"}, status_code=400)
        
    content = session["final_outputs"].get("report_md", "Detailed report here.")
    return PlainTextResponse(content, headers={"Content-Disposition": 'attachment; filename="report.md"'})
