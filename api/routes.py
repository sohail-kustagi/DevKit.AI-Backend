"""
api/routes.py
"""
import json
import uuid
import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from core.session_manager import create_session, get_session, add_qna_to_phase, complete_session_phase, save_final_outputs, get_db
from core.grpc_clients import (
    triage_classify,
    triage_generate_question,
    orchestrator_decide,
    orchestrator_compile_brief,
    specialist_run_swarm,
    vision_analyze_image,
    orchestrator_predict_blueprint,
    orchestrator_refine_blueprint
)
from core.boilerplate_generator import generate_boilerplate_zip

router = APIRouter()

class StartSessionRequest(BaseModel):
    initial_input: str

@router.post("/session/start")
async def start_session(req: StartSessionRequest):
    fluency, confidence = await triage_classify(req.initial_input)
    session_id = await create_session(fluency, confidence)
    return {"session_id": session_id}


# ── Quick-Mode: single-shot full blueprint prediction ─────────────────────────
class PredictRequest(BaseModel):
    initial_input: str

@router.post("/session/predict")
async def predict_session(req: PredictRequest):
    """
    Quick Mode: infer a complete blueprint from one prompt.
    Creates session, kicks off the async prediction, returns session_id immediately.
    The client connects to /stream/generate/{session_id} for live SSE results.
    """
    session_id = await create_session("quick_predict", 1.0)
    # Store the initial idea so the stream endpoint can use it

    await get_db().sessions.update_one(
        {"_id": session_id},
        {"$set": {"initial_input": req.initial_input, "mode": "quick"}}
    )
    return {"session_id": session_id}


# ── Refinement: patch blueprint with natural language ─────────────────────────
class RefineRequest(BaseModel):
    message: str

@router.post("/session/{session_id}/refine")
async def refine_session(session_id: str, req: RefineRequest):
    """
    Takes a natural-language refinement message and patches the stored blueprint.
    Returns updated architecture fields.
    """
    session = await get_session(session_id)
    if not session:
        return JSONResponse({"error": "Not found"}, status_code=404)
    outputs = session.get("final_outputs") or {}
    patch_str = await orchestrator_refine_blueprint(json.dumps(outputs), req.message)
    try:
        patch = json.loads(patch_str)
    except:
        patch = {}
    # Merge patch into final_outputs
    if patch.get("architecture"):
        merged_arch = {**(outputs.get("architecture") or {}), **patch["architecture"]}
        await get_db().sessions.update_one(
            {"_id": session_id},
            {"$set": {"final_outputs.architecture": merged_arch}}
        )
        return {"patch": patch, "architecture": merged_arch}
    return {"patch": patch}


# ── Boilerplate ZIP export ────────────────────────────────────────────────────
@router.post("/export/boilerplate/{session_id}")
async def export_boilerplate(session_id: str):
    """Generate and stream a project zip from the session's architecture data."""
    session = await get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    if not (session.get("final_outputs") or {}).get("architecture"):
        return JSONResponse({"error": "Blueprint not ready yet"}, status_code=400)

    buf = generate_boilerplate_zip(session)
    project_name = (session.get("project_name") or "devkit-project").lower().replace(" ", "-")

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_name}-boilerplate.zip"'}
    )

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

            data = await websocket.receive_json()
            skipped = data.get("skipped", False)
            answer = data.get("answer", "")
            image_base64 = data.get("image_base64", "")

            if image_base64:
                vision_resp = await vision_analyze_image(image_base64)
                if not vision_resp.degraded:
                    vision_text = (
                        f"[Vision Agent Analysis of User Uploaded Image]\n"
                        f"- Layout: {vision_resp.layout_json}\n"
                        f"- Components: {vision_resp.components_json}\n"
                        f"- Color Palette: {vision_resp.color_palette_json}\n"
                        f"- Style/Vibe: {vision_resp.style_vibe}"
                    )
                    answer += f"\n\n{vision_text}"
                else:
                    answer += f"\n\n[Vision Agent Error: {vision_resp.degradation_message}]"

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
        session = await get_session(session_id)
        if not session:
            yield 'data: {"event": "error", "message": "Session not found"}\n\n'
            return

        # ── Quick Mode: single-shot LLM predict path ──────────────────────────
        if session.get("mode") == "quick":
            initial_input = session.get("initial_input", "")
            yield 'data: {"event": "brief_ready"}\n\n'

            blueprint_str = await orchestrator_predict_blueprint(initial_input)
            try:
                blueprint = json.loads(blueprint_str, strict=False)
            except:
                blueprint = {}

            arch = blueprint.get("architecture", {})
            arch_payload = json.dumps(arch)
            yield f'data: {{"event": "architect_complete", "payload_json": {arch_payload}}}\n\n'

            milestones = {"milestones": blueprint.get("milestones", [])}
            pm_payload = json.dumps(milestones)
            yield f'data: {{"event": "pm_complete", "payload_json": {pm_payload}}}\n\n'

            instruction_md = blueprint.get("instruction_md", "")
            prompt_payload = json.dumps({"instruction_md": instruction_md})
            yield f'data: {{"event": "prompt_complete", "payload_json": {prompt_payload}}}\n\n'

            combined = {
                "architecture": arch,
                "milestones": milestones,
                "instruction_md": instruction_md,
                "project_name": blueprint.get("project_name", "Generated Project"),
                "phase_summaries": blueprint.get("phase_summaries", {}),
                "cost": arch.get("cost") or blueprint.get("cost", {}),
                "warnings": blueprint.get("warnings", []),
                "clarifying_questions": blueprint.get("clarifying_questions", []),
            }
            await save_final_outputs(
                session_id,
                arch,
                milestones,
                instruction_md,
                f"# {blueprint.get('project_name', 'Project')} Blueprint\n\n{instruction_md}"
            )
            # Also save project_name and phase_summaries
            await get_db().sessions.update_one(
                {"_id": session_id},
                {"$set": {
                    "project_name": blueprint.get("project_name", "Generated Project"),
                    "final_outputs.phase_summaries": blueprint.get("phase_summaries", {}),
                    "final_outputs.cost": combined["cost"],
                    "final_outputs.warnings": combined["warnings"],
                }}
            )
            done_payload = json.dumps(combined)
            yield f'data: {{"event": "done", "payload_json": {done_payload}}}\n\n'
            yield 'data: {"event": "saved"}\n\n'
            return

        # ── Advanced Mode: swarm pipeline path ───────────────────────────────
        yield 'data: {"event": "brief_ready"}\n\n'

        outputs = session.get("final_outputs") if session else None
        if outputs and outputs.get("architecture") is not None:
            yield 'data: {"event": "done"}\n\n'
            return

        brief = await orchestrator_compile_brief(json.dumps(session, default=str))

        final_outputs = {}
        async for event_type, payload_json in specialist_run_swarm(brief):
            yield f'data: {{"event": "{event_type}", "payload_json": {payload_json}}}\n\n'
            if event_type == "done":
                final_outputs = json.loads(payload_json)

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

    arch = outputs.get("architecture") or {}
    cost = arch.get("cost", {"launch": "$20-50 / mo", "scale": "$200+ / mo"})
    
    milestones_data = outputs.get("milestones") or {}
    
    # Prefer stored phase_summaries (Quick Mode) over reconstructed ones
    stored_summaries = outputs.get("phase_summaries")
    if stored_summaries:
        phase_summaries = stored_summaries

    stored_cost = outputs.get("cost")
    if stored_cost:
        cost = stored_cost

    return {
        "project_name": session.get("project_name") or "DevKit.AI Generated Blueprint",
        "architecture": arch,
        "phase_summaries": phase_summaries,
        "milestones": milestones_data.get("milestones", []) if isinstance(milestones_data, dict) else (milestones_data if isinstance(milestones_data, list) else []),
        "cost": cost,
        "warnings": outputs.get("warnings") or [],
        "instruction_md": outputs.get("instruction_md") or "",
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
