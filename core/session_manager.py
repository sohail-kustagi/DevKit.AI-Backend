"""
core/session_manager.py
"""
import uuid
import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from constants.defs import MONGODB_URI

_client = None

def get_db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client.devkit

async def create_session(fluency: str, confidence: float) -> str:
    db = get_db()
    session_id = str(uuid.uuid4())
    doc = {
        "_id": session_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "fluency": fluency,
        "fluency_confidence": confidence,
        "current_phase": 1,
        "phases": {str(i): {"status": "pending", "qna": [], "skipped": False} for i in range(1, 7)},
        "final_outputs": {
            "architecture": None,
            "milestones": None,
            "instruction_md": None,
            "report_md": None
        }
    }
    await db.sessions.insert_one(doc)
    return session_id

async def get_session(session_id: str) -> dict:
    db = get_db()
    return await db.sessions.find_one({"_id": session_id})

async def add_qna_to_phase(session_id: str, phase: int, question: str, answer: str):
    db = get_db()
    await db.sessions.update_one(
        {"_id": session_id},
        {"$push": {f"phases.{phase}.qna": {"question": question, "answer": answer}},
         "$set": {f"phases.{phase}.status": "active"}}
    )

async def complete_session_phase(session_id: str, phase: int, skipped: bool = False):
    db = get_db()
    await db.sessions.update_one(
        {"_id": session_id},
        {"$set": {
            f"phases.{phase}.status": "complete",
            f"phases.{phase}.skipped": skipped,
            "current_phase": phase + 1
        }}
    )

async def save_final_outputs(session_id: str, architecture: dict, milestones: dict, instruction_md: str, report_md: str):
    db = get_db()
    await db.sessions.update_one(
        {"_id": session_id},
        {"$set": {
            "final_outputs.architecture": architecture,
            "final_outputs.milestones": milestones,
            "final_outputs.instruction_md": instruction_md,
            "final_outputs.report_md": report_md
        }}
    )
