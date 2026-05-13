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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import _rate_limit_key
from app.auth.routes import router as auth_router
from app.health.routes import router as health_router
from app.config import CORS_ORIGINS, APP_NAME, APP_VERSION, DEBUG
from app.database import create_db_and_tables

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
# TODO: fitness routes, ai routes


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


# Startup events
@app.on_event("startup")
async def on_startup():
    """Initialize database and migrations."""
    create_db_and_tables()
    print(f"[{APP_NAME}] Database initialized at startup")
