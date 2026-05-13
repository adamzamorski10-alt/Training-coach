"""
FitAI Database — SQLModel engine, session management, migrations
"""

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine
from app.config import DATABASE_URL

# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)


def create_db_and_tables():
    """Create all tables in database (run once at startup)."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI Dependency — yields database session for each request."""
    with Session(engine) as session:
        yield session
