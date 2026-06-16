"""
routes/export.py

REST endpoints for downloading the two final output files.

  GET /export/instruction-md/{session_id}
      Downloads instruction.md — the AI coding assistant prompt file.

  GET /export/report/{session_id}
      Downloads devkit-report.md — the full 7-section project report.

Both endpoints return file downloads with:
  Content-Type:        text/markdown
  Content-Disposition: attachment; filename="..."
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/instruction-md/{session_id}")
async def download_instruction_md(session_id: str):
    """
    Download the instruction.md payload for the given session.
    This file is designed to be dragged directly into Cursor, Copilot, or Devin.
    """
    # TODO: Implement in Phase 6
    raise NotImplementedError("download_instruction_md not yet implemented — Phase 6")


@router.get("/report/{session_id}")
async def download_report(session_id: str):
    """
    Download the comprehensive 7-section project report for the given session.
    """
    # TODO: Implement in Phase 6
    raise NotImplementedError("download_report not yet implemented — Phase 6")
