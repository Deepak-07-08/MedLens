"""MedLens API entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.routers import auth

settings = get_settings()

app = FastAPI(
    title="MedLens API",
    description="Clinical information organisation. Not a diagnostic tool.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/api/health")
def health() -> dict:
    """Liveness plus a real database round-trip. Open to everyone."""
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok",
        "environment": settings.environment,
        "database": "connected" if db_ok else "unreachable",
        "phase": "2",
    }
