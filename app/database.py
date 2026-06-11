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


def _backfill_user_numbers():
    """Uzupełnia brakujące numery dla starych kont."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT id FROM users WHERE user_number IS NULL ORDER BY created_at")
            ).fetchall()
            for i, (uid,) in enumerate(rows, start=1):
                # Sprawdź max istniejący numer
                max_n = conn.execute(
                    _text("SELECT MAX(user_number) FROM users WHERE user_number IS NOT NULL")
                ).scalar() or 0
                conn.execute(
                    _text("UPDATE users SET user_number = :n WHERE id = :id"),
                    {"n": max_n + 1, "id": uid}
                )
            conn.commit()
            if rows:
                print(f"[FitAI] Uzupełniono user_number dla {len(rows)} kont")
    except Exception as exc:
        print(f"[FitAI] Nie udało się uzupełnić user_number: {exc}")


def create_db_and_tables():
    """Create all tables in database (run once at startup)."""
    SQLModel.metadata.create_all(engine)
    _ensure_legacy_sqlite_columns()
    _backfill_user_numbers()    # ← uzupełnia user_number dla istniejących kont


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
            "user_number": "INTEGER",       # ← DODAJ
        },
        "daily_logs": {
            "meals_json": "TEXT DEFAULT '[]'",
            "workouts_json": "TEXT DEFAULT '[]'",
            "custom_meals_json": "TEXT DEFAULT '[]'",
            "energy_level": "INTEGER",      # ← DODAJ
            "stress_level": "INTEGER",      # ← DODAJ
            "fatigue_score": "INTEGER",     # ← DODAJ
            "mood_score": "INTEGER",        # ← DODAJ
            "sleep_hours": "REAL",          # ← DODAJ
            "sleep_quality": "INTEGER",     # ← DODAJ
            "sleep_start": "TEXT",          # ← DODAJ
            "sleep_end": "TEXT",            # ← DODAJ
            "rpe": "INTEGER",               # ← DODAJ
            "meals_eaten": "INTEGER",       # ← DODAJ
            "workouts_done": "INTEGER",     # ← DODAJ
            "notes": "TEXT",                # ← DODAJ
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