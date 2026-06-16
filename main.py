"""
DevKit.AI — FastAPI Gateway Entrypoint

This is the single public-facing API layer. It handles:
  - REST routes:    /session/*, /export/*
  - WebSocket:      /ws/session/{session_id}
  - SSE stream:     /stream/generate/{session_id}
  - Health check:   /healthz

All AI work is delegated internally to gRPC agent services.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as main_router

app = FastAPI(
    title="DevKit.AI Backend",
    description="Multi-agent Second Brain for software creation.",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(main_router)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["Health"])
async def health_check():
    """Baseline connectivity check. Returns ok if the server is running."""
    return {"status": "ok", "service": "DevKit.AI Backend"}
