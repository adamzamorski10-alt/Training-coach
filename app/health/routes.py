"""
Health Routes — Status checks, diagnostics
"""

import os

from fastapi import APIRouter

from app.config import APP_NAME, APP_VERSION
from app.database import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", name="Health Check")
def health_check():
    """
    ✅ Health endpoint — checks API status and database connectivity.
    
    Returns:
    - status: "ok" | "unhealthy"
    - timestamp: ISO timestamp
    - database: "connected" | "error"
    - app_version: version string
    - ai_modes: list of available AI providers
    """
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    # Available AI providers
    ai_modes = []
    if os.getenv("GROQ_API_KEY"):
        ai_modes.append("groq")
    if os.getenv("GEMINI_API_KEY"):
        ai_modes.append("gemini")
    if not ai_modes:
        ai_modes.append("fallback")

    return {
        "status": "ok" if db_status == "connected" else "unhealthy",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "database": db_status,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "ai_modes": ai_modes,
    }


@router.get("", include_in_schema=False)
def health_check_no_slash():
    """Backward-compatible /health endpoint from fitai_api.py."""
    return health_check()
