"""
FitAI Backend API v2.0 — Modularized FastAPI Application

Struktura:
- app/config.py — Settings, constants
- app/database.py — SQLModel engine, session management
- app/models.py — SQLModel definitions
- app/schemas.py — Pydantic request/response models
- app/auth/ — JWT, password, dependencies, auth routes
- app/fitness/ — Macros, progression, XP
- app/ai/ — LLM integration
- app/health/ — Status checks
- app/utils/ — Helpers, exceptions
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import _rate_limit_key
from app.auth.routes import router as auth_router
from app.health.routes import router as health_router
from app.config import CORS_ORIGINS, APP_NAME, APP_VERSION, DEBUG
from app.database import create_db_and_tables
from app.legacy_routes import router as legacy_router

# Initialize FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="FitAI Backend API v2.0 — Fitness, Nutrition, Progressive Overload",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
limiter = Limiter(key_func=_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(health_router)

# Import fitness routes
from app.fitness.routes import router as fitness_router
from app.ai.routes import router as ai_router

app.include_router(fitness_router)
app.include_router(ai_router)
app.include_router(legacy_router)


# Exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    """Handle SQLAlchemy errors with proper logging."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error — please try again later"},
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request, exc):
    """Handle database connection errors."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Database connection error — please try again"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Catch-all for unexpected errors."""
    if DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ════════════════════════════════════════════════════════════════════════════════
# STATIC FILES — Serve HTML, CSS, JS, and SPA fallback
# ════════════════════════════════════════════════════════════════════════════════

# Define static directory (parent of app/ module)
STATIC_DIR = Path(__file__).parent.parent

# Mount public static files (if /public directory exists)
public_dir = STATIC_DIR / "public"
if public_dir.exists():
    app.mount("/public", StaticFiles(directory=str(public_dir), html=True), name="public")


# Root route — serve index.html for SPA
@app.get("/")
async def serve_root():
    """Serve main index.html for single-page app."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return JSONResponse({"error": "Frontend not found"}, status_code=404)


# Catch-all for SPA routing — serve index.html for any unmatched path
@app.get("/{path:path}")
async def serve_spa(path: str):
    """
    Fallback route for SPA routing. Serves index.html for any path
    that isn't matched by API routes or known static files.
    """
    # Skip API routes and known assets
    skip_paths = {".json", ".js", ".css", ".png", ".jpg", ".gif", ".svg", ".ico", ".woff", ".woff2"}
    if any(path.endswith(ext) for ext in skip_paths):
        return JSONResponse({"error": "File not found"}, status_code=404)
    
    # For all other paths, serve index.html (SPA routing)
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    
    return JSONResponse({"error": "Frontend not found"}, status_code=404)


# Startup events
@app.on_event("startup")
async def on_startup():
    """Initialize database and migrations."""
    create_db_and_tables()
    print(f"[{APP_NAME}] Database initialized at startup")
