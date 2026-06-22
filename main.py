"""
FitAI Backend — Main Entry Point

Uruchomienie:
  uvicorn main:app --reload --port 8000
"""

from app import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
