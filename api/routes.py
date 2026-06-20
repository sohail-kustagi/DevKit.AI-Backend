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
    session_id = await create_session(fluency, confidence, req.initial_input)
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
    session_id = await create_session("quick_predict", 1.0, req.initial_input)
    # Store the initial idea so the stream endpoint can use it

    await get_db().sessions.update_one(
        {"_id": session_id},
        {"$set": {"mode": "quick"}}
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
    
    history = session.get("refinement_history") or []
    history.append({"role": "user", "text": req.message})

    patch_str = await orchestrator_refine_blueprint(json.dumps(outputs), json.dumps(history))
    try:
        patch = json.loads(patch_str)
    except:
        patch = {}
        
    history.append({
        "role": "ai", 
        "text": f"✅ Processed request.", 
        "patch": patch
    })

    # Merge patch into final_outputs
    updated_fields = {"refinement_history": history}
    response_data = {"patch": patch, "refinement_history": history}
    
    merged_arch = outputs.get("architecture") or {}
    if patch.get("architecture"):
        merged_arch = {**merged_arch, **patch["architecture"]}
        updated_fields["final_outputs.architecture"] = merged_arch
        response_data["architecture"] = merged_arch
    
    # Merge other top-level fields
    for field in ["instruction_md", "milestones", "cost", "warnings", "project_name"]:
        if field in patch:
            updated_fields[f"final_outputs.{field}"] = patch[field]
            response_data[field] = patch[field]
            
    await get_db().sessions.update_one(
        {"_id": session_id},
        {"$set": updated_fields}
    )
    
    return response_data


# ── VC Pitch Deck Export ──────────────────────────────────────────────────────
@router.get("/export/pitch-deck/{session_id}")
async def export_pitch_deck(session_id: str):
    """Generates a Markdown VC Pitch Deck based on the session's architecture and summaries."""
    session = await get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
        
    outputs = session.get("final_outputs") or {}
    project_name = session.get("project_name") or "DevKit.AI Generated Project"
    
    stored_summaries = outputs.get("phase_summaries")
    if stored_summaries:
        phase_summaries = stored_summaries
    else:
        phase_summaries = {}
        PHASE_KEY_MAP = {1: "ui_ux", 2: "core_logic", 3: "architecture", 4: "security", 5: "testing", 6: "deployment"}
        for k, v in session.get("phases", {}).items():
            key_str = PHASE_KEY_MAP.get(int(k), k)
            if v.get("summary"):
                phase_summaries[key_str] = v.get("summary")
            else:
                qna_list = v.get("qna", [])
                if qna_list:
                    phase_summaries[key_str] = " ".join([item["answer"] for item in qna_list])

    ui_ux = phase_summaries.get("ui_ux") or "To be determined."
    core_logic = phase_summaries.get("core_logic") or "To be determined."
    arch_summary = phase_summaries.get("architecture") or "To be determined."
    security = phase_summaries.get("security") or "To be determined."
    
    arch = outputs.get("architecture") or {}
    cost = outputs.get("cost") or arch.get("cost") or {}
    milestones_data = outputs.get("milestones") or []
    if isinstance(milestones_data, dict):
        milestones = milestones_data.get("milestones", [])
    else:
        milestones = milestones_data if isinstance(milestones_data, list) else []
    
    warnings = outputs.get("warnings") or []

    # Format Architecture bullets
    arch_bullets_list = []
    if arch:
        for k, v in arch.items():
            if k == "cost":
                continue
            if isinstance(v, list):
                val_str = ", ".join(str(item) for item in v)
            elif isinstance(v, dict):
                val_str = ", ".join(f"{sub_k}: {sub_v}" for sub_k, sub_v in v.items())
            else:
                val_str = str(v).replace('\n', ' ')
            arch_bullets_list.append(f"- **{k.capitalize()}**: {val_str}")
        arch_bullets = "\n".join(arch_bullets_list)
    else:
        arch_bullets = "- To be determined."
    
    # Format Milestones
    ms_bullets = "\n".join([f"- **{m.get('name', 'Phase')}** ({m.get('duration', '')})" for m in milestones]) if milestones else "- To be determined."
    
    # Format Warnings
    warn_bullets = "\n".join([f"- ⚠️ {w.get('title', 'Warning')}: {w.get('description', '')}" for w in warnings]) if warnings else "- Minimal foreseeable risks."

    md_content = f"""# {project_name} - Pitch Deck

## Slide 1: Vision & Overview
{ui_ux}

---

## Slide 2: The Solution & Core Logic
{core_logic}

---

## Slide 3: Our Technical Moat
{arch_summary}

**Tech Stack:**
{arch_bullets}

---

## Slide 4: Execution Timeline
{ms_bullets}

---

## Slide 5: Business Scaling & Security
**Cost Analysis:**
- **Launch Phase:** {cost.get("launch", "TBD")}
- **Scale Phase:** {cost.get("scale", "TBD")}

**Security & Compliance:**
{security}

**Key Operational Risks:**
{warn_bullets}
"""

    return PlainTextResponse(
        content=md_content,
        headers={"Content-Disposition": f'attachment; filename="{project_name.replace(" ", "_")}_PitchDeck.md"'}
    )


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
            
            phase_data = session.get("phases", {}).get(str(phase_num), {})
            if len(phase_data.get("qna", [])) >= 2:
                action = "next_phase"
            
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
            
            context_dict = {"previous_answers": previous_answers}
            if session.get("initial_input"):
                context_dict["initial_input"] = session["initial_input"]
            context_json = json.dumps(context_dict)

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
        "refinement_history": session.get("refinement_history") or [],
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

@router.get("/export/pitch-deck/{session_id}")
async def export_pitch_deck(session_id: str):
    session = await get_session(session_id)
    if not session or not session.get("final_outputs"):
        return JSONResponse({"error": "Not ready"}, status_code=400)
        
    outputs = session["final_outputs"]
    project_name = session.get("project_name") or "DevKit Project"
    
    arch = outputs.get("architecture") or {}
    cost = outputs.get("cost") or {}
    milestones_data = outputs.get("milestones") or {}
    milestones = milestones_data.get("milestones", []) if isinstance(milestones_data, dict) else (milestones_data if isinstance(milestones_data, list) else [])

    md = f"# {project_name} - Pitch Deck\n\n"
    md += "## Executive Summary\n"
    md += "A high-performance, scalable solution architecture generated by DevKit.AI.\n\n"
    
    md += "## Architecture & Technology Stack\n"
    for comp in arch.get("components", []):
        md += f"- **{comp.get('name')}**: {comp.get('tech')} ({comp.get('purpose')})\n"
    md += "\n"
    
    md += "## Implementation Roadmap\n"
    for m in milestones:
        deps = m.get('dependencies', [])
        deps_str = f" (Depends on: {', '.join(deps)})" if deps else ""
        md += f"- **{m.get('name')}** ({m.get('duration')}){deps_str}\n"
    md += "\n"
    
    md += "## Estimated Infrastructure Cost\n"
    md += f"- **Launch Phase:** {cost.get('launch', 'N/A')}\n"
    md += f"- **Scale Phase:** {cost.get('scale', 'N/A')}\n"
    md += "\n"
    
    return PlainTextResponse(md, headers={"Content-Disposition": f'attachment; filename="{project_name.replace(" ", "_")}_PitchDeck.md"'})
