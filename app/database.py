"""
FitAI Database — SQLModel engine, session management, migrations
"""

from sqlalchemy import text as _text
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
    _ensure_legacy_sqlite_columns()


def _ensure_legacy_sqlite_columns():
    """Add missing columns to older local SQLite databases.

    SQLModel.metadata.create_all() does not alter existing tables, so older
    workspace databases need a tiny compatibility bootstrap for new columns.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    table_columns = {
        "users": {
            "nickname": "TEXT",
        },
        "daily_logs": {
            "meals_json": "TEXT DEFAULT '[]'",
            "workouts_json": "TEXT DEFAULT '[]'",
            "custom_meals_json": "TEXT DEFAULT '[]'",
        },
        "drill_results": {
            "drill_category": "TEXT",
            "drill_sport": "TEXT",
            "target_pct": "INTEGER",
        },
    }

    try:
        with engine.connect() as conn:
            for table_name, required_columns in table_columns.items():
                existing_columns = {
                    row[1]
                    for row in conn.execute(_text(f"PRAGMA table_info({table_name})")).fetchall()
                }
                for column_name, ddl_type in required_columns.items():
                    if column_name not in existing_columns:
                        conn.execute(_text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"))
            conn.commit()
    except Exception as exc:
        print(f"[FitAI] Ostrzeżenie: nie udało się zaktualizować schematu SQLite: {exc}")


def get_session():
    """FastAPI Dependency — yields database session for each request."""
    with Session(engine) as session:
        yield session
