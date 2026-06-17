"""
api/routes.py
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from core.session_manager import create_session, get_session, add_qna_to_phase, complete_session_phase, save_final_outputs
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

PHASE_KEY_MAP = {
    1: "ui_ux",
    2: "core_logic",
    3: "architecture",
    4: "security",
    5: "testing",
    6: "deployment",
}

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

            phase_num = session["current_phase"]
            phase_key = PHASE_KEY_MAP.get(phase_num, "ui_ux")
            
            if action == "next_phase":
                await complete_session_phase(session_id, phase_num)
                await websocket.send_json({"type": "phase_complete", "phase": phase_key})
                continue
                
            fluency = session["fluency"]

            # Build real context from previous answers
            previous_answers = {}
            for k, v in session.get("phases", {}).items():
                if v.get("status") in ["complete", "active"] or int(k) == phase_num:
                    qna_list = v.get("qna", [])
                    if qna_list:
                        previous_answers[PHASE_KEY_MAP.get(int(k), k)] = "\n".join(
                            [f"Q: {item['question']}\nA: {item['answer']}" for item in qna_list]
                        )
            
            context_json = json.dumps({"previous_answers": previous_answers})

            # Assemble all tokens into one question string, then send it as a question event
            question_text = ""
            async for token in triage_generate_question(phase_num, fluency, context_json):
                question_text += token

            await websocket.send_json({
                "type": "question",
                "phase": phase_key,
                "question": question_text,
            })

            # Wait for user answer
            data = await websocket.receive_json()
            skipped = data.get("skipped", False)
            answer = data.get("answer", "")

            if skipped:
                await complete_session_phase(session_id, phase_num, skipped=True)
                await websocket.send_json({"type": "phase_complete", "phase": phase_key})
            else:
                await add_qna_to_phase(session_id, phase_num, question_text, answer)

    except WebSocketDisconnect:
        pass

@router.get("/stream/generate/{session_id}")
async def stream_generation(session_id: str):
    async def event_generator():
        yield 'data: {"event": "brief_ready"}\n\n'
        
        session = await get_session(session_id)
        brief = await orchestrator_compile_brief(json.dumps(session, default=str))
        
        final_outputs = {}
        async for event_type, payload_json in specialist_run_swarm(brief):
            yield f'data: {{"event": "{event_type}", "payload_json": {payload_json}}}\n\n'
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
            yield 'data: {"event": "saved"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/session/{session_id}/results")
async def fetch_results(session_id: str):
    session = await get_session(session_id)
    if not session or not session.get("final_outputs"):
        return JSONResponse({"error": "Not found or not generated"}, status_code=404)
        
    outputs = session["final_outputs"]
    
    # Build phase summaries from the user's answers
    phase_summaries = {}
    PHASE_KEY_MAP = {1: "ui_ux", 2: "core_logic", 3: "architecture", 4: "security", 5: "testing", 6: "deployment"}
    for k, v in session.get("phases", {}).items():
        key_str = PHASE_KEY_MAP.get(int(k), k)
        qna_list = v.get("qna", [])
        if qna_list:
            phase_summaries[key_str] = " ".join([item["answer"] for item in qna_list])

    arch = outputs.get("architecture", {})
    cost = arch.get("cost", {"launch": "$20-50 / mo", "scale": "$200+ / mo"})
    
    # Map the backend final_outputs to the frontend Results interface
    return {
        "project_name": "DevKit.AI Generated Blueprint",
        "architecture": arch,
        "phase_summaries": phase_summaries,
        "milestones": outputs.get("milestones", {}).get("milestones", []),
        "cost": cost,
        "instruction_md": outputs.get("instruction_md", ""),
        "saved": True
    }

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
