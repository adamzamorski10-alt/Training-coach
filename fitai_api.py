"""
FitAI Backend API — FastAPI v2.0
=================================
Nowe w v2.0:
  - Migracja na SQLite / SQLModel (zamiast JSON)
  - System progresji RPE + Progressive Overload
  - Dynamiczne makroskładniki (Carb Cycling)

Uruchomienie: uvicorn fitai_api:app --reload --port 8000
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import secrets
import uuid as _uuid_mod
from datetime import date, datetime, timedelta
from typing import Any, Optional

import groq as _groq_module
import google.generativeai as genai
import jwt                          # PyJWT>=2.0
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import relationship
from sqlalchemy import text as _text
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

# ─── External prompt templates ────────────────────────────────────────────────
# Centralised in prompts.py — import here and use via .format() at each call
# site so the API file stays free of long instruction strings.
try:
    from prompts import (
        KITCHEN_PROMPT,
        PROGRESSION_PROMPT,
        WEEKLY_PLAN_PROMPT,
        RECOVERY_PROMPT,
    )
    print("[FitAI] prompts.py imported OK — AI prompt templates active.")
except ImportError:
    # Graceful fallback so the API still starts if prompts.py is absent.
    # All prompt variables are set to None; every call site has an
    # inline fallback string that mirrors the prompts.py content.
    KITCHEN_PROMPT = PROGRESSION_PROMPT = WEEKLY_PLAN_PROMPT = RECOVERY_PROMPT = None
    print("[FitAI] WARN: prompts.py not found — inline fallback prompts will be used.")

# ── Inline fallback definitions (mirror prompts.py, used when import fails) ──
# These are only active when KITCHEN_PROMPT etc. are None after the import.
_KITCHEN_PROMPT_FB = (
    "Jesteś Ekspertem Kulinarnym FitAI.\n"
    "Składniki: {ingredients}\n"
    "Cel: {goal}\n"
    "Limit kcal: {remaining_calories}\n"
    "Wykluczenia/alergie: {exclusions}\n"
    "Stwórz 4 przepisy w podanym formacie. Każdy musi mieścić się w limicie kcal."
)
_PROGRESSION_PROMPT_FB = (
    "Jesteś Trenerem FitAI. Ćwiczenie: {exercise_name}.\n"
    "Wynik: {successes}/{total_attempts}, RPE: {rpe}/10.\n"
    "Notatki: {user_notes}\n"
    "Podaj jedną konkretną radę (max 2 zdania)."
)
_WEEKLY_PLAN_PROMPT_FB = (
    "Jesteś Strategiem FitAI. Profil: wiek {age}, waga {weight}kg, cel: {goal}.\n"
    "Sport: {sport_focus}, poziom: {level}, treningi: {workout_days} dni/tydz.\n"
    "Typ dnia (carb cycling): {day_type}.\n"
    "Podaj główne założenie tygodnia i modyfikację diety."
)
_RECOVERY_PROMPT_FB = (
    "Jesteś Systemem Autoregulacji FitAI.\n"
    "Nastrój: {mood}/10, energia: {energy}/10, ból/zakwasy: {soreness}.\n"
    "Odpowiedź max 2 zdania."
)

def _get_prompt(template, fallback: str, **kwargs) -> str:
    """
    Bezpieczne renderowanie szablonu promptu.
    Jeśli template jest None (brak prompts.py) → użyj fallback.
    Wszystkie None-wartości w kwargs → zastąp pustym stringiem lub 'brak'.
    Zawsze opakowuje wywołanie .format() w try/except KeyError.
    """
    safe_kwargs = {
        k: (str(v) if v is not None else 'brak')
        for k, v in kwargs.items()
    }
    source = template if template is not None else fallback
    try:
        return source.format(**safe_kwargs)
    except KeyError as exc:
        # Brakująca zmienna w szablonie — loguj i zwróć fallback
        print(f"[FitAI] WARN: prompt KeyError {exc} — using raw fallback")
        try:
            return fallback.format(**safe_kwargs)
        except KeyError:
            return fallback  # ostateczny fallback: niesformatowany string


# ─── Rate limiter setup ───────────────────────────────────────────────────────
# Key function: prefer authenticated user ID over raw IP so shared NAT doesn't
# penalise all users behind the same router.

def _rate_limit_key(request: Request) -> str:
    """Use Bearer sub (user UUID) if present, otherwise fall back to client IP."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                os.getenv("JWT_SECRET_KEY", ""),
                algorithms=["HS256"],
                options={"verify_exp": False},   # key only — expiry checked elsewhere
            )
            return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)

# Limits read from env so they can be tuned without a redeploy.
# Defaults: 10 AI calls / minute per user, 50 / hour.
AI_RATE_PER_MINUTE: str = os.getenv("AI_RATE_PER_MINUTE", "10/minute")
AI_RATE_PER_HOUR:   str = os.getenv("AI_RATE_PER_HOUR",   "50/hour")

load_dotenv()

# ─── JWT / Auth configuration ─────────────────────────────────────────────────

# Klucz tajny — w produkcji ustaw w zmiennej środowiskowej JWT_SECRET_KEY
# Generuj: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM  = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "10080"))   # 7 dni domyślnie

_bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password hashing (stdlib — brak zależności zewnętrznych) ─────────────────

def _hash_password(plain: str) -> str:
    """SHA-256 PBKDF2 z losową solą — bezpieczne bez bcrypt."""
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260_000)
    return f"pbkdf2:sha256:260000:{salt}:{key.hex()}"


def _verify_password(plain: str, stored: str) -> bool:
    """Weryfikuje hasło względem przechowywanego hasha."""
    try:
        _, algo, iterations, salt, stored_hex = stored.split(":")
        key = hashlib.pbkdf2_hmac(algo, plain.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(key.hex(), stored_hex)
    except (ValueError, TypeError):
        return False


# ─── JWT helpers ──────────────────────────────────────────────────────────────

def _create_access_token(user_id: str, email: str, role: str) -> str:
    """Tworzy podpisany token JWT z payloadem użytkownika."""
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {
        "sub": str(user_id),      # subject = primary key w DB (UUID)
        "email": email,
        "role": role,
        "exp": exp,
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(8),   # unikalny ID tokena (do blacklistowania)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """Dekoduje i weryfikuje token JWT. Rzuca HTTPException przy błędzie."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token wygasł — zaloguj się ponownie",
                            headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Nieprawidłowy token: {exc}",
                            headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> "UserDB":
    """
    FastAPI Dependency — wyciąga użytkownika z Bearer tokena.

    Użycie w endpointach:
        @app.get("/app/profile")
        def profile(user: UserDB = Depends(get_current_user)):
            return user.to_profile_dict()
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Brak tokena autoryzacji",
                            headers={"WWW-Authenticate": "Bearer"})
    payload = _decode_token(credentials.credentials)
    user_id = payload["sub"]   # UUID string
    with Session(engine) as session:
        user = session.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Użytkownik z tokena nie istnieje")
    return user


def get_current_pro_user(user: "UserDB" = Depends(get_current_user)) -> "UserDB":
    """Dependency — wymaga planu PRO."""
    if user.role not in ("pro_user", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Ta funkcja wymaga planu PRO")
    return user


def get_current_admin(user: "UserDB" = Depends(get_current_user)) -> "UserDB":
    """Dependency — wymaga roli admin."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Brak uprawnień administratora")
    return user


# ─── Database setup ───────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fitai.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def get_session():
    with Session(engine) as session:
        yield session


# ─── SQLModel ORM models ──────────────────────────────────────────────────────

class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[str] = Field(
        default_factory=lambda: str(_uuid_mod.uuid4()),
        primary_key=True,
    )
    user_key: str = Field(unique=True, index=True)          # "web:<identity_id>" lub legacy user_id
    identity_id: Optional[str] = Field(default=None, index=True)
    email: Optional[str] = Field(default=None, index=True)
    name: str
    age: int
    height: float
    weight: float
    start_weight: float
    target_weight: float
    gender: str = "mężczyzna"
    goal: str
    frequency: str
    diet: str
    allergies: str = ""
    meals_per_day: int = 4
    notes: str = ""
    plan: str = "free"          # "free" | "pro"
    role: str = "free_user"
    calories_target: int = 0
    protein_target: int = 0
    streak_days: int = 0
    linked_discord_id: Optional[str] = None
    # JSON-encoded lists/dicts – SQLite nie ma ARRAY
    sports_json: str = "[]"
    training_focus_json: str = "[]"
    improvement_areas_json: str = "[]"
    preferred_foods_json: str = "[]"
    avoid_foods_json: str = "[]"
    available_equipment_json: str = "[]"
    avoid_exercises_json: str = "[]"
    reminders_json: str = '{"email_enabled":true,"discord_enabled":false,"discord_channel_id":null}'
    weekly_plan_json: Optional[str] = None
    substitutes_history_json: str = "{}"
    # ─── Sports module ───────────────────────────────────────────────────────
    sport_focus: Optional[str] = None                  # np. "koszykówka"
    sport_specialization: Optional[str] = None         # np. "rzuty"
    sport_training_days_json: str = "[]"               # np. ["Środa", "Sobota"]
    # ─── Auth (dodane w v2.1) ───────────────────────────────────────────────
    hashed_password: Optional[str] = None             # None = konto Netlify Identity (stare)
    is_active: bool = True                             # możliwość blokowania konta
    # ─── Gamification & safety ───────────────────────────────────────────────
    total_xp: int = 0                                  # łączne punkty XP
    injuries: str = ""                                 # przecinkowy string: "kolano lewe,bark"
    last_weight_change: float = 0.0                    # delta wagi wzgl. poprzedniego wpisu [kg]
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # ── Relacje ──────────────────────────────────────────────────────────────────
    logs: list["DailyLogDB"] = Relationship(
        sa_relationship=relationship(
            "DailyLogDB",
            back_populates="user",
            lazy="select",
        )
    )
    exercise_results: list["ExerciseResultDB"] = Relationship(
        sa_relationship=relationship(
            "ExerciseResultDB",
            back_populates="user",
            lazy="select",
        )
    )

    # Helpers
    def get_list(self, field: str) -> list:
        return json.loads(getattr(self, field, "[]") or "[]")

    def set_list(self, field: str, value: list):
        setattr(self, field, json.dumps(value, ensure_ascii=False))

    def get_dict(self, field: str) -> dict:
        return json.loads(getattr(self, field, "{}") or "{}")

    def set_dict(self, field: str, value: dict):
        setattr(self, field, json.dumps(value, ensure_ascii=False))

    def to_profile_dict(self) -> dict:
        """Serializes user row to the legacy profile dict format for backward compat."""
        return {
            "user_key": self.user_key,
            "identity_id": self.identity_id,
            "email": self.email,
            "name": self.name,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "start_weight": self.start_weight,
            "target_weight": self.target_weight,
            "gender": self.gender,
            "goal": self.goal,
            "frequency": self.frequency,
            "diet": self.diet,
            "allergies": self.allergies,
            "meals_per_day": self.meals_per_day,
            "notes": self.notes,
            "plan": self.plan,
            "role": self.role,
            "calories_target": self.calories_target,
            "protein_target": self.protein_target,
            "streak_days": self.streak_days,
            "linked_discord_id": self.linked_discord_id,
            "sports": self.get_list("sports_json"),
            "training_focus": self.get_list("training_focus_json"),
            "improvement_areas": self.get_list("improvement_areas_json"),
            "preferred_foods": self.get_list("preferred_foods_json"),
            "avoid_foods": self.get_list("avoid_foods_json"),
            "available_equipment": self.get_list("available_equipment_json"),
            "avoid_exercises": self.get_list("avoid_exercises_json"),
            "reminders": self.get_dict("reminders_json"),
            "weekly_plan": self.get_dict("weekly_plan_json") if self.weekly_plan_json else None,
            "substitutes_history": self.get_dict("substitutes_history_json"),
            "sport_focus": self.sport_focus,
            "sport_specialization": self.sport_specialization,
            "sport_training_days": self.get_list("sport_training_days_json"),
            "total_xp": self.total_xp,
            "level": _xp_to_level(self.total_xp),
            "injuries": [i.strip() for i in self.injuries.split(",") if i.strip()],
            "last_weight_change": self.last_weight_change,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DailyLogDB(SQLModel, table=True):
    __tablename__ = "daily_logs"

    id: Optional[str] = Field(
        default_factory=lambda: str(_uuid_mod.uuid4()),
        primary_key=True,
    )
    user_id: str = Field(foreign_key="users.id", index=True)
    log_date: str = Field(index=True)           # ISO date string
    food: str = ""
    workout: str = ""
    mood: str = ""
    weight: Optional[float] = None
    water_liters: Optional[float] = None          # spożycie wody w litrach (inkrementowane)
    logged_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    user: "UserDB" = Relationship(
        sa_relationship=relationship(
            "UserDB",
            back_populates="logs",
            lazy="select",
        )
    )

    def to_dict(self) -> dict:
        return {
            "date": self.log_date,
            "food": self.food,
            "workout": self.workout,
            "mood": self.mood,
            "weight": self.weight,
            "water_liters": self.water_liters,
            "logged_at": self.logged_at,
        }


class ExerciseResultDB(SQLModel, table=True):
    """Historyczne wyniki ćwiczeń – serce systemu progresji."""
    __tablename__ = "exercise_results"

    id: Optional[str] = Field(
        default_factory=lambda: str(_uuid_mod.uuid4()),
        primary_key=True,
    )
    user_id: str = Field(foreign_key="users.id", index=True)
    exercise_name: str = Field(index=True)
    session_date: str = Field(index=True)       # ISO date
    sets: int
    reps: int
    weight_kg: float
    rpe: int = Field(ge=1, le=10)               # 1 = bardzo lekko, 10 = maksymalny wysiłek
    notes: str = ""
    logged_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    user: Optional["UserDB"] = Relationship(
        sa_relationship=relationship(
            "UserDB",
            back_populates="exercise_results",
            lazy="select",
        )
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "exercise_name": self.exercise_name,
            "session_date": self.session_date,
            "sets": self.sets,
            "reps": self.reps,
            "weight_kg": self.weight_kg,
            "rpe": self.rpe,
            "notes": self.notes,
            "logged_at": self.logged_at,
        }


class DrillResultDB(SQLModel, table=True):
    """Wyniki sesji drilli sportowych – serce systemu progresji sportowej."""
    __tablename__ = "drill_results"

    id: Optional[str] = Field(
        default_factory=lambda: str(_uuid_mod.uuid4()),
        primary_key=True,
    )
    user_id: str = Field(foreign_key="users.id", index=True)
    drill_name: str = Field(index=True)
    session_date: str = Field(index=True)       # ISO date
    success_count: int = 0                      # trafienia / powtórzenia (rzuty)
    total_attempts: int = 0                     # łączna liczba prób (rzuty)
    rpe: int = Field(ge=1, le=10)              # 1 = bardzo lekko, 10 = maksymalny wysiłek
    notes: str = ""
    # ─── Pola dla typów drilli bieg/sprint ───────────────────────────────────
    time_seconds: Optional[float] = None        # czas w sekundach (Bieg/Sprint)
    distance_meters: Optional[float] = None     # dystans w metrach (Bieg/Sprint)
    # ─── Pola ogólne (Skill/Drill i Cardio/Sport) ─────────────────────────────
    duration_seconds: Optional[int] = None      # czas trwania ćwiczenia/meczu [s]
    weight_kg: Optional[float] = None           # obciążenie [kg] (np. weighted drill)
    logged_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        base = {
            "id": self.id,
            "drill_name": self.drill_name,
            "session_date": self.session_date,
            "rpe": self.rpe,
            "notes": self.notes,
            "logged_at": self.logged_at,
        }
        # Rzuty: pola success/attempts
        if self.total_attempts:
            base["success_count"]  = self.success_count
            base["total_attempts"] = self.total_attempts
            base["accuracy_pct"]   = round(self.success_count / self.total_attempts * 100)
        # Bieg/Sprint: pola time/distance
        if self.time_seconds is not None:
            base["time_seconds"]   = self.time_seconds
        if self.distance_meters is not None:
            base["distance_meters"] = self.distance_meters
        if self.duration_seconds is not None:
            base["duration_seconds"] = self.duration_seconds
        if self.weight_kg is not None:
            base["weight_kg"] = self.weight_kg
        return base


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _create_composite_indexes()


def _create_composite_indexes():
    """
    Creates composite indexes that SQLModel cannot express via Field alone.
    These are idempotent — IF NOT EXISTS guards prevent duplicate-index errors.

    Why composite indexes?
      - daily_logs(user_id, log_date)       → covers the most common filter pattern
      - exercise_results(user_id, session_date) → accelerates progression queries
      - drill_results(user_id, session_date)    → mirrors exercise pattern
    """
    ddl_statements = [
        # daily_logs: the single most-queried pattern is user_id + date range/equality
        """CREATE INDEX IF NOT EXISTS ix_daily_logs_user_date
           ON daily_logs (user_id, log_date)""",
        # exercise_results: progression queries always filter by user then scan by date
        """CREATE INDEX IF NOT EXISTS ix_exercise_results_user_date
           ON exercise_results (user_id, session_date)""",
        # exercise_results: progression also queries by user + exercise name
        """CREATE INDEX IF NOT EXISTS ix_exercise_results_user_name
           ON exercise_results (user_id, exercise_name)""",
        # drill_results: same pattern as exercise_results
        """CREATE INDEX IF NOT EXISTS ix_drill_results_user_date
           ON drill_results (user_id, session_date)""",
    ]
    try:
        with engine.connect() as conn:
            for stmt in ddl_statements:
                conn.execute(_text(stmt))
            conn.commit()
    except OperationalError as exc:
        # Non-fatal: indexes are a performance hint, not a correctness requirement
        print(f"[FitAI] Ostrzeżenie: nie udało się utworzyć indeksu kompozytowego: {exc}")


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="FitAI API", version="2.0")

# ── slowapi: attach limiter so decorators can find it ────────────────────────
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,   # returns 429 with Retry-After header
)

# ── Klienty AI (Groq primary, Gemini fallback) ───────────────────────────────
_groq_client:  Optional[_groq_module.Groq]  = None
_gemini_ready: bool = False

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",   # VS Code Live Server
    "http://127.0.0.1:5500",
    "null",                    # file:// origin (lokalne otwarcie index.html)
    "https://adamzamorski10-alt.github.io",
    "https://training-coach-app.netlify.app",
    "https://fitai-api-v83w.onrender.com",
    "https://training-coach-api.onrender.com",
]
custom_origins = os.getenv("CORS_ORIGINS", "").strip()
if custom_origins:
    CORS_ORIGINS.extend([o.strip() for o in custom_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    global _groq_client, _gemini_ready

    # ── 1. Inicjalizacja Groq ─────────────────────────────────────────────────
    _groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if _groq_key:
        _groq_client = _groq_module.Groq(api_key=_groq_key)
        print("[FitAI] OK Groq: klient zainicjalizowany (primary AI).")
    else:
        print(
            "[FitAI] WARN GROQ_API_KEY nie jest ustawiony. "
            "Endpointy AI będą używać wyłącznie Gemini (fallback). "
            "Dodaj GROQ_API_KEY do pliku .env, aby włączyć primary AI."
        )

    # ── 2. Inicjalizacja Google Gemini ────────────────────────────────────────
    _gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if _gemini_key:
        genai.configure(api_key=_gemini_key)
        _gemini_ready = True
        print("[FitAI] OK Gemini: klient zainicjalizowany (fallback AI).")
    else:
        print(
            "[FitAI] WARN GEMINI_API_KEY nie jest ustawiony. "
            "Fallback AI jest wyłączony. "
            "Dodaj GEMINI_API_KEY do pliku .env, aby aktywować fallback."
        )

    if not _groq_key and not _gemini_key:
        print(
            "[FitAI] ERROR ŻADEN klucz AI nie jest ustawiony (GROQ_API_KEY, GEMINI_API_KEY). "
            "Endpointy /ai/* i /app/plan/generate zwrócą komunikaty zastępcze."
        )

    # ── 3. Database bootstrap ─────────────────────────────────────────────────
    create_db_and_tables()
    _migrate_json_to_sqlite()


# ─── JSON → SQLite migration helper ──────────────────────────────────────────

def _migrate_json_to_sqlite():
    """One-time migration: imports fitai_users.json into SQLite if file exists."""
    from pathlib import Path
    json_path = Path("fitai_users.json")
    done_flag = Path(".json_migrated")
    if not json_path.exists() or done_flag.exists():
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            old_db: dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return

    with Session(engine) as session:
        for user_key, p in old_db.items():
            if session.exec(select(UserDB).where(UserDB.user_key == user_key)).first():
                continue
            user = UserDB(
                user_key=user_key,
                identity_id=p.get("identity_id"),
                email=p.get("email"),
                name=p.get("name", ""),
                age=p.get("age", 0),
                height=p.get("height", 0),
                weight=p.get("weight", 0),
                start_weight=p.get("start_weight", p.get("weight", 0)),
                target_weight=p.get("target_weight", p.get("weight", 0)),
                gender=p.get("gender", "mężczyzna"),
                goal=p.get("goal", ""),
                frequency=p.get("frequency", ""),
                diet=p.get("diet", ""),
                allergies=p.get("allergies", ""),
                meals_per_day=p.get("meals_per_day", 4),
                notes=p.get("notes", ""),
                plan=p.get("plan", "free"),
                role=p.get("role", "free_user"),
                calories_target=p.get("calories_target", 0),
                protein_target=p.get("protein_target", 0),
                streak_days=p.get("streak_days", 0),
                linked_discord_id=p.get("linked_discord_id"),
            )
            for field, key in [
                ("sports_json", "sports"), ("training_focus_json", "training_focus"),
                ("improvement_areas_json", "improvement_areas"), ("preferred_foods_json", "preferred_foods"),
                ("avoid_foods_json", "avoid_foods"), ("available_equipment_json", "available_equipment"),
                ("avoid_exercises_json", "avoid_exercises"),
            ]:
                user.set_list(field, p.get(key, []))
            if "reminders" in p:
                user.set_dict("reminders_json", p["reminders"])
            if p.get("weekly_plan"):
                user.set_dict("weekly_plan_json", p["weekly_plan"])
            if p.get("substitutes_history"):
                user.set_dict("substitutes_history_json", p["substitutes_history"])
            session.add(user)
            session.flush()  # get user.id

            for log in p.get("logs", []):
                session.add(DailyLogDB(
                    user_id=user.id,
                    log_date=log.get("date", ""),
                    food=log.get("food", ""),
                    workout=log.get("workout", ""),
                    mood=log.get("mood", ""),
                    weight=log.get("weight"),
                    logged_at=log.get("logged_at", datetime.now().isoformat()),
                ))
        session.commit()
    done_flag.touch()
    print("[FitAI] Migration from JSON completed.")


# ─── Health check endpoint ───────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health_check():
    """
    Proste sprawdzenie zdrowia serwera.
    Używane przez frontend do weryfikacji, że backend jest dostępny.
    
    Odpowiedź: 200 OK z JSON { "status": "ok" }
    """
    try:
        # Podstawowa weryfikacja: czy baza danych jest osiągalna
        with Session(engine) as session:
            session.exec(select(UserDB).limit(1))
        
        return {
            "status": "ok",
            "version": "2.0",
            "database": "ok",
            "ai_groq": "ok" if _groq_client is not None else "disabled",
            "ai_gemini": "ok" if _gemini_ready else "disabled",
        }
    except Exception as e:
        print(f"[Health] Database check failed: {e}")
        return {
            "status": "degraded",
            "version": "2.0",
            "database": "error",
            "error": str(e),
        }


# ─── Pydantic request/response models ────────────────────────────────────────

# ─── Auth request/response models ────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    age: int
    height: float
    weight: float
    target_weight: float
    gender: str = "mężczyzna"
    goal: str = "Utrzymanie wagi"
    frequency: str = "3-4 razy w tygodniu"
    diet: str = "Brak preferencji"

    @classmethod
    def __get_validators__(cls):
        yield cls


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRE_MIN * 60   # sekundy
    user_id: str
    name: str
    role: str
    plan: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @classmethod
    def validate_new(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Hasło musi mieć co najmniej 8 znaków")
        return v


class UserProfile(BaseModel):
    name: str
    age: int
    height: float
    weight: float
    target_weight: float
    gender: str = "mężczyzna"
    goal: str
    frequency: str
    training_focus: list[str] = []
    improvement_areas: list[str] = []
    sports: list[str] = []
    diet: str
    allergies: str = ""
    preferred_foods: list[str] = []
    avoid_foods: list[str] = []
    available_equipment: list[str] = []
    avoid_exercises: list[str] = []
    substitutes_history: dict = {}
    meals_per_day: int = 4
    notes: str = ""


class DailyLog(BaseModel):
    food: str = ""
    workout: str = ""
    mood: str = ""
    weight: Optional[float] = None


class AIRequest(BaseModel):
    user_id: str
    extra_context: str = ""


class AppOnboardingRequest(BaseModel):
    identity_id: str
    email: str
    name: str
    age: int
    height: float
    weight: float
    target_weight: float
    gender: str
    goal: str
    frequency: str
    sports: list[str] = []
    training_focus: list[str] = []
    improvement_areas: list[str] = []
    diet: str
    allergies: str = ""
    preferred_foods: list[str] = []
    avoid_foods: list[str] = []
    available_equipment: list[str] = []
    avoid_exercises: list[str] = []
    meals_per_day: int = 4
    notes: str = ""


class AppDailyCheckinRequest(BaseModel):
    food: str = ""
    workout: str = ""
    mood: str = ""
    weight: Optional[float] = None
    # ── Recovery / autoregulation fields (used by RECOVERY_PROMPT) ───────────
    mood_score: Optional[int] = Field(
        default=None, ge=1, le=10,
        description="Nastrój 1–10 (opcjonalne, uzupełnia pole mood)"
    )
    energy_score: Optional[int] = Field(
        default=None, ge=1, le=10,
        description="Poziom energii 1–10"
    )
    soreness: Optional[str] = Field(
        default=None,
        description="Opis zakwasów / bólu, np. 'klatka piersiowa, uda'"
    )


class DiscordLinkRequest(BaseModel):
    identity_id: str
    discord_user_id: str


class PlanUpdateRequest(BaseModel):
    plan: str


class ReminderPrefsRequest(BaseModel):
    email_enabled: bool = True
    discord_enabled: bool = True
    discord_channel_id: Optional[str] = None


class PlanGenerateRequest(BaseModel):
    force: bool = False


class PlanSwapRequest(BaseModel):
    day_index: int
    section: str
    item_index: int
    alternative_index: int


class DrillResultRequest(BaseModel):
    """Wynik sesji drilla sportowego z oceną RPE.
    
    Pola zależą od typu drilla:
    - Rzuty: success_count + total_attempts
    - Bieg/Sprint: time_seconds + distance_meters
    """
    drill_name: str
    rpe: int = Field(ge=1, le=10, description="Rate of Perceived Exertion 1-10")
    notes: str = ""
    session_date: Optional[str] = None          # ISO date; jeśli brak → today
    # Rzuty
    success_count: int = 0
    total_attempts: int = 0
    # Bieg / Sprint
    time_seconds: Optional[float] = Field(default=None, gt=0, description="Czas w sekundach")
    distance_meters: Optional[float] = Field(default=None, gt=0, description="Dystans w metrach")
    # Ogólne
    duration_seconds: Optional[int] = Field(default=None, ge=0, description="Czas trwania [s]")
    weight_kg: Optional[float] = Field(default=None, ge=0, description="Obciążenie [kg]")


class SportConfigRequest(BaseModel):
    """Konfiguracja modułu sportowego użytkownika."""
    sport_focus: str                            # np. "koszykówka"
    sport_specialization: str = ""             # np. "rzuty"
    sport_training_days: list[str] = []        # np. ["Środa", "Sobota"]


class ExerciseResultRequest(BaseModel):
    """Wpis wyniku ćwiczenia z oceną RPE."""
    exercise_name: str
    sets: int
    reps: int
    weight_kg: float
    rpe: int = Field(ge=1, le=10, description="Rate of Perceived Exertion 1-10")
    notes: str = ""
    session_date: Optional[str] = None  # ISO date; jeśli brak → today


# ─── Pure-logic helpers ────────────────────────────────────────────────────────

def _web_user_key(identity_id: str) -> str:
    return f"web:{identity_id}"


def _normalize_plan(plan_raw: str) -> str:
    return "pro" if (plan_raw or "").strip().lower() in {"pro", "premium", "paid"} else "free"


def _role_for_plan(plan: str) -> str:
    return "pro_user" if plan == "pro" else "free_user"


def calc_calories(p: dict | UserDB) -> int:
    """Mifflin-St Jeor + TDEE. Accepts both dict and ORM object."""
    if isinstance(p, UserDB):
        p = p.to_profile_dict()
    w, h, a = p.get("weight", 75), p.get("height", 175), p.get("age", 25)
    gender = str(p.get("gender", "")).lower()
    bmr = 10 * w + 6.25 * h - 5 * a + (-161 if "kobieta" in gender or "female" in gender else 5)
    freq = str(p.get("frequency", "")).lower()
    for key, mult in [("codziennie", 1.9), ("5-6", 1.725), ("3-4", 1.55), ("1-2", 1.375)]:
        if key in freq:
            break
    else:
        mult = 1.2
    tdee = int(bmr * mult)
    goal = str(p.get("goal", "")).lower()
    if any(x in goal for x in ["redukcj", "odchudzani", "schud"]):
        tdee -= 400
    elif any(x in goal for x in ["masa", "budow", "przyty"]):
        tdee += 300
    return tdee


def calc_protein(p: dict | UserDB) -> int:
    if isinstance(p, UserDB):
        p = p.to_profile_dict()
    w = p.get("weight", 75)
    goal = str(p.get("goal", "")).lower()
    if "masa" in goal:
        return int(w * 2.0)
    if "redukcj" in goal:
        return int(w * 2.2)
    return int(w * 1.6)


# ─── Carb Cycling macros ──────────────────────────────────────────────────────

_HEAVY_MUSCLE_GROUPS = {"nogi", "plecy", "full body", "cardio"}
_REST_KEYWORDS = {"odpoczynek", "rest", "regeneracja"}

# Mapowanie partii z frontendu na klucze w bazie ćwiczeń (pool)
_MUSCLE_MAP = {
    "ramiona": "barki",
    "core": "brzuch",
    "pośladki": "nogi",
    "brzuch": "brzuch",
    "klatka": "klatka",
    "plecy": "plecy",
    "nogi": "nogi"
}

def _day_type(day_name: str, focus: str) -> str:
    """Returns 'heavy', 'moderate', or 'rest' for carb cycling logic."""
    lower = day_name.lower()
    if any(k in lower for k in _REST_KEYWORDS):
        return "rest"
    if focus in _HEAVY_MUSCLE_GROUPS:
        return "heavy"
    return "moderate"


def calc_daily_macros(base_calories: int, day_type: str) -> dict:
    """
    Carb Cycling:
      heavy  → +200 kcal, 50% carbs / 30% protein / 20% fat
      moderate → base, 40% / 30% / 30%
      rest   → -200 kcal, 20% carbs / 35% protein / 45% fat (higher fat)
    """
    adjustments = {"heavy": 200, "moderate": 0, "rest": -200}
    macros_pct = {
        "heavy":    {"carbs": 0.50, "protein": 0.30, "fat": 0.20},
        "moderate": {"carbs": 0.40, "protein": 0.30, "fat": 0.30},
        "rest":     {"carbs": 0.20, "protein": 0.35, "fat": 0.45},
    }
    kcal = base_calories + adjustments.get(day_type, 0)
    pct = macros_pct.get(day_type, macros_pct["moderate"])
    return {
        "kcal": kcal,
        "carbs_g": round(kcal * pct["carbs"] / 4),
        "protein_g": round(kcal * pct["protein"] / 4),
        "fat_g": round(kcal * pct["fat"] / 9),
        "day_type": day_type,
    }


# Fix 4: Czytelna etykieta dnia dla promptów AI — zamiast technicznego klucza 'heavy'/'rest'
_DAY_TYPE_LABELS: dict[str, str] = {
    "heavy":    "Dzień Wysokich Węglowodanów (Ciężki Trening)",
    "moderate": "Dzień Umiarkowany (Trening Ogólny)",
    "rest":     "Dzień Odpoczynku / Niskich Węglowodanów",
}

def _day_type_label(day_type: str) -> str:
    """Zwraca czytelną po polsku etykietę dla {day_type} w promptach AI."""
    return _DAY_TYPE_LABELS.get(day_type, day_type)


# ─── Progressive Overload / RPE helpers ───────────────────────────────────────

_RPE_LOW_THRESHOLD = 6    # ≤6 → too easy → increase load
_RPE_HIGH_THRESHOLD = 9   # ≥9 → too hard → decrease or keep

_WEIGHT_INCREMENT_KG = 2.5
_REPS_INCREMENT = 1


def _suggest_progression(
    exercise_name: str,
    recent_results: list[ExerciseResultDB],
) -> dict:
    """
    Analyzes last 3 sessions for a given exercise and returns a progression suggestion.
    Returns: {"suggested_weight_kg": float, "suggested_reps": int, "reason": str}
    """
    if not recent_results:
        return {"suggested_weight_kg": None, "suggested_reps": None, "reason": "brak historii"}

    last = recent_results[0]
    avg_rpe = sum(r.rpe for r in recent_results[:3]) / min(len(recent_results), 3)

    if avg_rpe <= _RPE_LOW_THRESHOLD:
        # Zbyt łatwo – zwiększamy ciężar
        suggested_weight = round(last.weight_kg + _WEIGHT_INCREMENT_KG, 1)
        suggested_reps = last.reps
        reason = f"Średnie RPE={avg_rpe:.1f} (≤{_RPE_LOW_THRESHOLD}) → sugerowane +{_WEIGHT_INCREMENT_KG}kg"
    elif avg_rpe >= _RPE_HIGH_THRESHOLD:
        # Na granicy możliwości – utrzymaj lub zredukuj, dodaj powtórzenie zamiast ciężaru
        suggested_weight = last.weight_kg
        suggested_reps = last.reps + _REPS_INCREMENT
        reason = f"Średnie RPE={avg_rpe:.1f} (≥{_RPE_HIGH_THRESHOLD}) → utrzymaj ciężar, dodaj powtórzenie"
    else:
        # Dobry zakres RPE 7-8 – stopniowo zwiększaj powtórzenia
        suggested_weight = last.weight_kg
        suggested_reps = last.reps + _REPS_INCREMENT
        reason = f"Średnie RPE={avg_rpe:.1f} (7-8) → dodaj powtórzenie, ciężar bez zmiany"

    return {
        "suggested_weight_kg": suggested_weight,
        "suggested_reps": suggested_reps,
        "reason": reason,
        "last_session": last.to_dict(),
        "sessions_analyzed": len(recent_results[:3]),
    }


def _enrich_exercises_with_progression(
    exercises: list,
    user: UserDB,
    session: Session,
) -> list:
    """Adds progression hints to each exercise in a plan day."""
    enriched = []
    for ex in exercises:
        name = ex.get("name", "")
        results = session.exec(
            select(ExerciseResultDB)
            .where(ExerciseResultDB.user_id == user.id)
            .where(ExerciseResultDB.exercise_name == name)
            .order_by(ExerciseResultDB.session_date.desc())
        ).all()
        progression = _suggest_progression(name, list(results))
        enriched.append({**ex, "progression": progression})
    return enriched


# ─── Sports Drills Database ───────────────────────────────────────────────────

SPORT_DRILLS_DB: dict[str, dict[str, list[dict]]] = {
    "koszykówka": {
        "rzuty": [
            {
                "name": "Rzuty osobiste",
                "total_attempts": 20,
                "description": "Standardowe rzuty wolne z linii rzutów osobistych.",
                "progression_tip": "Cel: ≥15/20 (75%) przez 2 sesje z rzędu → zwiększ do 25 prób.",
                "video_url": "https://www.youtube.com/embed/SYqEkm83i-s",
            },
            {
                "name": "Rzuty za 3 punkty",
                "total_attempts": 20,
                "description": "5 rzutów z 4 różnych pozycji za łukiem (corners, wings, top).",
                "progression_tip": "Cel: ≥10/20 (50%) → dodaj 5 prób lub utrudnij pozycje.",
                "video_url": "https://www.youtube.com/embed/SfTLSvFkFak",
            },
            {
                "name": "Rzuty z odchylenia",
                "total_attempts": 15,
                "description": "Mid-range pull-up jump shot po jednym lub dwóch krokach.",
                "progression_tip": "Cel: ≥10/15 (67%) → dodaj obrońcę lub skróć czas wykonania.",
            },
            {
                "name": "Mikan Drill",
                "total_attempts": 40,
                "description": "Naprzemienne layupy z obu stron tablicy (20 z lewej + 20 z prawej).",
                "progression_tip": "Cel: ≥34/40 (85%) → przejdź do Power Mikan (po zbiórce).",
                "video_url": "https://www.youtube.com/embed/pJCGCEol1K0",
            },
        ],
        "drybling": [
            {
                "name": "Figure-8 Dribbling",
                "total_attempts": 10,
                "description": "Ósemka między nogami – 10 pełnych okrążeń bez zgubienia piłki.",
                "progression_tip": "Cel: 10/10 bez błędu → przyspiesz tempo lub zamknij oczy.",
            },
            {
                "name": "Stationary Crossover",
                "total_attempts": 20,
                "description": "Crossover przed ciałem – 20 powtórzeń na stronę.",
                "progression_tip": "Cel: 20/20 → wprowadź krok do przodu (live dribble).",
            },
        ],
        "obrona": [
            {
                "name": "Defensive Slides",
                "total_attempts": 10,
                "description": "10 powtórzeń ślizgów obronnych w obie strony (bez krzyżowania nóg).",
                "progression_tip": "Cel: 10/10 ze stabilną pozycją → dodaj zmianę kierunku.",
            },
        ],
    },
}

_DRILL_ACCURACY_HIGH = 0.70   # ≥70% trafień → łatwe → progresja w górę
_DRILL_RPE_LOW = 5            # RPE ≤5 przy wysokiej skuteczności → zdecydowanie za łatwe
_DRILL_ATTEMPTS_INCREMENT = 5  # Ile prób dodajemy przy progresji


def _suggest_drill_progression(
    drill_name: str,
    recent_results: list[DrillResultDB],
) -> dict:
    """
    Analizuje historię drilli i sugeruje progresję.
    Zwraca: {suggested_attempts, reason, last_accuracy_pct, sessions_analyzed}
    """
    if not recent_results:
        return {
            "suggested_attempts": None,
            "reason": "brak historii – zacznij od bazowej liczby prób",
            "last_accuracy_pct": None,
            "sessions_analyzed": 0,
        }

    last = recent_results[0]
    analyzed = recent_results[:3]
    avg_accuracy = sum(
        (r.success_count / r.total_attempts) if r.total_attempts else 0
        for r in analyzed
    ) / len(analyzed)
    avg_rpe = sum(r.rpe for r in analyzed) / len(analyzed)

    current_attempts = last.total_attempts

    if avg_accuracy >= _DRILL_ACCURACY_HIGH and avg_rpe <= _DRILL_RPE_LOW:
        suggested = current_attempts + _DRILL_ATTEMPTS_INCREMENT
        reason = (
            f"Skuteczność {avg_accuracy:.0%} przy RPE={avg_rpe:.1f} – wyraźnie za łatwe. "
            f"Zwiększ do {suggested} prób lub utrudnij warunki (bliższy obrońca, szybsze tempo)."
        )
    elif avg_accuracy >= _DRILL_ACCURACY_HIGH:
        suggested = current_attempts + _DRILL_ATTEMPTS_INCREMENT
        reason = (
            f"Skuteczność {avg_accuracy:.0%} (≥{_DRILL_ACCURACY_HIGH:.0%}) – dobry moment na progresję. "
            f"Sugerowane: {suggested} prób lub zmiana wariantu drilla."
        )
    else:
        suggested = current_attempts
        reason = (
            f"Skuteczność {avg_accuracy:.0%} – kontynuuj na {current_attempts} próbach "
            f"aż osiągniesz ≥{_DRILL_ACCURACY_HIGH:.0%} przez 2 sesje z rzędu."
        )

    return {
        "suggested_attempts": suggested,
        "reason": reason,
        "last_accuracy_pct": round(avg_accuracy * 100),
        "sessions_analyzed": len(analyzed),
    }



# ─── XP / Leveling system ─────────────────────────────────────────────────────

# Progi XP dla kolejnych poziomów (index 0 = poziom 1 = 0 pkt)
# Level N wymaga sumy: 0, 500, 1200, 2200, 3500, 5500, 8000, 11500, 16000, 22000 …
# Progi XP: każdy level wymaga 100 XP więcej niż poprzedni.
# Poziom 1 = 0, Poziom 2 = 100, Poziom 3 = 200, ..., Poziom 20 = 1900
# (zgodnie z wymogiem: 100 XP = Level Up)
_XP_THRESHOLDS = [i * 100 for i in range(20)]  # [0, 100, 200, 300, ..., 1900]

# XP per akcja
# ── Stałe XP (zgodne z wymaganiami projektu) ─────────────────────────────────
# Progi specyfikowane przez produkt: 100 XP = awans o poziom (Level Up)
# Stałe calibrowane tak, że aktywny użytkownik (3 akcje/dzień) awansuje co ~4-5 dni.
_XP_CHECKIN        = 10   # codzienne logowanie check-inu
_XP_MEAL_LOGGED    = 5    # zaznaczenie posiłku (max 25 XP/dzień)
_XP_WEIGHT_LOGGED  = 15   # wpis wagi
_XP_WORKOUT_LOGGED = 50   # wpis treningu (podwyższono wg specyfikacji)
_XP_WATER_LOGGED   = 5    # zalogowanie min. 500ml wody (nowe)
_XP_STREAK_BONUS   = 10   # bonus za każdy dzień streaku (max 100 XP)


def _xp_to_level(total_xp: int) -> int:
    """Zwraca aktualny poziom na podstawie łącznych punktów XP."""
    level = 1
    for i, threshold in enumerate(_XP_THRESHOLDS):
        if total_xp >= threshold:
            level = i + 1
        else:
            break
    return min(level, len(_XP_THRESHOLDS))


def _xp_to_next_level(total_xp: int) -> dict:
    """Zwraca informacje o postępie do następnego poziomu."""
    level = _xp_to_level(total_xp)
    current_threshold = _XP_THRESHOLDS[level - 1] if level <= len(_XP_THRESHOLDS) else _XP_THRESHOLDS[-1]
    next_threshold = _XP_THRESHOLDS[level] if level < len(_XP_THRESHOLDS) else None
    if next_threshold is None:
        return {"level": level, "xp": total_xp, "next_level_xp": None, "progress_pct": 100}
    xp_in_level = total_xp - current_threshold
    xp_needed = next_threshold - current_threshold
    return {
        "level": level,
        "xp": total_xp,
        "next_level_xp": next_threshold,
        "xp_in_level": xp_in_level,
        "xp_needed_for_next": xp_needed - xp_in_level,
        "progress_pct": round(xp_in_level / xp_needed * 100) if xp_needed > 0 else 100,
    }


def _award_xp(user: UserDB, points: int, session: Session) -> int:
    """
    Dodaje punkty XP użytkownikowi i commituje zmianę.
    Zwraca nową sumę XP.
    """
    user.total_xp = (user.total_xp or 0) + points
    user.updated_at = datetime.now().isoformat()
    session.commit()
    return user.total_xp


# ─── Overload detection ───────────────────────────────────────────────────────

def _check_overload(
    user_id: int,
    session: Session,
    threshold_pct: float = 0.20,
) -> dict:
    """
    Porównuje wolumen (sets × reps × weight_kg) dwóch ostatnich RÓŻNYCH sesji
    treningowych dla każdego ćwiczenia.

    Zwraca:
        {
          "overload_detected": bool,
          "exercises": [
            {
              "name": str,
              "session_a_date": str,   # starsza sesja
              "session_b_date": str,   # nowsza sesja
              "volume_a": float,
              "volume_b": float,
              "increase_pct": float,   # % wzrostu wolumenu
              "overloaded": bool,      # True jeśli wzrost > threshold_pct
            }, ...
          ]
        }

    Sesja = unikalna data. Jeśli użytkownik ma < 2 sesji dla danego ćwiczenia,
    wpis jest pomijany.
    """
    all_results = list(session.exec(
        select(ExerciseResultDB)
        .where(ExerciseResultDB.user_id == user_id)
        .order_by(ExerciseResultDB.session_date.desc())
    ).all())

    # Grupuj po nazwie ćwiczenia, zachowując kolejność dat
    by_exercise: dict[str, dict[str, float]] = {}
    for r in all_results:
        name = r.exercise_name
        if name not in by_exercise:
            by_exercise[name] = {}
        d = r.session_date
        vol = r.sets * r.reps * r.weight_kg
        by_exercise[name][d] = by_exercise[name].get(d, 0) + vol

    exercises_report = []
    any_overloaded = False

    for name, vol_by_date in by_exercise.items():
        dates_sorted = sorted(vol_by_date.keys(), reverse=True)  # nowsze pierwsze
        if len(dates_sorted) < 2:
            continue
        date_b, date_a = dates_sorted[0], dates_sorted[1]
        vol_b, vol_a = vol_by_date[date_b], vol_by_date[date_a]

        if vol_a == 0:
            continue

        increase_pct = round((vol_b - vol_a) / vol_a * 100, 1)
        overloaded = increase_pct > threshold_pct * 100

        if overloaded:
            any_overloaded = True

        exercises_report.append({
            "name": name,
            "session_a_date": date_a,
            "session_b_date": date_b,
            "volume_a": round(vol_a, 1),
            "volume_b": round(vol_b, 1),
            "increase_pct": increase_pct,
            "overloaded": overloaded,
        })

    # Posortuj: najpierw przeciążone, potem reszta
    exercises_report.sort(key=lambda x: -x["increase_pct"])

    return {
        "overload_detected": any_overloaded,
        "threshold_pct": round(threshold_pct * 100),
        "exercises": exercises_report,
    }


def _compute_streak_days_from_logs(logs: list[DailyLogDB]) -> int:
    if not logs:
        return 0
    unique_days = sorted({l.log_date for l in logs if l.log_date}, reverse=True)
    streak = 0
    expected = date.today()
    for day_str in unique_days:
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            continue
        if d == expected:
            streak += 1
            expected = date.fromordinal(expected.toordinal() - 1)
        elif d < expected:
            break
    return streak


# ─── Dashboard builder ────────────────────────────────────────────────────────

def _build_dashboard(user: UserDB, logs: list[DailyLogDB]) -> dict:
    sorted_logs = sorted(logs, key=lambda l: l.log_date)
    calories_target = user.calories_target or calc_calories(user)
    protein_target = user.protein_target or calc_protein(user)

    weight_points = [
        {"date": l.log_date, "weight": l.weight}
        for l in sorted_logs if l.weight is not None
    ][-30:]

    last_7 = sorted_logs[-7:]
    workout_days = sum(1 for l in last_7 if l.workout)
    consistency = round((workout_days / 7) * 100) if last_7 else 0

    calorie_hit = sum(1 for l in last_7 if l.food)
    protein_hit = sum(
        1 for l in last_7
        if l.food and any(k in l.food.lower() for k in ["kurczak", "jaj", "twar", "protein", "ryba", "indyk"])
    )

    return {
        "weight_series": weight_points,
        "workout_consistency_pct": consistency,
        "calorie_adherence_pct": round((calorie_hit / len(last_7)) * 100) if last_7 else 0,
        "protein_adherence_pct": round((protein_hit / len(last_7)) * 100) if last_7 else 0,
        "streak_days": _compute_streak_days_from_logs(logs),
        "targets": {"calories": calories_target, "protein": protein_target},
    }


# ─── Plan builder ─────────────────────────────────────────────────────────────

def _is_profile_ready_for_plan(user: UserDB) -> bool:
    return all([user.name, user.goal, user.frequency, user.diet, user.weight, user.target_weight])


def _default_meal_catalog(diet: str) -> dict:
    """
    Rozbudowany katalog posiłków — wystarczająco duży, żeby każdy dzień tygodnia
    miał INNE danie. Kandydaci są mieszani pseudolosowo w _build_weekly_plan,
    więc kolejność na liście nie determinuje przypisania do dnia.
    """
    key = (diet or "").lower()

    if "wega" in key:
        return {
            "Śniadanie": [
                ("Owsianka proteinowa z borówkami i nasionami chia", 520),
                ("Tofu scramble z papryką i szpinakiem + chleb żytni", 500),
                ("Pudding chia z mango i masłem migdałowym", 480),
                ("Smoothie bowl: banan, szpinak, granola, nasiona konopi", 490),
                ("Pancakes owsiane z syropem klonowym i owocami leśnymi", 530),
                ("Musli nocne z mlekiem owsianym, malinami i orzechami", 470),
                ("Awokado toast z pastą z ciecierzycy i kiełkami", 510),
            ],
            "Przekąska 1": [
                ("Shake roślinny (białko grochu) + banan", 280),
                ("Hummus z marchewką i selerem naciowym", 260),
                ("Jogurt kokosowy z granolą i malinami", 300),
                ("Jabłko z masłem orzechowym i nasionami słonecznika", 270),
                ("Garść mieszanych orzechów + suszone morele", 290),
                ("Edamame z odrobiną soli morskiej", 240),
                ("Ryżowe wafle z pastą tahini i miodem", 255),
            ],
            "Obiad": [
                ("Tempeh teriyaki z brązowym ryżem i brokułem", 720),
                ("Makaron z bolognese z soczewicy i pomidorami", 690),
                ("Buddha bowl: tofu, komosa ryżowa, warzywa pieczone, tahini", 700),
                ("Curry z ciecierzycą, ziemniakami i szpinakiem + naan", 730),
                ("Burrito z czarną fasolą, awokado, ryżem i salsą", 750),
                ("Zupa tajska z tofu, mlekiem kokosowym i ryżem jaśminowym", 680),
                ("Stir-fry z tempeh, papryką, brokułem i makaronem soba", 710),
            ],
            "Przekąska 2": [
                ("Kanapka razowa z pastą z ciecierzycy i ogórkiem", 310),
                ("Mix świeżych owoców (kiwi, truskawki, winogrona) + migdały", 290),
                ("Baton roślinny daktylowo-orzechowy", 260),
                ("Smoothie: banan, szpinak, mleko migdałowe", 280),
                ("Nachos z guacamole i pico de gallo", 320),
                ("Twaróg sojowy z borówkami i syropem agawy", 270),
                ("Pieczone ciecierzycy z papryką i czosnkiem", 300),
            ],
            "Kolacja": [
                ("Sałatka z czarną fasolą, awokado, kukurydzą i limonką", 520),
                ("Wrap pełnoziarnisty z tofu, rukolą i pesto", 560),
                ("Krem z czerwonej soczewicy z grzankami żytnimi", 500),
                ("Grzybowa zapiekanka z kaszą gryczaną i ziołami", 540),
                ("Sałatka z pieczonym burakiem, orzechami i rukolą", 480),
                ("Zupa miso z tofu, wakame i makaronem ryżowym", 460),
                ("Tacos z jackfruitem, kapustą pekińską i salsą awokado", 530),
            ],
        }

    if "ketogen" in key or "keto" in key:
        return {
            "Śniadanie": [
                ("Jajecznica na boczku z awokado i serem feta", 580),
                ("Omlet z łososiem wędzonym, szpinakiem i śmietaną", 560),
                ("Jajka sadzone z chorizo i pieczonym szparagiem", 540),
                ("Shake MCT: mleko kokosowe, białko, masło migdałowe", 520),
                ("Fritata z boczkiem, papryką i mozarellą", 570),
                ("Jajka gotowane + awokado + oliwa z oliwek + rukola", 510),
                ("Pancakes z mąki migdałowej z masłem i jagodami", 500),
            ],
            "Przekąska 1": [
                ("Plastry ogórka z kremowym serem i łososiem", 220),
                ("Orzechy macadamia + kawałek sera cheddar", 280),
                ("Seler naciowy z masłem orzechowym (bez cukru)", 200),
                ("Jajka na twardo (2 szt.) + oliwa z ziołami", 240),
                ("Plastry salami z serem gouda", 260),
                ("Shake konopny z olejem kokosowym i cynamonem", 230),
                ("Pepperoni + kostki sera + oliwki", 270),
            ],
            "Obiad": [
                ("Łosoś pieczony z kalafiorem w śmietanie i koperkiem", 750),
                ("Stek wołowy z puree z kalafiora i masłem ziołowym", 780),
                ("Kurczak w sosie śmietanowo-grzybowym z fasolką szparagową", 720),
                ("Tuńczyk z awokado, jajkiem, oliwkami i oliwą", 700),
                ("Boczek panierowany w parmezanie z sałatką cezar", 760),
                ("Udka z kurczaka pieczone z warzywami keto i tymiankiem", 740),
                ("Kotlet mielony wieprzowy z kapustą zasmażaną i boczkiem", 730),
            ],
            "Przekąska 2": [
                ("Plastry awokado z solą morską i cytryną", 240),
                ("Wiórki kokosowe + orzechy pekan", 280),
                ("Łyżka masła orzechowego bez cukru + kawałek gorzk. czekolady", 260),
                ("Rollsy z sałatą, szynką parmeńską i serem", 220),
                ("Małe porcje sardynek w oliwie", 230),
                ("Orzechy brazylijskie + plasterek sera brie", 270),
                ("Chips z parmezanu pieczony z rozmarynem", 210),
            ],
            "Kolacja": [
                ("Sałatka z rukolą, boczkiem, jajkiem i parmezanem", 540),
                ("Krewetki na maśle czosnkowym ze szparagami", 520),
                ("Zupa krem z dyni z kokosem i imbirem (keto)", 480),
                ("Pieczony dorsz z pesto bazyliowym i cukinią", 510),
                ("Wrap sałatowy z kurczakiem, awokado i fetą", 500),
                ("Carpaccio wołowe z oliwą, kaparami i parmezanem", 490),
                ("Mielone indycze z cukinią i sosem hollandaise", 530),
            ],
        }

    # ── Dieta standardowa / wysokobiałkowa (domyślna) ─────────────────────────
    return {
        "Śniadanie": [
            ("Owsianka z odżywką białkową, bananem i masłem orzechowym", 520),
            ("Jajecznica z 4 jaj, szpinakiem i pełnoziarnistym tostami", 510),
            ("Skyr z granolą, borówkami i miodem", 480),
            ("Pancakes z twarogiem i musem truskawkowym", 530),
            ("Shake proteinowy: mleko, białko, banan, płatki owsiane", 540),
            ("Musli nocne z jogurtem greckim, malinami i orzechami", 490),
            ("Tosty z awokado, jajkiem sadzonym i kiełkami rzodkiewki", 500),
        ],
        "Przekąska 1": [
            ("Shake białkowy z bananem i mlekiem", 280),
            ("Serek wiejski z papryką i ogórkiem", 300),
            ("Jogurt grecki z owocami i łyżeczką miodu", 250),
            ("Jabłko z masłem orzechowym i garścią orzechów", 270),
            ("Ryżowe wafle z twarogiem i szczypiorkiem", 240),
            ("Koktajl: kefir, truskawki, banan, siemię lniane", 290),
            ("Kanapka razowa z jajkiem na twardo i rzodkiewką", 310),
        ],
        "Obiad": [
            ("Pierś z kurczaka, ryż basmati, brokuł gotowany na parze", 730),
            ("Indyk w sosie pomidorowym, ziemniaki gotowane, surówka", 700),
            ("Łosoś pieczony z kaszą gryczaną i warzywami z piekarnika", 750),
            ("Dorsz w ziołach z puree ziemniaczanym i fasolką szparagową", 680),
            ("Makaron pełnoziarnisty z mięsem mielonym i sosem pomidorowym", 720),
            ("Kurczak tikka masala z ryżem jaśminowym i jogurtem", 760),
            ("Wołowina duszona z kaszą pęczak i buraczkami", 740),
        ],
        "Przekąska 2": [
            ("Kanapka pełnoziarnista z indykiem i rukolą", 320),
            ("Twaróg z borówkami i cynamonem", 290),
            ("Baton proteinowy (20+ g białka)", 260),
            ("Garść migdałów + suszone śliwki", 280),
            ("Koktajl: kefir, banan, łyżka białka", 300),
            ("Serek wiejski z ogórkiem i rzodkiewką", 270),
            ("Szklanka maślanki + 2 ryżowe wafle", 250),
        ],
        "Kolacja": [
            ("Sałatka z tuńczykiem, jajkiem, pomidorem i jogurtowym dressingiem", 520),
            ("Wrap pełnoziarnisty z kurczakiem, awokado i warzywami", 560),
            ("Omlet z 3 jaj z papryką, cebulą i serem żółtym", 500),
            ("Kasza jaglana z pieczoną dynią, fetą i orzechami", 510),
            ("Sałatka grecka z grillowanym kurczakiem i fetą", 490),
            ("Zupa krem z brokułu z grzankami żytnimi i serem", 470),
            ("Pieczony łosoś z sałatką z rukoli, pomidorków i parmezanu", 530),
        ],
    }


def _exercise_pool() -> dict:
    """
    Rozbudowana baza ćwiczeń — każda partia ma 7+ ćwiczeń, żeby
    _build_weekly_plan mógł losować różne zestawy bez powtórzeń w tygodniu.
    """
    return {
        "klatka": [
            {"name": "Wyciskanie sztangi leżąc", "sets": "4", "reps": "6-8",
             "notes": "Łopatki ściągnięte, stopy stabilnie na podłodze.",
             "how_to": "Opuszczaj sztangę do dolnej części klatki, łokcie pod kątem ~45°. Wydech przy wycisku."},
            {"name": "Wyciskanie hantli na skosie dodatnim", "sets": "4", "reps": "8-10",
             "notes": "Ławka 30-45°, kontroluj fazę ekscentryczną (3 sek.).",
             "how_to": "Hantle unieś po łuku nad górną klatkę, nie rozkładaj łokci do boku."},
            {"name": "Wyciskanie hantli na skosie ujemnym", "sets": "3", "reps": "10-12",
             "notes": "Aktywuje dolną część klatki.",
             "how_to": "Ustaw ławkę pod kątem -15° do -30°. Prowadź hantle nad dolną klatkę."},
            {"name": "Rozpiętki na maszynie (pec deck)", "sets": "3", "reps": "12-15",
             "notes": "Skup się na szczytowym napięciu klatki.",
             "how_to": "Na końcu ruchu zatrzymaj dłonie obok siebie przez 1 sekundę."},
            {"name": "Rozpiętki na bramie (kabel dolny)", "sets": "3", "reps": "12-15",
             "notes": "Dolna gałąź kabla — izolacja środkowej i górnej klatki.",
             "how_to": "Prowadź dłonie od bioder ku górze po szerokim łuku, napnij klatkę na szczycie."},
            {"name": "Pompki na poręczach", "sets": "3", "reps": "8-12",
             "notes": "Lekkie pochylenie do przodu = więcej klatki.",
             "how_to": "Zejdź, aż ramię będzie równoległe do podłogi, odepchnij się dynamicznie."},
            {"name": "Pompki szerokie z obciążeniem (talerz na plecach)", "sets": "3", "reps": "10-15",
             "notes": "Wariant dla zaawansowanych bez sprzętu.",
             "how_to": "Rozstaw dłonie szeroko, opuść klatkę blisko podłoża, utrzymaj sztywny tułów."},
            {"name": "Wyciskanie na maszynie Hammera", "sets": "3", "reps": "10-12",
             "notes": "Dobre jako ćwiczenie finiszujące — mniejsze ryzyko kontuzji.",
             "how_to": "Pełny zakres ruchu, wolne opuszczanie, szybki wycisk."},
        ],
        "nogi": [
            {"name": "Przysiad ze sztangą (back squat)", "sets": "4", "reps": "6-8",
             "notes": "Neutralny kręgosłup, kolana podążają za stopami.",
             "how_to": "Cofnij biodra, zejdź poniżej równoległości, wróć wypchnięciem przez pięty."},
            {"name": "Front squat (przysiad ze sztangą z przodu)", "sets": "4", "reps": "6-8",
             "notes": "Większe zaangażowanie czworogłowych i gorsetu.",
             "how_to": "Sztanga na przednich deltoidsach, łokcie wysoko, prostszy tors niż w back squat."},
            {"name": "Rumuński martwy ciąg na prostych nogach", "sets": "3", "reps": "8-10",
             "notes": "Ruch inicjuj biodrem, bez zaokrąglenia lędźwi.",
             "how_to": "Prowadź sztangę blisko ud, poczuj rozciąganie w tylnych udach, wróć napinając pośladki."},
            {"name": "Wykroki bułgarskie (na ławce)", "sets": "3", "reps": "8/strona",
             "notes": "Tylna noga na ławce — głęboka izolacja czworogłowych.",
             "how_to": "Przednia stopa daleko od ławki, zejdź pionowo w dół, odepchnij się z pięty."},
            {"name": "Leg press (prasa nożna)", "sets": "4", "reps": "10-12",
             "notes": "Stopy wyżej = więcej tylnych ud i pośladków.",
             "how_to": "Nie blokuj kolan na szczycie, pełen zakres opuszczania."},
            {"name": "Wyprosty nóg na maszynie", "sets": "3", "reps": "12-15",
             "notes": "Izolacja czworogłowych — dobre jako pre-exhaust.",
             "how_to": "Zatrzymaj się na szczycie przez 1 sekundę, wolne opuszczanie (3 sek.)."},
            {"name": "Uginanie nóg leżąc (leg curl)", "sets": "3", "reps": "10-12",
             "notes": "Pełny zakres ruchu, bez wyrywania bioder.",
             "how_to": "Ugnij nogi do maksimum, zatrzymaj, wolno wróć do wyprostu."},
            {"name": "Wspięcia na palce stojąc (łydki)", "sets": "4", "reps": "15-20",
             "notes": "Pełen zakres — od pełnego rozciągnięcia do pełnego uniesienia.",
             "how_to": "Zatrzymaj się na szczycie 2 sekundy, opuść powoli, poczuj rozciągnięcie."},
        ],
        "plecy": [
            {"name": "Martwy ciąg konwencjonalny", "sets": "4", "reps": "4-6",
             "notes": "Król ćwiczeń wielostawowych — priorytet techniczny.",
             "how_to": "Biodra nisko, klatka wypięta, sztanga przy goleniach, wyprost bioder i kolan jednocześnie."},
            {"name": "Podciąganie nachwytem (szerokim chwytem)", "sets": "4", "reps": "6-10",
             "notes": "Aktywuj łopatki przed ruchem (scapular pull).",
             "how_to": "Zwis aktywny → podciągnięcie klatki do drążka → wolne opuszczanie (3 sek.)."},
            {"name": "Podciąganie podchwytem (supination)", "sets": "3", "reps": "8-10",
             "notes": "Większe zaangażowanie bicepsów, wąski chwyt.",
             "how_to": "Dłonie skierowane do siebie, opuszczaj z pełnym wyprostem łokci."},
            {"name": "Wiosłowanie sztangą w opadzie tułowia", "sets": "4", "reps": "6-8",
             "notes": "Tułów pod 45°, ściągaj sztangę do brzucha.",
             "how_to": "Utrzymaj napięty brzuch i prosty grzbiet przez cały ruch."},
            {"name": "Wiosłowanie hantlem jednostronnie", "sets": "3", "reps": "8-12/strona",
             "notes": "Łokieć blisko tułowia, ruch do biodra.",
             "how_to": "Podpórz się wolną ręką i kolanem na ławce, pełny zakres ruchu."},
            {"name": "Ściąganie drążka wyciągu do klatki (szeroki chwyt)", "sets": "3", "reps": "10-12",
             "notes": "Prowadź drążek do górnej klatki, ściągaj łopatki.",
             "how_to": "Lekkie odchylenie tułowia, ściągnij drążek do mostka, powoli wróć."},
            {"name": "Wiosłowanie na maszynie siedząc (cable row)", "sets": "3", "reps": "10-12",
             "notes": "Brak ruchu tułowia — czysta izolacja pleców.",
             "how_to": "Przyciągnij rączki do brzucha, zatrzymaj z ściągniętymi łopatkami."},
            {"name": "Szrugsy ze sztangą (czworoboczny kapturowy)", "sets": "3", "reps": "12-15",
             "notes": "Ruch pionowy, bez rotacji barków.",
             "how_to": "Unieś barki pionowo ku uszom i powoli opuść z kontrolą."},
        ],
        "barki": [
            {"name": "Wyciskanie żołnierskie (military press) ze sztangą", "sets": "4", "reps": "6-8",
             "notes": "Brak przeprostu lędźwi, aktywny brzuch.",
             "how_to": "Ze sztangą na poziomie obojczyków, wyciśnij pionowo nad głowę, łokcie lekko przed tułowiem."},
            {"name": "Wyciskanie hantli nad głowę siedząc", "sets": "3", "reps": "8-10",
             "notes": "Oparcie ławki ustawione pionowo lub lekko odchylone.",
             "how_to": "Prowadź hantle pionowo, w górze zbliż do siebie bez uderzania."},
            {"name": "Arnold press", "sets": "3", "reps": "10-12",
             "notes": "Rotacja angażuje przedni i środkowy akton barku.",
             "how_to": "Start z dłońmi ku sobie na wysokości brody → obróć w górę i wyciśnij."},
            {"name": "Unoszenie hantli bokiem (lateral raise)", "sets": "4", "reps": "12-15",
             "notes": "Ruch bez szarpania, lekkie ugięcie łokci.",
             "how_to": "Unieś hantle do poziomu barków, zatrzymaj 1 sek., powoli opuść."},
            {"name": "Unoszenie hantli przodem (front raise)", "sets": "3", "reps": "10-12",
             "notes": "Angażuje przedni akton barku.",
             "how_to": "Prowadź hantle do wysokości oczu z lekkim ugięciem łokcia."},
            {"name": "Face pull na wyciągu (z liną)", "sets": "4", "reps": "15-20",
             "notes": "Kluczowe dla zdrowia stawów ramiennych — nie pomijaj.",
             "how_to": "Wyciąg na wysokości głowy, przyciągnij linę do twarzy z rotacją zewnętrzną."},
            {"name": "Odwrotne rozpiętki na maszynie (rear delt fly)", "sets": "3", "reps": "12-15",
             "notes": "Tylny akton barku i górne plecy.",
             "how_to": "Usiądź przodem do maszyny, rozłóż ramiona jak skrzydła, zatrzymaj na szczycie."},
        ],
        "biceps": [
            {"name": "Uginania ze sztangą stojąc", "sets": "4", "reps": "8-10",
             "notes": "Brak bujanias tułowia, łokcie przy boku.",
             "how_to": "Pełny wyprost w dole, ugnij do szczytowego napięcia i powoli opuść."},
            {"name": "Uginania hantlami naprzemiennie", "sets": "3", "reps": "10/strona",
             "notes": "Supinacja nadgarstka w górnej fazie ruchu.",
             "how_to": "Ugnij, obracając dłoń ku górze, zatrzymaj u góry 1 sek., powoli opuść."},
            {"name": "Uginania hantlem na modlitewniku (concentration curl)", "sets": "3", "reps": "10-12/strona",
             "notes": "Maksymalna izolacja bicepsa.",
             "how_to": "Łokieć oparty o wewnętrzną stronę uda, pełen zakres ruchu."},
            {"name": "Uginania na wyciągu (cable curl)", "sets": "3", "reps": "12-15",
             "notes": "Stałe napięcie mięśnia przez cały ruch.",
             "how_to": "Stój blisko wyciągu, ugnij ku ramionom i wolno wróć."},
            {"name": "Uginania młotkowe (hammer curl)", "sets": "3", "reps": "10-12",
             "notes": "Angażuje brachialis i brachioradialis.",
             "how_to": "Neutralny chwyt (kciuk ku górze), ugnij pionowo, bez rotacji nadgarstka."},
            {"name": "Spider curl na ławce skośnej", "sets": "3", "reps": "10-12",
             "notes": "Brak możliwości użycia inercji — czysta praca bicepsa.",
             "how_to": "Połóż się klatką na ławce pod 45°, ramiona zwisają swobodnie, uginaj ku twarzy."},
        ],
        "triceps": [
            {"name": "Wyciskanie wąskim chwytem", "sets": "4", "reps": "6-8",
             "notes": "Chwyp na szerokość barków, łokcie blisko tułowia.",
             "how_to": "Opuszczaj sztangę do dolnej klatki, wyciśnij z tricepsów, nie z klatki."},
            {"name": "Prostowanie ramion na wyciągu (pushdown)", "sets": "3", "reps": "12-15",
             "notes": "Łokcie przy tułowiu przez cały ruch.",
             "how_to": "Naciśnij drążek/linę do bioder, zatrzymaj, powoli wróć do 90°."},
            {"name": "Skull crushers (łamiące czaszkę) z hantlami", "sets": "3", "reps": "10-12",
             "notes": "Długa głowa tricepsa — ruch ponad głowę.",
             "how_to": "Leż na ławce, opuść hantle ku czołu, wyciśnij pionowo nad klatkę."},
            {"name": "French press ze sztangą stojąc", "sets": "3", "reps": "10-12",
             "notes": "Zaangażowanie długiej głowy przy stałym napięciu.",
             "how_to": "Unieś sztangę nad głowę, zegnij w łokciach, opuść za głowę i wróć."},
            {"name": "Triceps kick-back hantlem", "sets": "3", "reps": "12-15/strona",
             "notes": "Izolacja bocznej i środkowej głowy tricepsa.",
             "how_to": "Tułów w opadzie, łokieć przy boku na poziomie tułowia, wyciągnij ramię do tyłu."},
            {"name": "Pompki na poręczach (triceps dips)", "sets": "3", "reps": "8-12",
             "notes": "Pionowy tułów = więcej tricepsa, pochylony = klatka.",
             "how_to": "Zejdź do 90° w łokciu, odepchnij przez tricepsy, nie rozchylaj łokci."},
        ],
        "brzuch": [
            {"name": "Plank przedni", "sets": "3", "reps": "45-60 s",
             "notes": "Linia bark–biodro–kostka, brak opadania bioder.",
             "how_to": "Napnij brzuch, pośladki i uda. Oddychaj spokojnie. Wzrok ku podłodze."},
            {"name": "Dead bug", "sets": "3", "reps": "10/strona",
             "notes": "Lędźwia DOCIŚNIĘTE do podłogi przez cały ruch.",
             "how_to": "Opuszczaj naprzemiennie prostowaną nogę i przeciwne ramię, zachowując kontakt pleców z podłogą."},
            {"name": "Unoszenie nóg w zwisie na drążku", "sets": "3", "reps": "8-12",
             "notes": "Bez bujania — kontrolowany ruch.",
             "how_to": "Unieś nogi zgięte lub proste przez napięcie brzucha. Opuść powoli."},
            {"name": "Kółka ab wheel (rollout)", "sets": "3", "reps": "6-10",
             "notes": "Zaawansowane — nie wypuszczaj bioder na dół.",
             "how_to": "Powoli toczysz kółko do przodu, utrzymuj napięty brzuch i proste plecy, wróć kontrolując."},
            {"name": "Hollow body hold", "sets": "3", "reps": "30-45 s",
             "notes": "Baza gimnastyczna — napięcie przez cały czas.",
             "how_to": "Leż na plecach, wyciągnij ręce za głowę, unieś nogi i barki, wciśnij dolną część pleców."},
            {"name": "Crunch na maszynie z linką", "sets": "3", "reps": "15-20",
             "notes": "Stałe napięcie dzięki ciężarowi — kontroluj prędkość.",
             "how_to": "Stój lub klęcz przed wyciągiem, zgiń kręgosłup w zgięciu, nie ciągnij szyją."},
            {"name": "Side plank z rotacją (thread the needle)", "sets": "3", "reps": "8/strona",
             "notes": "Skośne + stabilizacja boczna w jednym ćwiczeniu.",
             "how_to": "Pozycja side plank, przeciągnij górną rękę pod tułowiem i wróć do góry."},
        ],
        "full body": [
            {"name": "Martwy ciąg konwencjonalny", "sets": "4", "reps": "5-6",
             "notes": "Wzorzec ruchowy numer jeden — cały łańcuch tylny.",
             "how_to": "Sztanga nad stopami, klatka wysoko, napnij brzuch i wyciągnij pionowo."},
            {"name": "Clean & press (podrzut + wycisk)", "sets": "3", "reps": "5-6",
             "notes": "Ćwiczenie balistyczne — siła eksplozywna i koordynacja.",
             "how_to": "Szybko podciągnij sztangę do ramion i natychmiast wyciśnij nad głowę."},
            {"name": "Przysiad ze sztangą", "sets": "3", "reps": "8",
             "notes": "Łączy nogi, tułów i stabilizację.",
             "how_to": "Pełna głębokość, pięty na podłodze, kolana na zewnątrz."},
            {"name": "Podciąganie nachwytem", "sets": "3", "reps": "6-8",
             "notes": "Górna część ciała — plecy i biceps.",
             "how_to": "Aktywny zwis, podciągnięcie klatki do drążka, kontrolowane opuszczanie."},
            {"name": "Kettlebell swing", "sets": "4", "reps": "15",
             "notes": "Moc bioder, wytrzymałość mięśniowa, cardio.",
             "how_to": "Ruch bioder (hip hinge), nie przysiad. Kettlebell wychyla się ruchem bioder, nie rąk."},
            {"name": "Turkish get-up (TGU)", "sets": "3", "reps": "3/strona",
             "notes": "Stabilizacja, mobilność, siła funkcjonalna.",
             "how_to": "Powolny, kontrolowany ruch przez każdy etap — oczy na dzwonku przez cały czas."},
        ],
        "cardio": [
            {"name": "Interwały HIIT na bieżni (30 s sprint / 90 s marsz)", "sets": "8", "reps": "1 runda",
             "notes": "Monitoruj tętno — sprint >85% HRmax, marsz <65%.",
             "how_to": "Rozgrzewka 5 min marszu, 8 rund interwałów, schłodzenie 5 min."},
            {"name": "Ergometr wioślarski (steady state)", "sets": "1", "reps": "20 min",
             "notes": "Tempo średnie, 500m split ~2:20-2:40.",
             "how_to": "Nogi → tułów → ręce w fazie pchania; ręce → tułów → nogi w powrocie."},
            {"name": "Skakanka (double under lub single)", "sets": "5", "reps": "1 min",
             "notes": "Odpoczynek 30 s między seriami.",
             "how_to": "Nadgarstki przy biodrach, drobne skoki, rytmiczne obroty nadgarstkami."},
            {"name": "Box jumps (skoki na skrzynię)", "sets": "4", "reps": "8",
             "notes": "Miękkie lądowanie na całej stopie — nie na palcach.",
             "how_to": "Dołek z zamachu ramion → eksplozywny odskok → lądowanie w przysiadzie na skrzyni."},
            {"name": "Burpees", "sets": "5", "reps": "10",
             "notes": "Pełny zakres — klatka dotyka podłogi, pełny skok z klaśnięciem.",
             "how_to": "Padnij, pompka, wróć do przysiadu, eksploduj do góry z oklaśnięciem nad głową."},
            {"name": "Atak rowerowy (assault bike) — tabata", "sets": "8", "reps": "20 s sprint / 10 s odpocz.",
             "notes": "Wyczerpujące — maksymalny wysiłek w fazach sprintu.",
             "how_to": "W fazie sprintu pełna moc rękoma i nogami, faza odpoczynku to aktywne pedałowanie."},
        ],
    }


def _build_weekly_plan(user: UserDB) -> dict:
    """
    Buduje tygodniowy plan z Carb Cycling + unikalnymi posiłkami i ćwiczeniami
    na każdy dzień. Zamiast `i % len(list)` używamy przetasowanego indeksu,
    dzięki czemu każdy dzień dostaje INNE zestawy posiłków i ćwiczeń.
    """
    profile = user.to_profile_dict()
    meal_catalog = _default_meal_catalog(profile.get("diet", ""))
    pool = _exercise_pool()

    base_calories = user.calories_target or calc_calories(user)

    focus = [x.lower() for x in user.get_list("training_focus_json") if isinstance(x, str)]
    improve = [x.lower() for x in user.get_list("improvement_areas_json") if isinstance(x, str)]
    preferred = focus + [x for x in improve if x not in focus]
    if not preferred:
        preferred = ["klatka", "plecy", "nogi", "brzuch", "barki"]

    preferred_foods = [x.lower() for x in user.get_list("preferred_foods_json")]
    avoid_foods = [x.lower() for x in user.get_list("avoid_foods_json")]
    avoid_exercises = [x.lower() for x in user.get_list("avoid_exercises_json")]

    # ─── Sport module configuration ───────────────────────────────────────────
    sport_focus = (user.sport_focus or "").lower().strip()
    sport_spec = (user.sport_specialization or "").lower().strip()
    sport_days = {d.strip() for d in user.get_list("sport_training_days_json")}

    _sport_drills: list[dict] = []
    if sport_focus and sport_focus in SPORT_DRILLS_DB:
        spec_map = SPORT_DRILLS_DB[sport_focus]
        if sport_spec in spec_map:
            _sport_drills = spec_map[sport_spec]
        elif spec_map:
            _sport_drills = next(iter(spec_map.values()))

    week_schedule = [
        ("Poniedziałek", False), ("Wtorek", False), ("Środa", False),
        ("Czwartek", False), ("Piątek", False), ("Sobota", False),
        ("Niedziela", True),
    ]
    meal_slots = ["Śniadanie", "Przekąska 1", "Obiad", "Przekąska 2", "Kolacja"]

    # ─── Przetasuj posiłki dla każdego slotu raz na cały tydzień ─────────────
    # Każdy slot dostaje listę kandydatów w losowej kolejności.
    # Dzień i bierze kandydata o indeksie i → brak powtórzeń przez 7 dni
    # (o ile lista ma ≥7 pozycji, co zapewniamy w _default_meal_catalog).
    rng_seed = hash(user.user_key + datetime.now().strftime("%Y-%W"))  # stały seed dla danego tygodnia
    rng = random.Random(rng_seed)

    shuffled_meals: dict[str, list] = {}
    for slot in meal_slots:
        candidates = list(meal_catalog.get(slot, []))
        rng.shuffle(candidates)
        shuffled_meals[slot] = candidates

    # ─── Rozdziel partie treningowe na dni ────────────────────────────────────
    # Budujemy listę partii dla dni treningowych (bez niedzieli i dni sportowych),
    # żeby każda partia pojawiła się raz i nie powielała sąsiednich.
    training_days_count = sum(
        1 for (day_name, is_rest) in week_schedule
        if not is_rest and not (bool(_sport_drills) and day_name in sport_days)
    )

    # Rozwiń preferred do rozmiaru liczby dni treningowych — bez powtórzeń o ile możliwe
    if len(preferred) >= training_days_count:
        day_focuses_pool = preferred[:training_days_count]
    else:
        # Powtarzamy partie, ale tak, żeby sąsiednie dni się nie duplikowały
        day_focuses_pool = []
        prev = None
        extended = preferred * (training_days_count // len(preferred) + 2)
        for p in extended:
            if p != prev:
                day_focuses_pool.append(p)
                prev = p
            if len(day_focuses_pool) >= training_days_count:
                break

    rng.shuffle(day_focuses_pool)  # przetasuj partie — różna kolejność każdego tygodnia
    focus_iter = iter(day_focuses_pool)

    # ─── Przetasuj ćwiczenia wewnątrz każdej partii ───────────────────────────
    shuffled_pool: dict[str, list] = {}
    for key, exercises in pool.items():
        ex_copy = list(exercises)
        rng.shuffle(ex_copy)
        shuffled_pool[key] = ex_copy

    days = []
    for day_idx, (day_name, is_rest) in enumerate(week_schedule):
        is_sport_day = bool(_sport_drills) and (day_name in sport_days)

        # ─── Wyznacz typ dnia i makro ─────────────────────────────────────────
        if is_rest:
            day_type = "rest"
            focus_key = "odpoczynek"
        elif is_sport_day:
            day_type = "heavy"   # sesja sportowa = ciężki dzień kaloryczny
            focus_key = sport_focus
        else:
            raw_focus = next(focus_iter, preferred[0])
            # Rozwiąż mapowanie (np. ramiona -> barki)
            focus_key = _MUSCLE_MAP.get(raw_focus, raw_focus)
            if focus_key not in pool:
                focus_key = "klatka"
            day_type = _day_type(day_name, focus_key)

        macros = calc_daily_macros(base_calories, day_type)

        # ─── Ćwiczenia ────────────────────────────────────────────────────────
        if is_rest:
            workout_items = []
            workout_title = "Odpoczynek / Aktywna regeneracja"
            is_sport_session = False
        elif is_sport_day:
            workout_items = [
                {
                    "name": drill["name"],
                    "total_attempts": drill["total_attempts"],
                    "description": drill["description"],
                    "progression_tip": drill["progression_tip"],
                    "sets": "—",
                    "reps": f"{drill['total_attempts']} prób",
                    "notes": drill["description"],
                    "how_to": drill["progression_tip"],
                    "alternatives": [],
                }
                for drill in _sport_drills
            ]
            spec_label = sport_spec.title() if sport_spec else "Specjalistyczna"
            workout_title = f"Sesja Sportowa – {sport_focus.title()} ({spec_label})"
            is_sport_session = True
        else:
            # Wybierz 4 różne ćwiczenia z przetasowanej partii (brak powtórzeń w dniu)
            available_ex = [
                ex for ex in shuffled_pool.get(focus_key, pool.get(focus_key, []))
                if not any(a in ex["name"].lower() for a in avoid_exercises)
            ] or shuffled_pool.get(focus_key, pool.get(focus_key, []))

            selected = available_ex[:4]
            workout_items = []
            for ex in selected:
                # Alternatywy: inne ćwiczenia tej samej partii (nie wybrane) + 1 z innej partii
                same_group_alts = [a for a in available_ex if a["name"] != ex["name"]]
                # Dobierz alternatywę z sąsiedniej partii dla urozmaicenia
                complement_keys = [k for k in preferred if k != focus_key and k in pool]
                if complement_keys:
                    comp_key = complement_keys[day_idx % len(complement_keys)]
                    same_group_alts.extend(shuffled_pool.get(comp_key, pool.get(comp_key, []))[:1])
                workout_items.append({
                    **ex,
                    "alternatives": [
                        {"name": a["name"], "sets": a["sets"], "reps": a["reps"]}
                        for a in same_group_alts[:3]
                    ],
                })
            workout_title = f"Sesja {focus_key.title()}"
            is_sport_session = False

        # ─── Posiłki ──────────────────────────────────────────────────────────
        meals = []
        for slot in meal_slots:
            candidates = shuffled_meals.get(slot, [])

            # Filtruj preferowane / zakazane
            if preferred_foods:
                pref_c = [c for c in candidates if any(p in c[0].lower() for p in preferred_foods)]
                if pref_c:
                    candidates = pref_c
            if avoid_foods:
                filtered = [c for c in candidates if not any(av in c[0].lower() for av in avoid_foods)]
                if filtered:
                    candidates = filtered

            # Wybierz posiłek dla tego dnia (day_idx jako indeks w przetasowanej liście)
            if not candidates:
                candidates = meal_catalog.get(slot, [("Posiłek", 500)])

            main = candidates[day_idx % len(candidates)]
            alt = [{"name": c[0], "kcal": c[1]} for c in candidates if c[0] != main[0]][:3]
            meals.append({"slot": slot, "name": main[0], "kcal": main[1], "alternatives": alt})

        days.append({
            "day": day_name,
            "day_type": day_type,
            "macros": macros,
            "is_sport_session": is_sport_session,
            "workout": {
                "title": workout_title,
                "focus": sport_focus if is_sport_session else focus_key,
                "is_sport_session": is_sport_session,
                "sport": sport_focus if is_sport_session else None,
                "specialization": sport_spec if is_sport_session else None,
                "exercises": workout_items,
            },
            "meals": meals,
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "weekly_goal": user.goal,
        "days": days,
    }



# ─── AI helper — Groq (primary) + Gemini (fallback) ──────────────────────────

# Sentinel: subklasa str — caller może sprawdzić isinstance(result, _AIError)
# żeby zdecydować czy podnieść HTTP 503, zamiast traktować to jako pusty tekst.
class _AIError(str):
    """Oznacza odpowiedź zwróconą przez fallback lokalny, nie przez AI."""
    pass


def _fallback_response(error_kind: str, system_hint: str) -> str:
    """Kontekstowy komunikat zastępczy po polsku gdy oba API są niedostępne."""
    hint = system_hint.lower()
    if "dietet" in hint or "diet" in hint or "posiłk" in hint or "meal" in hint:
        return (
            "⚠️ Asystent AI jest chwilowo niedostępny.\n\n"
            "**Tymczasowe wskazówki dietetyczne (na podstawie Twojego profilu):**\n"
            "• Trzymaj się ustalonych celów kalorycznych i białkowych.\n"
            "• Postaw na produkty pełnoziarniste, chude białko i warzywa.\n"
            "• Pij co najmniej 2 l wody dziennie.\n"
            "• Spróbuj ponownie za kilka minut — spersonalizowany plan będzie dostępny."
        )
    if "trener" in hint or "workout" in hint or "trening" in hint or "ćwiczeni" in hint:
        return (
            "⚠️ Asystent AI jest chwilowo niedostępny.\n\n"
            "**Tymczasowe wskazówki treningowe:**\n"
            "• Skorzystaj z wygenerowanego planu tygodniowego dostępnego w zakładce 'Plan'.\n"
            "• Ogranicz intensywność o 10–15%, jeśli odczuwasz zmęczenie.\n"
            "• Pamiętaj o rozgrzewce (5–10 min) i rozciąganiu po treningu.\n"
            "• Spróbuj ponownie za kilka minut — szczegółowy plan wróci wkrótce."
        )
    if "analiz" in hint or "raport" in hint or "log" in hint:
        return (
            "⚠️ Asystent AI jest chwilowo niedostępny.\n\n"
            "**Wskazówka:** Twój dziennik został zapisany. Analiza będzie dostępna, "
            "gdy połączenie z AI zostanie przywrócone. Spróbuj ponownie za kilka minut."
        )
    if "tygodniow" in hint or "weekly" in hint or "podsumow" in hint:
        return (
            "⚠️ Asystent AI jest chwilowo niedostępny.\n\n"
            "**Wskazówka:** Sprawdź sekcję 'Postępy', aby zobaczyć wykresy wagi "
            "i wolumenu treningowego za ostatnie tygodnie. Podsumowanie AI będzie "
            "dostępne po przywróceniu połączenia."
        )
    if "przepis" in hint or "lodówk" in hint or "fridge" in hint or "chef" in hint:
        return (
            "⚠️ Asystent AI jest chwilowo niedostępny.\n\n"
            "**Szybki posiłek bez AI:** Połącz dostępne białko (kurczak, jajka, twaróg) "
            "z warzywami i źródłem węglowodanów (ryż, makaron, ziemniaki). "
            "Dopraw oliwą, czosnkiem i ulubionymi ziołami. Spróbuj ponownie wkrótce."
        )
    return (
        f"⚠️ Asystent AI jest chwilowo niedostępny ({error_kind}).\n\n"
        "Spróbuj ponownie za kilka minut. Jeśli problem się powtarza, "
        "sprawdź status serwisu lub skontaktuj się z pomocą techniczną."
    )


def _call_groq(system: str, user_msg: str, max_tokens: int) -> str:
    """
    Wywołuje Groq API (model llama-3.3-70b-versatile).
    Rzuca wyjątek przy każdym błędzie — caller decyduje o fallbacku.
    """
    if _groq_client is None:
        raise RuntimeError("Groq client nie jest zainicjalizowany (brak GROQ_API_KEY)")

    completion = _groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
    )
    return completion.choices[0].message.content


def _call_gemini(system: str, user_msg: str, max_tokens: int) -> str:
    """
    Wywołuje Google Gemini API (model gemini-2.5-flash).
    Rzuca wyjątek przy każdym błędzie — caller decyduje o fallbacku.

    Obsługiwane błędy:
      • google.api_core.exceptions.ResourceExhausted  → limit zapytań / quota
      • google.api_core.exceptions.PermissionDenied   → nieprawidłowy klucz
      • google.api_core.exceptions.GoogleAPIError     → ogólny błąd API
      • ValueError                                    → pusta/blokowana odpowiedź (safety filter)
    """
    if not _gemini_ready:
        raise RuntimeError("Gemini client nie jest zainicjalizowany (brak GEMINI_API_KEY)")

    try:
        from google.api_core import exceptions as _gapi_exc  # lazy — nie blokuje startu
    except ImportError:
        _gapi_exc = None  # type: ignore[assignment]

    try:
        generation_kwargs: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": 0.2,
        }
        if "json" in f"{system}\n{user_msg}".lower():
            generation_kwargs["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system,
        )
        response = model.generate_content(
            user_msg,
            generation_config=genai.GenerationConfig(**generation_kwargs),
        )

        # Gemini może zwrócić pustą odpowiedź gdy safety filter zablokuje treść
        if not response.text:
            raise ValueError("Gemini zwrócił pustą odpowiedź (safety filter lub brak treści)")

        return response.text

    except Exception as exc:
        # Przekaż z czytelną nazwą klasy błędu żeby ask_ai() mógł to zalogować
        exc_type = type(exc).__name__
        if _gapi_exc:
            if isinstance(exc, _gapi_exc.ResourceExhausted):
                raise RuntimeError(f"Gemini: limit zapytań (quota). {exc}") from exc
            if isinstance(exc, _gapi_exc.PermissionDenied):
                raise RuntimeError(f"Gemini: brak uprawnień (GEMINI_API_KEY?). {exc}") from exc
            if isinstance(exc, _gapi_exc.GoogleAPIError):
                raise RuntimeError(f"Gemini: błąd Google API ({exc_type}). {exc}") from exc
        raise  # pozostałe wyjątki (ValueError, RuntimeError) propaguj bez zmian


def ask_ai(system: str, user_msg: str, max_tokens: int = 800) -> str:
    """
    Główna funkcja AI z architekturą Groq → Gemini fallback.

    Sekwencja:
      1. Próbuje Groq (llama-3.3-70b-versatile) — szybki, darmowy tier.
      2. Jeśli Groq zwróci błąd (limit zapytań, brak klucza, błąd sieci)
         → automatycznie przechodzi na Gemini (gemini-2.5-flash).
      3. Jeśli oba zawiodą → zwraca _AIError z kontekstowym komunikatem PL.

    Callerzy wykrywający błąd AI:
        result = ask_ai(system, msg)
        if isinstance(result, _AIError):
            raise HTTPException(status_code=503, detail=str(result))
    """
    system_hint = system[:80]

    # ── Krok 1: Groq (primary) ────────────────────────────────────────────────
    if _groq_client is not None:
        try:
            text = _call_groq(system, user_msg, max_tokens)
            print("[FitAI] AI: odpowiedź z Groq OK")
            return text
        except _groq_module.RateLimitError as e:
            print(f"[FitAI] Groq: limit zapytań — przełączam na Gemini. ({e})")
        except _groq_module.AuthenticationError as e:
            print(f"[FitAI] Groq: błąd autoryzacji (GROQ_API_KEY?) — przełączam na Gemini. ({e})")
        except _groq_module.APIConnectionError as e:
            print(f"[FitAI] Groq: brak połączenia — przełączam na Gemini. ({e})")
        except _groq_module.APIStatusError as e:
            print(f"[FitAI] Groq: HTTP {e.status_code} — przełączam na Gemini. ({e})")
        except Exception as e:
            print(f"[FitAI] Groq: nieoczekiwany błąd ({type(e).__name__}: {e}) — przełączam na Gemini.")
    else:
        print("[FitAI] AI: Groq niedostępny (brak klucza) — próbuję Gemini.")

    # ── Krok 2: Gemini (fallback) ─────────────────────────────────────────────
    if _gemini_ready:
        try:
            text = _call_gemini(system, user_msg, max_tokens)
            print("[FitAI] AI: odpowiedź z Gemini (fallback) OK")
            return text
        except Exception as e:
            print(f"[FitAI] Gemini: błąd ({type(e).__name__}: {e}) — serwuję odpowiedź lokalną.")
    else:
        print("[FitAI] AI: Gemini niedostępny (brak klucza) — serwuję odpowiedź lokalną.")

    # ── Krok 3: Lokalny fallback ──────────────────────────────────────────────
    return _AIError(_fallback_response("oba dostawcy AI niedostępni", system_hint))


# Alias wsteczny — wszystkie istniejące wywołania ask_claude() działają bez zmian
ask_claude = ask_ai


# ── Algorytmiczne fallbacki gdy AI niedostępne ────────────────────────────────
def _fallback_recovery_tip(mood: Optional[float], energy: Optional[float]) -> str:
    """Statyczna rada regeneracyjna gdy AI jest niedostępne.
    Ton zgodny z RECOVERY_PROMPT w prompts.py — krótki, konkretny, max 2 zdania."""
    m = float(mood)   if mood   is not None else 5.0
    e = float(energy) if energy is not None else 5.0
    avg = (m + e) / 2
    if avg < 4:
        return "Twoje wskaźniki są niskie — dziś priorytet to regeneracja. Postaw na lekki stretching i sen minimum 8h."
    elif avg > 7:
        return "Świetny stan — to idealny moment na intensywny trening lub pobicie rekordu. Działaj!"
    else:
        return "Umiarkowany poziom energii — wykonaj zaplanowany trening, słuchaj ciała i nie forsuj nadmiernie."


def _fallback_drill_tip(accuracy_pct: int, rpe: int) -> str:
    """Statyczna rada treningowa gdy AI jest niedostępne.
    Ton zgodny z PROGRESSION_PROMPT w prompts.py — max 2 zdania, konkretna wskazówka techniczna lub intensywność."""
    if rpe < 5:
        return f"RPE {rpe}/10 — intensywność niska. Zwiększ tempo lub trudność ćwiczenia w kolejnej sesji."
    if rpe > 8:
        return f"RPE {rpe}/10 — bardzo intensywna sesja. Skup się na technice i zaplanuj jutro dzień regeneracyjny."
    if accuracy_pct < 40:
        return f"Skuteczność {accuracy_pct}% — zwolnij tempo i skup się na mechanice ruchu zamiast na liczbie powtórzeń."
    if accuracy_pct >= 80:
        return f"Skuteczność {accuracy_pct}% — doskonały wynik. Czas zwiększyć trudność: dodaj obciążenie lub skróć przerwę."
    return f"Skuteczność {accuracy_pct}% przy RPE {rpe}/10 — solidna praca. Konsekwencja to klucz do postępu."


# ─── DB helpers ───────────────────────────────────────────────────────────────

def _get_user_or_404(user_key: str, session: Session) -> UserDB:
    user = session.exec(select(UserDB).where(UserDB.user_key == user_key)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    return user


def _get_user_logs(user: UserDB, session: Session) -> list[DailyLogDB]:
    return list(session.exec(
        select(DailyLogDB).where(DailyLogDB.user_id == user.id).order_by(DailyLogDB.log_date)
    ).all())


def _upsert_user_from_profile(
    user_key: str,
    payload: dict,
    session: Session,
    *,
    identity_id: Optional[str] = None,
    email: Optional[str] = None,
) -> UserDB:
    user = session.exec(select(UserDB).where(UserDB.user_key == user_key)).first()
    if not user:
        user = UserDB(
            user_key=user_key,
            name=payload.get("name", ""),
            age=payload.get("age", 0),
            height=payload.get("height", 0),
            weight=payload.get("weight", 0),
            start_weight=payload.get("weight", 0),
            target_weight=payload.get("target_weight", 0),
            goal=payload.get("goal", ""),
            frequency=payload.get("frequency", ""),
            diet=payload.get("diet", ""),
        )
        session.add(user)

    for field in ["name", "age", "height", "weight", "target_weight", "gender", "goal",
                  "frequency", "diet", "allergies", "meals_per_day", "notes"]:
        if field in payload:
            setattr(user, field, payload[field])

    if identity_id:
        user.identity_id = identity_id
    if email:
        user.email = email
    if not user.start_weight:
        user.start_weight = user.weight

    for list_field, key in [
        ("sports_json", "sports"), ("training_focus_json", "training_focus"),
        ("improvement_areas_json", "improvement_areas"), ("preferred_foods_json", "preferred_foods"),
        ("avoid_foods_json", "avoid_foods"), ("available_equipment_json", "available_equipment"),
        ("avoid_exercises_json", "avoid_exercises"),
    ]:
        if key in payload:
            user.set_list(list_field, payload[key])

    # Sport module fields (optional – passed only from sport-config endpoint)
    if "sport_focus" in payload:
        user.sport_focus = payload["sport_focus"] or None
    if "sport_specialization" in payload:
        user.sport_specialization = payload["sport_specialization"] or None
    if "sport_training_days" in payload:
        user.set_list("sport_training_days_json", payload["sport_training_days"])

    user.calories_target = calc_calories(user)
    user.protein_target = calc_protein(user)
    user.updated_at = datetime.now().isoformat()
    session.commit()
    session.refresh(user)
    return user


# ─── Auth endpoints ──────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse, tags=["auth"])
def auth_register(payload: RegisterRequest):
    """
    Rejestracja nowego użytkownika z hasłem.
    Zwraca JWT gotowy do użycia w nagłówku Authorization: Bearer <token>.
    """
    with Session(engine) as session:
        # Sprawdź unikalność e-maila
        existing = session.exec(
            select(UserDB).where(UserDB.email == payload.email.lower().strip())
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Konto z tym e-mailem już istnieje",
            )

        user = UserDB(
            user_key=f"native:{payload.email.lower().strip()}",
            email=payload.email.lower().strip(),
            hashed_password=_hash_password(payload.password),
            name=payload.name,
            age=payload.age,
            height=payload.height,
            weight=payload.weight,
            start_weight=payload.weight,
            target_weight=payload.target_weight,
            gender=payload.gender,
            goal=payload.goal,
            frequency=payload.frequency,
            diet=payload.diet,
            is_active=True,
        )
        user.calories_target = calc_calories(user)
        user.protein_target  = calc_protein(user)
        session.add(user)
        try:
            session.commit()
            session.refresh(user)
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Konto z tym e-mailem już istnieje (race condition)",
            )
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Błąd bazy danych podczas rejestracji: {exc}",
            )

        token = _create_access_token(user.id, user.email, user.role)
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            name=user.name,
            role=user.role,
            plan=user.plan,
        )


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def auth_login(payload: LoginRequest):
    """
    Logowanie email + hasło. Zwraca JWT.
    Endpoint publiczny — nie wymaga tokena.
    """
    with Session(engine) as session:
        user = session.exec(
            select(UserDB).where(UserDB.email == payload.email.lower().strip())
        ).first()

        # Celowo jednolity komunikat błędu — nie ujawniamy czy email istnieje
        _INVALID = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if not user:
            raise _INVALID
        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="To konto używa logowania zewnętrznego (Netlify Identity). "
                       "Użyj oryginalnego dostawcy.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Konto zostało zablokowane. Skontaktuj się z pomocą techniczną.",
            )
        if not _verify_password(payload.password, user.hashed_password):
            raise _INVALID

        token = _create_access_token(user.id, user.email, user.role)
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            name=user.name,
            role=user.role,
            plan=user.plan,
        )


@app.get("/auth/me", tags=["auth"])
def auth_me(user: UserDB = Depends(get_current_user)):
    """Zwraca profil aktualnie zalogowanego użytkownika."""
    return user.to_profile_dict()


@app.post("/auth/change-password", tags=["auth"])
def auth_change_password(
    payload: ChangePasswordRequest,
    user: UserDB = Depends(get_current_user),
):
    """Zmiana hasła — wymaga podania aktualnego hasła."""
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto zewnętrzne — zmień hasło u dostawcy identity.",
        )
    if not _verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Aktualne hasło jest nieprawidłowe",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nowe hasło musi mieć co najmniej 8 znaków",
        )
    with Session(engine) as session:
        db_user = session.get(UserDB, user.id)
        db_user.hashed_password = _hash_password(payload.new_password)
        db_user.updated_at = datetime.now().isoformat()
        session.commit()
    return {"status": "ok", "message": "Hasło zostało zmienione"}


@app.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
def auth_refresh(user: UserDB = Depends(get_current_user)):
    """
    Odświeżenie tokena — klient wysyła stary (wciąż ważny) token,
    dostaje nowy z przesuniętym `exp`. Bezpieczne zastępstwo refresh tokenów
    dla aplikacji SPA bez backendu sesji.
    """
    token = _create_access_token(user.id, user.email, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        role=user.role,
        plan=user.plan,
    )


# ─── /users/ endpoints (legacy + Discord bot compat) ─────────────────────────

@app.post("/users/{user_id}")
def create_or_update_user(user_id: str, profile: UserProfile):
    with Session(engine) as session:
        user = _upsert_user_from_profile(user_id, profile.model_dump(), session)
        return {"status": "ok", "user_id": user_id, "calories_target": user.calories_target}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    with Session(engine) as session:
        user = _get_user_or_404(user_id, session)
        return user.to_profile_dict()


@app.post("/users/{user_id}/logs")
def add_log(user_id: str, log: DailyLog):
    with Session(engine) as session:
        user = _get_user_or_404(user_id, session)
        today = date.today().isoformat()
        existing = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .where(DailyLogDB.log_date == today)
        ).first()
        if existing:
            # ── Upsert (legacy endpoint) ──────────────────────────────────────
            if log.food:    existing.food    = log.food
            if log.workout: existing.workout = log.workout
            if log.mood:    existing.mood    = log.mood
            if log.weight is not None: existing.weight = log.weight
            existing.logged_at = datetime.now().isoformat()
            entry = existing
        else:
            entry = DailyLogDB(
                user_id=user.id, log_date=today,
                food=log.food, workout=log.workout, mood=log.mood, weight=log.weight,
            )
        session.add(entry)
        if log.weight is not None:
            user.weight = log.weight
            user.calories_target = calc_calories(user)
            user.protein_target = calc_protein(user)
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "log": entry.to_dict()}


@app.get("/users/{user_id}/logs")
def get_logs(user_id: str, limit: int = 30):
    with Session(engine) as session:
        user = _get_user_or_404(user_id, session)
        logs = list(session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .order_by(DailyLogDB.log_date.desc())
        ).all())
        return {"logs": [l.to_dict() for l in logs[:limit]]}


# ─── Exercise Results & Progression endpoints ─────────────────────────────────

@app.post("/app/exercise-result", tags=["exercise"])
def log_exercise_result(payload: ExerciseResultRequest, user: UserDB = Depends(get_current_user)):
    """
    Rejestruje wynik ćwiczenia z oceną RPE.
    Na podstawie historii RPE sugeruje progresję na kolejną sesję.
    """
    with Session(engine) as session:
        session_date = payload.session_date or date.today().isoformat()
        result = ExerciseResultDB(
            user_id=user.id,
            exercise_name=payload.exercise_name,
            session_date=session_date,
            sets=payload.sets,
            reps=payload.reps,
            weight_kg=payload.weight_kg,
            rpe=payload.rpe,
            notes=payload.notes,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        # Wylicz sugestię progresji na podstawie ostatnich sesji
        history = list(session.exec(
            select(ExerciseResultDB)
            .where(ExerciseResultDB.user_id == user.id)
            .where(ExerciseResultDB.exercise_name == payload.exercise_name)
            .order_by(ExerciseResultDB.session_date.desc())
        ).all())
        progression = _suggest_progression(payload.exercise_name, history)

        return {
            "status": "ok",
            "result": result.to_dict(),
            "progression": progression,
        }


@app.get("/app/exercise-history", tags=["exercise"])
def get_exercise_history(exercise_name: Optional[str] = None, limit: int = 20, user: UserDB = Depends(get_current_user)):
    """Zwraca historię wyników ćwiczeń z sugestią progresji."""
    with Session(engine) as session:
        query = select(ExerciseResultDB).where(ExerciseResultDB.user_id == user.id)
        if exercise_name:
            query = query.where(ExerciseResultDB.exercise_name == exercise_name)
        results = list(session.exec(query.order_by(ExerciseResultDB.session_date.desc())).all())[:limit]

        data = [r.to_dict() for r in results]
        progression = None
        if exercise_name and results:
            progression = _suggest_progression(exercise_name, results)

        return {"results": data, "progression": progression}


@app.get("/app/progression-summary", tags=["exercise"])
def get_progression_summary(user: UserDB = Depends(get_current_user)):
    """Zwraca podsumowanie progresji dla wszystkich ćwiczeń użytkownika."""
    with Session(engine) as session:
        # Pobierz unikalne nazwy ćwiczeń
        all_results = list(session.exec(
            select(ExerciseResultDB)
            .where(ExerciseResultDB.user_id == user.id)
            .order_by(ExerciseResultDB.session_date.desc())
        ).all())

        by_exercise: dict[str, list[ExerciseResultDB]] = {}
        for r in all_results:
            by_exercise.setdefault(r.exercise_name, []).append(r)

        summary = []
        for name, hist in by_exercise.items():
            prog = _suggest_progression(name, hist)
            summary.append({
                "exercise_name": name,
                "total_sessions": len(hist),
                "last_session": hist[0].to_dict(),
                "progression": prog,
            })

        return {"exercises": summary, "total_exercises_tracked": len(summary)}


# ─── /app/ endpoints ──────────────────────────────────────────────────────────

@app.post("/app/onboarding")
def app_onboarding(payload: AppOnboardingRequest):
    user_key = _web_user_key(payload.identity_id)
    with Session(engine) as session:
        user = _upsert_user_from_profile(
            user_key,
            payload.model_dump(),
            session,
            identity_id=payload.identity_id,
            email=payload.email,
        )
        return {
            "status": "ok",
            "user_id": user_key,
            "plan": user.plan,
            "role": user.role,
        }


@app.get("/app/profile", tags=["profile"])
def app_get_profile(user: UserDB = Depends(get_current_user)):
    return user.to_profile_dict()


@app.get("/app/dashboard", tags=["profile"])
def app_dashboard(user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        logs = _get_user_logs(user, session)
        return _build_dashboard(user, logs)


@app.post("/app/checkin", tags=["checkin"])
def app_daily_checkin(log: AppDailyCheckinRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        today = date.today().isoformat()
        existing = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .where(DailyLogDB.log_date == today)
        ).first()

        if existing:
            # ── UPSERT: nadpisz istniejący wpis zamiast delete+insert ────────
            # Zachowujemy stary id i water_liters (inkrementowane oddzielnie)
            if log.food:         existing.food         = log.food
            if log.workout:      existing.workout      = log.workout
            if log.mood:         existing.mood         = log.mood
            if log.weight is not None:  existing.weight = log.weight
            sq = getattr(log, "sleep_quality", None)
            el = getattr(log, "energy_level", None)
            sl = getattr(log, "stress_level", None)
            wl = getattr(log, "water_liters", None)
            wc = getattr(log, "waist_cm", None)
            cc = getattr(log, "chest_cm", None)
            pp = getattr(log, "photo_path", None)
            if sq is not None: existing.sleep_quality  = sq
            if el is not None: existing.energy_level   = el
            if sl is not None: existing.stress_level   = sl
            if wl is not None: existing.water_liters   = wl   # nadpisz (tracker wysyła pełną wartość)
            if wc is not None: existing.waist_cm       = wc
            if cc is not None: existing.chest_cm       = cc
            if pp is not None: existing.photo_path     = pp
            if hasattr(log, "eaten_meals") and log.eaten_meals:
                existing.set_eaten_meals(log.eaten_meals)
            existing.logged_at = datetime.now().isoformat()
            entry = existing
        else:
            # ── Nowy wpis ─────────────────────────────────────────────────────
            entry = DailyLogDB(
                user_id=user.id, log_date=today,
                food=log.food, workout=log.workout, mood=log.mood, weight=log.weight,
                sleep_quality=getattr(log, "sleep_quality", None),
                energy_level=getattr(log, "energy_level", None),
                stress_level=getattr(log, "stress_level", None),
                water_liters=getattr(log, "water_liters", None),
                waist_cm=getattr(log, "waist_cm", None),
                chest_cm=getattr(log, "chest_cm", None),
                photo_path=getattr(log, "photo_path", None),
            )
            if hasattr(log, "eaten_meals") and log.eaten_meals:
                entry.set_eaten_meals(log.eaten_meals)
        session.add(entry)

        # ── XP awards ────────────────────────────────────────────────────────
        xp_earned = _XP_CHECKIN
        # XP za wodę — 5 XP gdy zalogowano ≥ 500 ml (zgodnie z nowym systemem)
        wl_val = getattr(log, "water_liters", None) or 0
        if wl_val >= 0.5:
            xp_earned += _XP_WATER_LOGGED
        if log.weight is not None:
            xp_earned += _XP_WEIGHT_LOGGED
            # Aktualizuj last_weight_change
            prev_log = session.exec(
                select(DailyLogDB)
                .where(DailyLogDB.user_id == user.id)
                .where(DailyLogDB.log_date < today)
                .where(DailyLogDB.weight != None)
                .order_by(DailyLogDB.log_date.desc())
            ).first()
            if prev_log and prev_log.weight:
                user.last_weight_change = round(log.weight - prev_log.weight, 2)
            user.weight = log.weight
            user.calories_target = calc_calories(user)
            user.protein_target = calc_protein(user)
        if log.workout:
            xp_earned += _XP_WORKOUT_LOGGED
        eaten = getattr(log, "eaten_meals", []) or []
        if eaten:
            xp_earned += min(len(eaten) * _XP_MEAL_LOGGED, 25)

        user.total_xp = (user.total_xp or 0) + xp_earned
        logs = list(session.exec(select(DailyLogDB).where(DailyLogDB.user_id == user.id)).all())
        logs.append(entry)
        user.streak_days = _compute_streak_days_from_logs(logs)
        if user.streak_days > 1:
            streak_bonus = min(user.streak_days * _XP_STREAK_BONUS, 100)
            user.total_xp += streak_bonus
            xp_earned += streak_bonus
        user.updated_at = datetime.now().isoformat()
        session.commit()
        water_ml_today = round((entry.water_liters or 0) * 1000)

        # ── Recovery / autoregulation AI tip (RECOVERY_PROMPT) ───────────────
        # Triggered when the checkin includes numeric mood_score or energy_score.
        # Falls back gracefully — never blocks the checkin response.
        ai_recovery_tip: Optional[str] = None
        _mood_num   = getattr(log, "mood_score",  None)
        _energy_num = getattr(log, "energy_score", None)
        _soreness   = getattr(log, "soreness",     None)
        # ── Recovery AI tip — używamy _get_prompt() dla bezpiecznego renderowania ─
        if _mood_num is not None or _energy_num is not None:
            try:
                _recovery_user_msg = _get_prompt(
                    RECOVERY_PROMPT, _RECOVERY_PROMPT_FB,
                    mood=_mood_num,
                    energy=_energy_num,
                    soreness=_soreness,
                )
                _recovery_system = (
                    "Jesteś Systemem Autoregulacji FitAI. Odpowiadaj po polsku. "
                    "Bądź krótki (max 2 zdania), konkretny i wspierający."
                )
                _recovery_raw = ask_ai(_recovery_system, _recovery_user_msg, max_tokens=150)
                if not isinstance(_recovery_raw, _AIError):
                    ai_recovery_tip = _recovery_raw.strip()
                else:
                    # Non-fatal: AI niedostępne, zwróć komunikat zastępczy
                    print(f"[AI ERROR] {datetime.now()}: Błąd w module [Checkin/RecoveryTip]: {_recovery_raw}")
                    ai_recovery_tip = _fallback_recovery_tip(_mood_num, _energy_num)
            except Exception as _exc:
                # Non-fatal — checkin zawsze wraca z wynikiem nawet bez porady AI
                print(f"[AI ERROR] {datetime.now()}: Błąd w module [Checkin/RecoveryTip]: {type(_exc).__name__}: {_exc}")
                ai_recovery_tip = _fallback_recovery_tip(_mood_num, _energy_num)

        return {
            "status": "ok",
            "log": entry.to_dict(),
            "streak_days": user.streak_days,
            "today_eaten": entry.get_eaten_meals() if hasattr(entry, "get_eaten_meals") else [],
            "xp_earned": xp_earned,
            "total_xp": user.total_xp,
            "level": _xp_to_level(user.total_xp),
            "xp_to_next_level": _xp_to_next_level(user.total_xp),
            "water_ml_today": water_ml_today,
            "ai_recovery_tip": ai_recovery_tip,   # None when not sent or AI unavailable
        }


@app.post("/app/water", tags=["checkin"])
def app_log_water(body: dict, user: UserDB = Depends(get_current_user)):
    """
    POST /app/water/{identity_id}
    Body: { "ml": 250 }

    Inkrementuje spożycie wody w DailyLogDB dla bieżącego dnia.
    Zwraca aktualny stan (water_liters) po dodaniu.
    """
    ml = int(body.get("ml", 0))
    if ml <= 0:
        raise HTTPException(status_code=400, detail="Ilość wody musi być większa niż 0 ml.")
    if ml > 5000:
        raise HTTPException(status_code=400, detail="Maksymalna jednorazowa porcja to 5000 ml.")

    liters_to_add = round(ml / 1000, 4)

    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        today = date.today().isoformat()

        existing = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .where(DailyLogDB.log_date == today)
        ).first()

        prev_total = existing.water_liters if existing else 0
        if existing:
            existing.water_liters = round((existing.water_liters or 0) + liters_to_add, 4)
            session.add(existing)
            total_liters = existing.water_liters
        else:
            entry = DailyLogDB(
                user_id=user.id,
                log_date=today,
                water_liters=liters_to_add,
            )
            session.add(entry)
            total_liters = liters_to_add

        session.commit()

    # ── XP za wodę (5 XP za każde zalogowanie wody, max raz dziennie) ────────
    # Używamy prostego heurystiku: przyznaj XP jeśli to pierwsze dodanie (prev=0)
    xp_info = {}
    user_for_xp = None
    if prev_total == 0:  # pierwsze logowanie wody dziś
        with Session(engine) as xp_session:
            try:
                user_for_xp = _get_user_or_404(user_key, xp_session)
                user_for_xp.total_xp = (user_for_xp.total_xp or 0) + _XP_WATER_LOGGED
                xp_session.add(user_for_xp)
                xp_session.commit()
                xp_info = {"xp_earned": _XP_WATER_LOGGED, "total_xp": user_for_xp.total_xp}
            except Exception:
                pass

    return {
        "status": "ok",
        "added_ml": ml,
        "water_liters_today": total_liters,
        "water_ml_today": round(total_liters * 1000),
        **xp_info,
    }


@app.post("/app/link-discord")
def app_link_discord(payload: DiscordLinkRequest):
    user_key = _web_user_key(payload.identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        user.linked_discord_id = payload.discord_user_id
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "linked_discord_id": payload.discord_user_id}


@app.get("/app/reminders", tags=["reminders"])
def app_get_reminders(user: UserDB = Depends(get_current_user)):
    return user.get_dict("reminders_json")


@app.post("/app/reminders", tags=["reminders"])
def app_set_reminders(prefs: ReminderPrefsRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        user.set_dict("reminders_json", prefs.model_dump())
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "reminders": prefs.model_dump()}


@app.get("/app/reminders-due")
def app_reminders_due():
    today = date.today().isoformat()
    with Session(engine) as session:
        users = list(session.exec(select(UserDB).where(UserDB.user_key.startswith("web:"))).all())
        due = []
        for user in users:
            reminders = user.get_dict("reminders_json")
            if not reminders.get("email_enabled") and not reminders.get("discord_enabled"):
                continue
            has_today = session.exec(
                select(DailyLogDB)
                .where(DailyLogDB.user_id == user.id)
                .where(DailyLogDB.log_date == today)
            ).first()
            if has_today:
                continue
            due.append({
                "user_id": user.user_key,
                "email": user.email,
                "linked_discord_id": user.linked_discord_id,
                "reminders": reminders,
                "streak_days": user.streak_days,
            })
        return {"due": due, "count": len(due)}


@app.get("/app/plan", tags=["plan"])
def app_get_plan(user: UserDB = Depends(get_current_user)):
    if not user.weekly_plan_json:
        return {"days": [], "generated_at": None, "weekly_goal": None}
    return user.get_dict("weekly_plan_json")


@app.post("/app/plan/generate", tags=["plan"])
def app_generate_plan(payload: PlanGenerateRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        if not _is_profile_ready_for_plan(user):
            raise HTTPException(status_code=400, detail="Najpierw uzupełnij pełny onboarding")
        if payload.force or not user.weekly_plan_json:
            plan = _build_weekly_plan(user)
            user.set_dict("weekly_plan_json", plan)
            # Wzbogać plan o sugestie progresji
            for day in plan.get("days", []):
                exercises = day.get("workout", {}).get("exercises", [])
                if exercises:
                    day["workout"]["exercises"] = _enrich_exercises_with_progression(exercises, user, session)
            user.set_dict("weekly_plan_json", plan)
            user.updated_at = datetime.now().isoformat()
            session.commit()
        return {"status": "ok", "plan": user.get_dict("weekly_plan_json")}


@app.post("/app/plan/swap", tags=["plan"])
def app_swap_plan_item(payload: PlanSwapRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        if not user.weekly_plan_json:
            raise HTTPException(status_code=404, detail="Plan nie został jeszcze wygenerowany")
        plan = user.get_dict("weekly_plan_json")
        days = plan.get("days", [])
        if not (0 <= payload.day_index < len(days)):
            raise HTTPException(status_code=400, detail="Niepoprawny day_index")
        day = days[payload.day_index]
        section = (payload.section or "").strip().lower()

        if section == "meal":
            items = day.get("meals", [])
            if not (0 <= payload.item_index < len(items)):
                raise HTTPException(status_code=400, detail="Niepoprawny item_index dla meal")
            item = items[payload.item_index]
            alts = item.get("alternatives", [])
            if not (0 <= payload.alternative_index < len(alts)):
                raise HTTPException(status_code=400, detail="Niepoprawny alternative_index")
            current = {"name": item["name"], "kcal": item["kcal"]}
            selected = alts[payload.alternative_index]
            item.update({"name": selected["name"], "kcal": selected["kcal"]})
            item["alternatives"] = [a for i, a in enumerate(alts) if i != payload.alternative_index] + [current]

        elif section == "exercise":
            exercises = day.get("workout", {}).get("exercises", [])
            if not (0 <= payload.item_index < len(exercises)):
                raise HTTPException(status_code=400, detail="Niepoprawny item_index dla exercise")
            item = exercises[payload.item_index]
            alts = item.get("alternatives", [])
            if not (0 <= payload.alternative_index < len(alts)):
                raise HTTPException(status_code=400, detail="Niepoprawny alternative_index")
            current = {k: item.get(k) for k in ["name", "sets", "reps", "notes", "how_to"]}
            selected = alts[payload.alternative_index]
            item.update({k: selected.get(k) for k in ["name", "sets", "reps", "notes", "how_to"]})
            item["alternatives"] = [a for i, a in enumerate(alts) if i != payload.alternative_index] + [current]
        else:
            raise HTTPException(status_code=400, detail="section musi być meal albo exercise")

        user.set_dict("weekly_plan_json", plan)
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "plan": plan}


# ─── Sports Module endpoints ──────────────────────────────────────────────────

@app.post("/app/sport-config", tags=["sport"])
def set_sport_config(payload: SportConfigRequest, user: UserDB = Depends(get_current_user)):
    """Konfiguruje moduł sportowy: sport, specjalizacja i dni treningowe."""
    with Session(engine) as session:
        user.sport_focus = payload.sport_focus.strip() or None
        user.sport_specialization = payload.sport_specialization.strip() or None
        user.set_list("sport_training_days_json", payload.sport_training_days)
        user.weekly_plan_json = None  # Unieważnij stary plan – zostanie wygenerowany na nowo
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {
            "status": "ok",
            "sport_focus": user.sport_focus,
            "sport_specialization": user.sport_specialization,
            "sport_training_days": payload.sport_training_days,
        }


@app.get("/app/sport-suggest-day", tags=["sport"])
def sport_suggest_day(user: UserDB = Depends(get_current_user)):
    """
    GET /app/sport-suggest-day

    Analizuje tygodniowy plan użytkownika i zwraca sugestię:
    który z zarejestrowanych dni treningowych ma najmniejszą objętość
    (najmniej ćwiczeń/serii) i może przyjąć nowe drille sportowe.

    Odpowiedź:
        {
          "suggested_day": "Środa",
          "reason": "Najniższa objętość treningowa (2 ćwiczenia)",
          "day_volumes": {"Poniedziałek": 4, "Środa": 2, "Piątek": 3},
          "training_days": ["Poniedziałek", "Środa", "Piątek"]
        }
    """
    plan = user.get_dict("weekly_plan_json")
    sport_days = set(user.get_list("sport_training_days_json"))

    ALL_DAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

    # Oblicz objętość każdego dnia (liczba ćwiczeń × serie)
    day_volumes: dict[str, int] = {}
    if plan and "days" in plan:
        for day_entry in plan["days"]:
            day_name = day_entry.get("day", "")
            exercises = day_entry.get("workout", {}).get("exercises", [])
            # Objętość = suma serii; fallback: liczba ćwiczeń
            volume = 0
            for ex in exercises:
                sets_raw = ex.get("sets", "3")
                try:
                    volume += int(str(sets_raw).split()[0])
                except (ValueError, TypeError):
                    volume += 3  # zakładamy 3 serie
            day_volumes[day_name] = volume
    else:
        # Brak wygenerowanego planu — wszystkie dni mają volume=0
        for d in ALL_DAYS_PL:
            day_volumes[d] = 0

    # Kandydaci: dni treningowe użytkownika (nie dni sportowe, nie niedziela)
    training_days = user.get_list("sport_training_days_json")
    if not training_days:
        # Fallback: wszystkie dni poza niedzielą i dniami sportowymi
        training_days = [d for d in ALL_DAYS_PL if d not in sport_days and d != "Niedziela"]

    if not training_days:
        return {
            "suggested_day": None,
            "reason": "Brak skonfigurowanych dni treningowych. Ustaw trening w profilu sportowym.",
            "day_volumes": day_volumes,
            "training_days": [],
        }

    # Wybierz dzień z najmniejszą objętością
    best_day = min(training_days, key=lambda d: day_volumes.get(d, 0))
    best_volume = day_volumes.get(best_day, 0)
    ex_count = best_volume // 3 or best_volume  # przybliżona liczba ćwiczeń

    return {
        "suggested_day": best_day,
        "reason": f"Najniższa objętość treningowa ({ex_count} ćwiczeń) — idealny dzień na drille.",
        "day_volumes": {d: day_volumes.get(d, 0) for d in training_days},
        "training_days": training_days,
    }


@app.get("/app/training-load/{user_id}", tags=["plan"])
def get_training_load(user_id: str, user: UserDB = Depends(get_current_user)):
    """
    GET /app/training-load/{user_id}

    Oblicza tygodniowy Workload (obciążenie) dla każdego dnia z bieżącego planu.
    Workload = suma (serie × powtórzenia) dla każdego ćwiczenia w danym dniu.

    Odpowiedź:
        {
          "workload": {
            "Poniedziałek": {"sets": 12, "reps": 96, "workload": 288, "exercise_count": 4},
            "Środa":        {"sets": 9,  "reps": 72, "workload": 216, "exercise_count": 3},
            ...
          },
          "suggested_day": "Środa",
          "suggested_reason": "Najniższy Workload (216 pkt) — idealny dzień na nowe ćwiczenie.",
          "total_weekly_workload": 504
        }

    Parametr `user_id` jest ignorowany na rzecz tokena JWT (bezpieczeństwo).
    Endpoint wymaga autoryzacji Bearer.
    """
    ALL_DAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

    plan = user.get_dict("weekly_plan_json")
    workload: dict[str, dict] = {}

    if plan and "days" in plan:
        for day_entry in plan["days"]:
            day_name = day_entry.get("day", "")
            exercises = day_entry.get("workout", {}).get("exercises", [])
            day_sets = 0
            day_reps = 0
            for ex in exercises:
                # Parsuj serie — może być "3 serie" lub "3"
                sets_raw = str(ex.get("sets", "3")).split()[0]
                reps_raw = str(ex.get("reps", "10")).split()[0]
                try:
                    s = int(sets_raw)
                except ValueError:
                    s = 3
                try:
                    r = int(reps_raw)
                except ValueError:
                    r = 10
                day_sets += s
                day_reps += r
            workload[day_name] = {
                "sets": day_sets,
                "reps": day_reps,
                "workload": day_sets * day_reps,
                "exercise_count": len(exercises),
                "is_rest": day_entry.get("workout", {}).get("rest", False),
            }
    else:
        # Brak planu — wszystkie dni mają zerowy workload
        for d in ALL_DAYS_PL:
            workload[d] = {"sets": 0, "reps": 0, "workload": 0, "exercise_count": 0, "is_rest": False}

    # Uzupełnij brakujące dni (np. dni odpoczynku nieobecne w planie)
    for d in ALL_DAYS_PL:
        if d not in workload:
            workload[d] = {"sets": 0, "reps": 0, "workload": 0, "exercise_count": 0, "is_rest": False}

    # Wybierz najlepszy dzień (najmniejszy workload, nie dzień odpoczynku)
    active_days = {d: v for d, v in workload.items() if not v.get("is_rest", False)}
    if active_days:
        best_day = min(active_days, key=lambda d: active_days[d]["workload"])
        best_wl = active_days[best_day]["workload"]
        best_count = active_days[best_day]["exercise_count"]
        suggested_reason = (
            f"Najniższy Workload ({best_wl} pkt, {best_count} ćwiczeń) — "
            "idealny dzień na dodanie nowego ćwiczenia."
        )
    else:
        best_day = None
        suggested_reason = "Brak aktywnych dni treningowych w planie."

    total_workload = sum(v["workload"] for v in workload.values())

    return {
        "workload": workload,
        "suggested_day": best_day,
        "suggested_reason": suggested_reason,
        "total_weekly_workload": total_workload,
        "has_plan": bool(plan and "days" in plan),
    }


@app.post("/app/plan/regenerate-ai", tags=["plan"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def regenerate_plan_with_ai(request: Request, user: UserDB = Depends(get_current_user)):
    """
    POST /app/plan/regenerate-ai

    Wysyła obecny tygodniowy plan użytkownika do modelu LLM z prośbą
    o optymalne rozmieszczenie wszystkich ćwiczeń w tygodniu,
    tak aby uniknąć przetrenowania i zapewnić właściwą regenerację.

    Algorytm:
      1. Zbiera wszystkie ćwiczenia ze wszystkich dni z obecnego planu.
      2. Buduje prompt opisujący ćwiczenia, grupy mięśniowe i profil użytkownika.
      3. Prosi LLM o optymalną dystrybucję między dniami (JSON).
      4. Aplikuje zwrócony rozkład do planu — zachowując oryginalne obiekty ćwiczeń.
      5. Zapisuje zaktualizowany plan do bazy.

    Zwraca:
        {"status": "ok", "plan": <zaktualizowany plan>, "ai_note": "<komentarz AI>"}
    """
    if not user.weekly_plan_json:
        raise HTTPException(status_code=404, detail="Brak planu do zregenerowania. Najpierw wygeneruj plan.")

    plan = user.get_dict("weekly_plan_json")
    days = plan.get("days", [])

    ALL_DAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

    # ── 1. Zbierz wszystkie ćwiczenia z całego planu ─────────────────────────
    all_exercises: list[dict] = []
    for day_entry in days:
        for ex in day_entry.get("workout", {}).get("exercises", []):
            muscles = ex.get("muscles", ex.get("muscle_group", "ogólne"))
            all_exercises.append({
                "name": ex.get("name", "Ćwiczenie"),
                "sets": ex.get("sets", 3),
                "reps": ex.get("reps", 10),
                "muscles": muscles,
                "_original": ex,  # zachowaj pełny obiekt do późniejszego mapowania
            })

    if not all_exercises:
        raise HTTPException(status_code=400, detail="Plan nie zawiera żadnych ćwiczeń do reorganizacji.")

    # ── 2. Buduj prompt ────────────────────────────────────────────────────────
    exercise_list_str = "\n".join(
        f"- {e['name']} ({e['sets']} serie × {e['reps']} powt., mięśnie: {e['muscles']})"
        for e in all_exercises
    )

    goal = user.goal or "ogólna sprawność"
    frequency = user.frequency or "3-4 razy w tygodniu"
    injuries = user.injuries or "brak"
    sport_focus = user.sport_focus or "brak"
    training_days_raw = user.get_list("sport_training_days_json")
    training_days_str = ", ".join(training_days_raw) if training_days_raw else "dowolne"

    system_prompt = (
        "Jesteś ekspertem planowania treningów. Twoim zadaniem jest optymalne "
        "rozmieszczenie zestawu ćwiczeń na dni tygodnia, aby unikać przetrenowania "
        "tych samych grup mięśniowych w kolejnych dniach i zapewnić właściwą regenerację. "
        "Odpowiadaj WYŁĄCZNIE w formacie JSON, bez żadnego tekstu poza JSON."
    )

    user_msg = f"""Profil użytkownika:
- Cel: {goal}
- Częstotliwość: {frequency}
- Sport: {sport_focus}
- Preferowane dni treningowe: {training_days_str}
- Kontuzje/ograniczenia: {injuries}

Ćwiczenia do rozmieszczenia ({len(all_exercises)} łącznie):
{exercise_list_str}

Dostępne dni tygodnia: {', '.join(ALL_DAYS_PL)}

Zadanie: Przypisz każde ćwiczenie do optymalnego dnia tygodnia. Zasady:
1. Nie trenuj tej samej grupy mięśni w 2 kolejnych dniach.
2. Zostaw przynajmniej 1 dzień odpoczynku w tygodniu (Niedziela lub Sobota).
3. Jeśli są preferowane dni treningowe, priorytetyzuj je.
4. Zbalansuj obciążenie — unikaj przeładowania jednego dnia.
5. Ćwiczenia sportowe (_sport: true) umieszczaj w preferowanych dniach sportowych.

Odpowiedź MUSI być w tym dokładnym formacie JSON (bez żadnego tekstu poza JSON):
{{
  "schedule": {{
    "Poniedziałek": ["NazwaĆwiczenia1", "NazwaĆwiczenia2"],
    "Wtorek": [],
    "Środa": ["NazwaĆwiczenia3"],
    "Czwartek": [],
    "Piątek": ["NazwaĆwiczenia4", "NazwaĆwiczenia5"],
    "Sobota": [],
    "Niedziela": []
  }},
  "ai_note": "Krótkie (1-2 zdania) wyjaśnienie strategii podziału."
}}"""

    ai_result = ask_ai(system_prompt, user_msg, max_tokens=1000)
    if isinstance(ai_result, _AIError):
        raise HTTPException(status_code=503, detail=str(ai_result))

    # ── 3. Parsuj odpowiedź JSON ───────────────────────────────────────────────
    try:
        # Wyczyść ewentualne backticks z odpowiedzi
        clean = ai_result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        ai_data = json.loads(clean.strip())
        schedule: dict[str, list[str]] = ai_data.get("schedule", {})
        ai_note: str = ai_data.get("ai_note", "Plan zoptymalizowany przez AI.")
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI zwróciło niepoprawny JSON: {exc}. Spróbuj ponownie."
        )

    # ── 4. Aplikuj nowy rozkład — mapuj nazwy → oryginalne obiekty ćwiczeń ───
    exercise_by_name: dict[str, dict] = {e["name"]: e["_original"] for e in all_exercises}

    # Buduj nowe dni na podstawie harmonogramu AI
    new_days: list[dict] = []
    for day_name in ALL_DAYS_PL:
        ex_names_for_day = schedule.get(day_name, [])
        exercises_for_day = [
            exercise_by_name[n] for n in ex_names_for_day if n in exercise_by_name
        ]

        # Znajdź oryginalne dane dnia (meals, itp.) lub utwórz pusty szablon
        original_day = next((d for d in days if d.get("day") == day_name), None)
        if original_day:
            new_day = dict(original_day)
            new_day["workout"] = dict(original_day.get("workout", {}))
            new_day["workout"]["exercises"] = exercises_for_day
            new_day["workout"]["rest"] = len(exercises_for_day) == 0
        else:
            new_day = {
                "day": day_name,
                "workout": {
                    "exercises": exercises_for_day,
                    "rest": len(exercises_for_day) == 0,
                },
                "meals": [],
            }
        new_days.append(new_day)

    # ── 5. Zapisz zaktualizowany plan ─────────────────────────────────────────
    plan["days"] = new_days
    plan["ai_regenerated_at"] = datetime.now().isoformat()
    plan["ai_note"] = ai_note

    with Session(engine) as session:
        db_user = session.get(UserDB, user.id)
        if db_user:
            db_user.set_dict("weekly_plan_json", plan)
            db_user.updated_at = datetime.now().isoformat()
            session.commit()

    return {
        "status": "ok",
        "plan": plan,
        "ai_note": ai_note,
        "exercises_redistributed": len(all_exercises),
    }


@app.get("/app/sport-drills", tags=["sport"])
def list_sport_drills(sport: str = "koszykówka", specialization: str = ""):
    """Zwraca dostępne drille dla danego sportu i specjalizacji."""
    sport_lower = sport.lower().strip()
    if sport_lower not in SPORT_DRILLS_DB:
        raise HTTPException(status_code=404, detail=f"Brak drilli dla sportu: {sport}")
    spec_map = SPORT_DRILLS_DB[sport_lower]
    if specialization:
        spec_lower = specialization.lower().strip()
        drills = spec_map.get(spec_lower)
        if drills is None:
            raise HTTPException(status_code=404, detail=f"Brak specjalizacji: {specialization}")
        return {"sport": sport, "specialization": specialization, "drills": drills}
    return {"sport": sport, "specializations": list(spec_map.keys()), "all_drills": spec_map}


@app.post("/app/drill-result", tags=["sport"])
def log_drill_result(payload: DrillResultRequest, user: UserDB = Depends(get_current_user)):
    """Zapisuje wynik drilla sportowego i zwraca sugestię progresji.
    
    Obsługuje dwa typy drilli:
    - Rzuty (success_count + total_attempts)
    - Bieg/Sprint (time_seconds + distance_meters)
    """
    session_date = payload.session_date or date.today().isoformat()

    with Session(engine) as session:

        # ── UPSERT: jeden rekord per (user, drill, dzień) ──────────────────────
        existing_dr = session.exec(
            select(DrillResultDB)
            .where(DrillResultDB.user_id == user.id)
            .where(DrillResultDB.drill_name == payload.drill_name)
            .where(DrillResultDB.session_date == session_date)
        ).first()

        if existing_dr:
            # Aktualizacja istniejącego rekordu drilla
            if payload.success_count    is not None: existing_dr.success_count    = payload.success_count
            if payload.total_attempts   is not None: existing_dr.total_attempts   = payload.total_attempts
            if payload.rpe              is not None: existing_dr.rpe              = payload.rpe
            if payload.notes            is not None: existing_dr.notes            = payload.notes
            if payload.time_seconds     is not None: existing_dr.time_seconds     = payload.time_seconds
            if payload.distance_meters  is not None: existing_dr.distance_meters  = payload.distance_meters
            if payload.duration_seconds is not None: existing_dr.duration_seconds = payload.duration_seconds
            if payload.weight_kg        is not None: existing_dr.weight_kg        = payload.weight_kg
            result = existing_dr
        else:
            result = DrillResultDB(
                user_id=user.id,
                drill_name=payload.drill_name,
                session_date=session_date,
                success_count=payload.success_count,
                total_attempts=payload.total_attempts,
                rpe=payload.rpe,
                notes=payload.notes,
                time_seconds=payload.time_seconds,
                distance_meters=payload.distance_meters,
                duration_seconds=payload.duration_seconds,
                weight_kg=payload.weight_kg,
            )
        session.add(result)
        session.commit()
        session.refresh(result)

        # Pobierz historię dla tej nazwy drilla i oblicz progresję
        history = list(session.exec(
            select(DrillResultDB)
            .where(DrillResultDB.user_id == user.id)
            .where(DrillResultDB.drill_name == payload.drill_name)
            .order_by(DrillResultDB.session_date.desc())
        ).all())

        progression = _suggest_drill_progression(payload.drill_name, history)

        # ── AI coaching tip via PROGRESSION_PROMPT ──────────────────────────
        # Personalizowana rada po zapisie wyniku drilla.
        # Używamy _get_prompt() z fallbackiem gdy prompts.py niedostępny.
        # Błąd AI nie blokuje odpowiedzi — progression algorytmiczny zawsze wraca.
        ai_coaching_tip: Optional[str] = None
        if history:
            last_h = history[0]
            _successes   = last_h.success_count  or 0
            _total_atts  = last_h.total_attempts or max(1, _successes)
            _rpe_val     = last_h.rpe            or payload.rpe or 5
            # Fix 1: jawny fallback 'brak' — nie wysyłaj pustego stringa do AI
            _notes_val   = (payload.notes or "").strip() or "brak"
            try:
                _prog_user_msg = _get_prompt(
                    PROGRESSION_PROMPT, _PROGRESSION_PROMPT_FB,
                    exercise_name=payload.drill_name,
                    successes=_successes,
                    total_attempts=_total_atts,
                    rpe=_rpe_val,
                    user_notes=_notes_val,
                )
                _prog_system = (
                    "Jesteś Trenerem Przygotowania Fizycznego FitAI. "
                    "Odpowiadaj po polsku. Bądź konkretny, motywujący i zwięzły (max 2 zdania)."
                )
                _tip_raw = ask_ai(_prog_system, _prog_user_msg, max_tokens=200)
                if not isinstance(_tip_raw, _AIError):
                    ai_coaching_tip = _tip_raw.strip()
                else:
                    # Fallback algorytmiczny gdy AI niedostępne
                    print(f"[AI ERROR] {datetime.now()}: Błąd w module [DrillResult/CoachingTip]: {_tip_raw}")
                    _eff = round((_successes / _total_atts) * 100) if _total_atts > 0 else 0
                    ai_coaching_tip = _fallback_drill_tip(_eff, int(_rpe_val))
            except Exception as _exc:
                # Non-fatal — progression algorytmiczny zawsze zwracany
                print(f"[AI ERROR] {datetime.now()}: Błąd w module [DrillResult/CoachingTip]: {type(_exc).__name__}: {_exc}")
                _eff = round((_successes / _total_atts) * 100) if _total_atts > 0 else 0
                ai_coaching_tip = _fallback_drill_tip(_eff, int(payload.rpe or 5))

        return {
            "status": "ok",
            "result": result.to_dict(),
            "progression": progression,
            "ai_coaching_tip": ai_coaching_tip,   # None when AI unavailable
            "upserted": existing_dr is not None,
        }


@app.get("/app/drill-history", tags=["sport"])
def get_drill_history(drill_name: Optional[str] = None, limit: int = 20, user: UserDB = Depends(get_current_user)):
    """Pobiera historię wyników drilli dla użytkownika."""
    with Session(engine) as session:
        query = select(DrillResultDB).where(DrillResultDB.user_id == user.id)
        if drill_name:
            query = query.where(DrillResultDB.drill_name == drill_name)
        query = query.order_by(DrillResultDB.session_date.desc())
        results = list(session.exec(query).all())[:limit]

        # Dołącz progresję dla każdego unikalnego drilla
        by_name: dict[str, list] = {}
        for r in results:
            by_name.setdefault(r.drill_name, []).append(r)

        progressions = {
            name: _suggest_drill_progression(name, hist)
            for name, hist in by_name.items()
        }

        return {
            "results": [r.to_dict() for r in results],
            "progressions": progressions,
        }


# ─── Billing endpoints ────────────────────────────────────────────────────────

@app.post("/billing/plan", tags=["billing"])
def billing_set_plan(payload: PlanUpdateRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        plan = _normalize_plan(payload.plan)
        user.plan = plan
        user.role = _role_for_plan(plan)
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "plan": plan, "role": user.role}


@app.post("/billing/stripe/webhook", tags=["billing"])
async def stripe_webhook(request: Request):
    payload = await request.json()
    identity_id = payload.get("identity_id")
    if not identity_id:
        raise HTTPException(status_code=400, detail="Brak identity_id")
    plan = _normalize_plan(payload.get("plan", "free"))
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        user.plan = plan
        user.role = _role_for_plan(plan)
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "plan": plan, "role": user.role}


# ─── AI endpoints ─────────────────────────────────────────────────────────────

@app.post("/ai/diet", tags=["ai"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_diet_plan(request: Request, req: AIRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        kcal = user.calories_target or calc_calories(user)
        protein = user.protein_target or calc_protein(user)
        day_of_week = datetime.now().strftime("%A")

        # Wyznacz typ dnia i makro carb cycling
        focus = user.get_list("training_focus_json")
        day_type = _day_type(day_of_week, focus[0].lower() if focus else "klatka")
        macros = calc_daily_macros(kcal, day_type)

        system = (
            "Jesteś dietetykiem sportowym. Piszesz po polsku. "
            "Tworzysz konkretne, zróżnicowane i zdrowe plany posiłków z dokładną gramaturą."
        )
        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Typ dnia (carb cycling): {_day_type_label(day_type)}\n"
            f"Makroskładniki DZIŚ: {macros['kcal']} kcal, "
            f"białko {macros['protein_g']}g, węgle {macros['carbs_g']}g, tłuszcze {macros['fat_g']}g\n"
            f"Dzień: {day_of_week}\n"
            f"Dieta: {user.diet or 'brak'}, alergie: {user.allergies or 'brak'}\n"
            f"Posiłków dziennie: {user.meals_per_day}\n\n"
            f"Kontekst: {req.extra_context or 'brak'}\n\n"
            "Utwórz szczegółowy plan diety na DZIŚ z godzinami, pełnymi nazwami produktów, "
            "gramaturą i kaloriami każdego posiłku. Na końcu łączne makroskładniki."
        )
        try:
            _diet_result = ask_claude(system, user_msg, 1000)
            if isinstance(_diet_result, _AIError):
                raise HTTPException(
                    status_code=503,
                    detail=f"Serwis AI tymczasowo niedostępny: {_diet_result}"
                )
            return {
                "plan": _diet_result,
                "calories_target": kcal,
                "protein_target": protein,
                "macros": macros,
            }
        except HTTPException:
            raise
        except Exception as _exc:
            print(f"[AI ERROR] {datetime.now()}: Błąd w module [ai/diet]: {type(_exc).__name__}: {_exc}")
            # Fallback: zwróć makro bez planu tekstowego
            return {
                "plan": (
                    f"AI tymczasowo niedostępne. Twoje makro na dziś ({_day_type_label(day_type)}): "
                    f"{macros['kcal']} kcal | białko {macros['protein_g']}g | "
                    f"węgle {macros['carbs_g']}g | tłuszcze {macros['fat_g']}g."
                ),
                "calories_target": kcal,
                "protein_target": protein,
                "macros": macros,
                "fallback": True,
            }


@app.post("/ai/workout", tags=["ai"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_workout_plan(request: Request, req: AIRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        logs = list(session.exec(
            select(DailyLogDB).where(DailyLogDB.user_id == user.id).order_by(DailyLogDB.log_date.desc())
        ).all())[:7]
        recent_workouts = [l.workout for l in logs if l.workout]

        # Pobierz dane progresji dla AI
        progression_summary = []
        ex_results = list(session.exec(
            select(ExerciseResultDB)
            .where(ExerciseResultDB.user_id == user.id)
            .order_by(ExerciseResultDB.session_date.desc())
        ).all())[:30]
        by_name: dict[str, list] = {}
        for r in ex_results:
            by_name.setdefault(r.exercise_name, []).append(r)
        for name, hist in by_name.items():
            p = _suggest_progression(name, hist)
            progression_summary.append(f"{name}: sugerowany ciężar {p.get('suggested_weight_kg')} kg "
                                       f"x {p.get('suggested_reps')} powtórzeń ({p.get('reason')})")

        day = datetime.now().strftime("%A")
        system = (
            "Jesteś doświadczonym trenerem personalnym. Piszesz po polsku. "
            "Tworzysz efektywne i bezpieczne plany treningowe z progresją obciążenia."
        )
        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Dzień tygodnia: {day}\n"
            f"Ostatnie treningi (7 dni): {chr(10).join(recent_workouts) or 'brak danych'}\n"
            f"Historia progresji (RPE-based):\n{chr(10).join(progression_summary) or 'brak historii'}\n"
            f"Kontekst: {req.extra_context or 'brak'}\n\n"
            "Utwórz plan treningowy na DZIŚ — nazwa sesji, 5-6 ćwiczeń z seriami, "
            "powtórzeniami, konkretnym obciążeniem (uwzględnij sugestie progresji powyżej) "
            "i wskazówkami technicznymi. Unikaj partii zmęczonych z ostatnich dni.\n"
            f"Cel: {user.goal}, sporty: {', '.join(user.get_list('sports_json'))}"
        )
        try:
            _workout_result = ask_claude(system, user_msg, 900)
            if isinstance(_workout_result, _AIError):
                raise HTTPException(
                    status_code=503,
                    detail=f"Serwis AI tymczasowo niedostępny: {_workout_result}"
                )
            return {"plan": _workout_result}
        except HTTPException:
            raise
        except Exception as _exc:
            print(f"[AI ERROR] {datetime.now()}: Błąd w module [ai/workout]: {type(_exc).__name__}: {_exc}")
            return {
                "plan": (
                    "AI tymczasowo niedostępne. Wykonaj trening według ostatniego "
                    "zaplanowanego planu lub skonsultuj się z trenerem."
                ),
                "fallback": True,
            }


@app.post("/ai/analyze-log", tags=["ai"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_analyze_log(request: Request, req: AIRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        today = date.today().isoformat()
        today_log = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .where(DailyLogDB.log_date == today)
        ).first()
        if not today_log:
            raise HTTPException(status_code=400, detail="Brak raportu na dziś")
        kcal = user.calories_target or calc_calories(user)
        focus = user.get_list("training_focus_json")
        day_type = _day_type(datetime.now().strftime("%A"), focus[0].lower() if focus else "klatka")
        macros = calc_daily_macros(kcal, day_type)
        system = (
            "Jesteś osobistym asystentem fitness. Piszesz po polsku. "
            "Analizujesz raporty i tworzysz konkretne plany na kolejny dzień."
        )
        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Makro na dziś ({_day_type_label(day_type)}): {macros}\n\n"
            f"Raport z dziś:\n"
            f"- Co jadłem: {today_log.food or 'nie podano'}\n"
            f"- Trening: {today_log.workout or 'nie podano'}\n"
            f"- Samopoczucie: {today_log.mood or 'nie podano'}\n"
            f"- Waga: {today_log.weight or 'nie podano'} kg\n\n"
            "Oceń dzień i podaj KONKRETNY plan na jutro z makroskładnikami. Max 400 słów."
        )
        try:
            _log_result = ask_claude(system, user_msg, 1000)
            if isinstance(_log_result, _AIError):
                raise HTTPException(
                    status_code=503,
                    detail=f"Serwis AI tymczasowo niedostępny: {_log_result}"
                )
            return {"analysis": _log_result}
        except HTTPException:
            raise
        except Exception as _exc:
            print(f"[AI ERROR] {datetime.now()}: Błąd w module [ai/analyze-log]: {type(_exc).__name__}: {_exc}")
            return {
                "analysis": (
                    "AI tymczasowo niedostępne. Twój wpis z dziś został zapisany. "
                    "Sprawdź analizę jutro po przywróceniu serwisu."
                ),
                "fallback": True,
            }


@app.post("/ai/weekly", tags=["ai"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_weekly_summary(request: Request, req: AIRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        logs = list(session.exec(
            select(DailyLogDB).where(DailyLogDB.user_id == user.id).order_by(DailyLogDB.log_date.desc())
        ).all())[:7]
        _weekly_system = (
            "Jesteś Głównym Strategiem FitAI. Piszesz po polsku. "
            "Tworzysz motywujące ale realistyczne podsumowania tygodniowe "
            "oraz konkretne zalecenia na kolejny tydzień."
        )

        # ── Build user message from WEEKLY_PLAN_PROMPT (lub fallback) ─────────
        # _get_prompt() obsługuje: brak prompts.py, None-wartości, KeyError.
        # Po wygenerowaniu dołączamy dane logów jako kontekst empiryczny.
        _focus = user.get_list("training_focus_json")
        _day_type_now = _day_type(
            datetime.now().strftime("%A"),
            _focus[0].lower() if _focus else "klatka"
        )
        try:
            _user_msg = _get_prompt(
                WEEKLY_PLAN_PROMPT, _WEEKLY_PLAN_PROMPT_FB,
                age=user.age,
                weight=user.weight,
                goal=user.goal or "ogólna sprawność",
                sport_focus=user.sport_focus or "brak",
                level=_xp_to_level(user.total_xp),
                workout_days=user.frequency or "3-4",
                # Fix 4: czytelna etykieta zamiast technicznego klucza 'heavy'/'rest'
                day_type=_day_type_label(_day_type_now),
            )
        except Exception as _fmt_exc:
            print(f"[AI ERROR] {datetime.now()}: Błąd w module [WeeklySummary/PromptFormat]: {_fmt_exc}")
            _user_msg = f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}"

        # Dołącz logi tygodniowe — AI ma konkretne dane, nie tylko profil
        _log_summary = json.dumps(
            [l.to_dict() for l in logs], ensure_ascii=False
        )
        _user_msg += (
            f"\n\nLogi z ostatnich 7 dni:\n{_log_summary}"
            "\n\nPodaj tygodniowe podsumowanie: ocena tygodnia, postęp do celu, "
            "top 3 rekomendacje na kolejny tydzień (dieta + trening). Max 300 słów."
        )

        try:
            _weekly_result = ask_claude(_weekly_system, _user_msg, 800)
            if isinstance(_weekly_result, _AIError):
                print(f"[WeeklySummary] AI error: {_weekly_result}")
                raise HTTPException(status_code=503, detail=str(_weekly_result))
            return {"summary": _weekly_result}
        except HTTPException:
            raise
        except Exception as _exc:
            print(f"[AI ERROR] {datetime.now()}: Błąd w module [ai/weekly]: {type(_exc).__name__}: {_exc}")
            # Fallback: statyczne podsumowanie z danych logów
            _n_logs = len(logs)
            _workouts_done = sum(1 for l in logs if l.workout)
            return {
                "summary": (
                    f"AI tymczasowo niedostępne. Statystyki tygodnia: "
                    f"{_n_logs} wpisów w dzienniku, {_workouts_done} treningów. "
                    "Sprawdź pełną analizę gdy serwis AI wróci online."
                ),
                "fallback": True,
            }


# ─── XP / Injuries endpoints ─────────────────────────────────────────────────

class InjuryUpdateRequest(BaseModel):
    injuries: list[str] = []   # lista kontuzji, np. ["kolano lewe", "bark prawy"]


@app.get("/app/xp", tags=["gamification"])
def app_get_xp(user: UserDB = Depends(get_current_user)):
    """Zwraca poziom XP, level i postęp do następnego poziomu."""
    return {
        "total_xp": user.total_xp,
        **_xp_to_next_level(user.total_xp),
        "injuries": [i.strip() for i in (user.injuries or "").split(",") if i.strip()],
    }


@app.post("/app/injuries", tags=["safety"])
def app_update_injuries(payload: InjuryUpdateRequest, user: UserDB = Depends(get_current_user)):
    """Aktualizuje listę kontuzji użytkownika."""
    with Session(engine) as session:
        user.injuries = ", ".join(i.strip() for i in payload.injuries if i.strip())
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {
            "status": "ok",
            "injuries": [i.strip() for i in user.injuries.split(",") if i.strip()],
        }


@app.get("/app/overload", tags=["safety"])
def app_check_overload(threshold_pct: float = 20.0, user: UserDB = Depends(get_current_user)):
    """
    Sprawdza przeciążenie treningowe: porównuje wolumen (sets×reps×weight)
    dwóch ostatnich sesji dla każdego ćwiczenia.
    threshold_pct: próg wzrostu wolumenu w % (domyślnie 20%).
    """
    with Session(engine) as session:
        return _check_overload(user.id, session, threshold_pct=threshold_pct / 100)


# ─── Fridge Chef & Meal Prep endpoints ───────────────────────────────────────

class FridgeChefRequest(BaseModel):
    identity_id: str
    ingredients: list[str]                  # np. ["kurczak 300g", "brokuły", "jajka"]
    extra_context: Optional[str] = None     # np. "jestem po treningu siłowym"
    strict_mode: bool = False               # True = używaj WYŁĄCZNIE podanych składników


class MealPrepRequest(BaseModel):
    days: int = 3                           # ile dni planu uwzględnić (1-7)
    extra_context: Optional[str] = None


# ── SYSTEM PROMPTS ─────────────────────────────────────────────────────────────

_FRIDGE_SYSTEM_BASE = """\
Jesteś kulinarnym asystentem sportowym. Piszesz WYŁĄCZNIE po polsku.
Zasady odpowiedzi:
1. Zwróć dokładnie 4 RÓŻNE dania.
2. Format każdego dania (zachowaj nagłówki, powtórz dla każdego z 4 dań):
   ## 🍳 [Nazwa potrawy]
   **Czas przygotowania:** X min
   **Makroskładniki (porcja):** Kcal: X | Białko: Xg | Węgle: Xg | Tłuszcze: Xg
   ### Składniki
   - [ilość] [produkt]
   ### Przygotowanie
   Numerowane kroki (max 6). Konkretne, bez lania wody.
   ### 💡 Wskazówka
   Jedno zdanie o modyfikacji pasującej do celu użytkownika.
3. Nie pytaj o nic. Nie dodawaj komentarzy poza formatem.
"""

_FRIDGE_SYSTEM_STRICT = """\
Jesteś kulinarnym asystentem sportowym. Piszesz WYŁĄCZNIE po polsku.
Zasady odpowiedzi:
1. Wygeneruj dokładnie 4 RÓŻNE dania używając WYŁĄCZNIE składników podanych przez użytkownika.
   Nie możesz użyć ŻADNEGO składnika spoza listy — nawet soli, oliwy czy przypraw, jeśli nie są na liście.
   Jeśli podanych składników jest za mało, by stworzyć 4 kompletne dania, zwróć TYLKO tekst: Error01
2. Jeśli możesz stworzyć 4 dania — format każdego (powtórz 4x):
   ## 🍳 [Nazwa potrawy]
   **Czas przygotowania:** X min
   **Makroskładniki (porcja):** Kcal: X | Białko: Xg | Węgle: Xg | Tłuszcze: Xg
   ### Składniki
   - [ilość] [produkt]  ← tylko z podanej listy
   ### Przygotowanie
   Numerowane kroki (max 6).
   ### 💡 Wskazówka
   Jedno zdanie.
3. Nie pytaj o nic. Nie używaj składników spoza listy pod żadnym pozorem.
"""

# Keep alias for backward compat
_FRIDGE_SYSTEM = _FRIDGE_SYSTEM_BASE

_MEAL_PREP_SYSTEM = """\
Jesteś ekspertem od meal-prep i optymalizacji żywieniowej dla sportowców. Piszesz WYŁĄCZNIE po polsku.
Zasady odpowiedzi:
1. Przeanalizuj plan posiłków na podane dni i wygeneruj:
   a) Zbiorczą listę zakupów z dokładnymi ilościami łącznymi (zsumowanymi na wszystkie dni).
   b) Harmonogram gotowania batch-cooking — co ugotować raz i podzielić na porcje.
   c) Kolejność przygotowań w niedzielę lub wieczór przed tygodniem.
2. Format odpowiedzi (zachowaj nagłówki):
   ## 🛒 Lista zakupów (na X dni)
   Pogrupuj: BIAŁKA | WARZYWA I OWOCE | WĘGLOWODANY | NABIAŁ I TŁUSZCZE | INNE
   Każda pozycja: "- [ilość łączna] [produkt]  → [ile porcji da]"
   ## ⏱️ Harmonogram gotowania (batch-cooking)
   Numerowane kroki — od najdłuższego gotowania do najkrótszego.
   Każdy krok: czas + ile porcji powstaje + jak przechowywać.
   ## 📦 Podział na pojemniki
   Tabela tekstowa: Dzień | Posiłek | Zawartość pojemnika | Kcal
   ## 💰 Szacowany koszt
   Podaj orientacyjny koszt całego meal-prep w PLN.
   ## ⚡ Top 3 pro-tipy
   Konkretne wskazówki oszczędzające czas lub poprawiające smak.
3. Nie pytaj o nic. Bądź precyzyjny w gramaturach.
"""


@app.post("/app/fridge-chef", tags=["ai_chef"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def app_fridge_chef(request: Request, req: FridgeChefRequest, user: UserDB = Depends(get_current_user)):
    """
    Na podstawie listy składników z lodówki generuje 1 optymalny przepis
    dopasowany do celu i limitu kalorycznego użytkownika.
    """
    print(f"[FridgeChef] Incoming request: {len(req.ingredients)} ingredients, strict_mode={req.strict_mode}")
    
    if not req.ingredients:
        print("[FridgeChef] ERROR: Empty ingredients list")
        raise HTTPException(status_code=422, detail="Lista składników nie może być pusta.")
    if len(req.ingredients) > 30:
        print(f"[FridgeChef] ERROR: Too many ingredients ({len(req.ingredients)} > 30)")
        raise HTTPException(status_code=422, detail="Maksymalnie 30 składników naraz.")

    try:
        with Session(engine) as session:

            kcal_target   = user.calories_target or calc_calories(user)
            protein_target = user.protein_target or calc_protein(user)
            avoid_foods   = user.get_list("avoid_foods_json")
            preferred     = user.get_list("preferred_foods_json")

            # Jeden posiłek ≈ 1/meals_per_day całodobowego limitu (±20%)
            meals_n    = max(user.meals_per_day, 1)
            meal_kcal  = int(kcal_target / meals_n)

            ingredients_str = ", ".join(req.ingredients)
            avoid_str       = ", ".join(avoid_foods) if avoid_foods else "brak"
            preferred_str   = ", ".join(preferred)   if preferred   else "brak"

            print(f"[FridgeChef] User: {user.name}, kcal_target: {kcal_target}, meal_kcal: {meal_kcal}")

            # Select system prompt based on strict_mode
            system_prompt = _FRIDGE_SYSTEM_STRICT if req.strict_mode else _FRIDGE_SYSTEM_BASE

            mode_instruction = (
                "Używaj WYŁĄCZNIE podanych składników — żadnych dodatków spoza listy. "
                "Jeśli nie można stworzyć 4 pełnych dań, zwróć TYLKO: Error01"
                if req.strict_mode else
                "Generuj 4 dania na bazie tych składników. Dopuszczalne są standardowe dodatki "
                "(sól, pieprz, oliwa, podstawowe przyprawy) spoza listy."
            )

            # Scal exclusions dla KITCHEN_PROMPT: allergies z DB + avoid + tryb
            _fc_excl_parts = []
            _fc_excl_parts.append(f"alergie: {user.allergies.strip() if user.allergies else 'brak'}")
            if avoid_str and avoid_str != "brak":
                _fc_excl_parts.append(f"unikane: {avoid_str}")
            if preferred_str and preferred_str != "brak":
                _fc_excl_parts.append(f"preferowane: {preferred_str}")
            _fc_excl_parts.append(f"tryb: {mode_instruction}")
            _fc_excl_full = " | ".join(_fc_excl_parts)

            try:
                user_msg = _get_prompt(
                    KITCHEN_PROMPT, _KITCHEN_PROMPT_FB,
                    ingredients=ingredients_str,
                    goal=user.goal or "ogólna sprawność",
                    remaining_calories=meal_kcal,
                    # Fix 1: jawny fallback 'brak' zamiast pustego stringa
                    exclusions=_fc_excl_full or "brak",
                )
                # Dołącz pełny profil dla fridge-chef (bardziej szczegółowy)
                user_msg += (
                    f"\n\nDodatkowe dane profilu:"
                    f"\n  Imię: {user.name or 'brak'}, Dieta: {user.diet or 'brak'}"
                    f"\n  Kontuzje: {user.injuries or 'brak'}"
                    f"\n  Kontekst: {req.extra_context or 'brak'}"
                    "\n\nWygeneruj 4 przepisy zgodnie z instrukcjami systemowymi."
                )
            except Exception as _fmt_exc:
                print(f"[AI ERROR] {datetime.now()}: Błąd w module [FridgeChef/PromptFormat]: {_fmt_exc}")
                user_msg = (
                    f"Składniki: {ingredients_str}. Cel: {user.goal or 'brak'}. "
                    f"Alergie: {user.allergies or 'brak'}. Kcal/posiłek: ~{meal_kcal}. "
                    f"Tryb: {mode_instruction}. "
                    "Wygeneruj 4 przepisy zgodnie z instrukcjami systemowymi."
                )

            print("[FridgeChef] Calling ask_claude()...")
            recipe_text = ask_claude(system_prompt, user_msg, max_tokens=2400)

            # Check if ask_claude returned _AIError (fallback response)
            if isinstance(recipe_text, _AIError):
                print(f"[AI ERROR] {datetime.now()}: Błąd w module [FridgeChef/AskClaude]: {recipe_text}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Błąd serwisu AI: {str(recipe_text)}"
                )

            print("[FridgeChef] Recipe generated successfully OK")
            return {
                "recipe": recipe_text,
                "meta": {
                    "ingredients_used": req.ingredients,
                    "kcal_target_per_meal": meal_kcal,
                    "protein_target_g":     protein_target,
                    "user_goal":            user.goal,
                    "user_diet":            user.diet,
                },
            }

    except HTTPException as http_err:
        print(f"[FridgeChef] HTTP Exception: {http_err.detail}")
        raise
    except Exception as err:
        print(f"[FridgeChef] Unexpected Error: {type(err).__name__}: {err}")
        raise HTTPException(
            status_code=500,
            detail="Nieoczekiwany błąd podczas generowania przepisu. Spróbuj ponownie."
        )


# ─── Nowy endpoint Kitchen Generate ──────────────────────────────────────────

@app.post("/app/kitchen/generate", tags=["ai_chef"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def app_kitchen_generate(request: Request, req: FridgeChefRequest):
    """
    Generuje 4 przepisy na podstawie wybranych składników.
    Zwraca JSON tablica 4 obiektów: { nazwa, składniki, opis, kalorie }
    
    Uwaga: Zamiast JWT, używa identity_id z payloadu do identyfikacji użytkownika.
    """
    print(f"[KitchenGenerate] Incoming request: identity_id={req.identity_id}, {len(req.ingredients)} ingredients, strict_mode={req.strict_mode}")
    
    if not req.ingredients:
        print("[KitchenGenerate] ERROR: Empty ingredients list")
        raise HTTPException(status_code=422, detail="Lista składników nie może być pusta.")
    if len(req.ingredients) > 30:
        print(f"[KitchenGenerate] ERROR: Too many ingredients ({len(req.ingredients)} > 30)")
        raise HTTPException(status_code=422, detail="Maksymalnie 30 składników naraz.")

    try:
        with Session(engine) as session:
            # ─ Znalezienie user'a po identity_id ─
            user = session.exec(
                select(UserDB).where(UserDB.identity_id == req.identity_id)
            ).first()
            
            if not user:
                print(f"[KitchenGenerate] ERROR: User not found for identity_id={req.identity_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Użytkownik z identity_id='{req.identity_id}' nie znaleziony. Proszę się zalogować."
                )
            
            kcal_target   = user.calories_target or calc_calories(user)
            protein_target = user.protein_target or calc_protein(user)
            avoid_foods   = user.get_list("avoid_foods_json")
            preferred     = user.get_list("preferred_foods_json")

            meals_n    = max(user.meals_per_day, 1)
            meal_kcal  = int(kcal_target / meals_n)

            ingredients_str = ", ".join(req.ingredients)
            avoid_str       = ", ".join(avoid_foods) if avoid_foods else "brak"
            preferred_str   = ", ".join(preferred)   if preferred   else "brak"

            print(f"[KitchenGenerate] User: {user.name}, kcal_target: {kcal_target}, meal_kcal: {meal_kcal}")
            print(f"[KitchenGenerate] Ingredients: {ingredients_str}")
            print(f"[KitchenGenerate] Avoid foods: {avoid_str}")

            mode_instruction = (
                "Używaj WYŁĄCZNIE podanych składników — żadnych dodatków spoza listy. "
                "Jeśli nie można stworzyć 4 pełnych dań, zwróć JSON z pustą tablicą []. "
                "Format JSON obowiązkowy!"
                if req.strict_mode else
                "Generuj 4 dania na bazie tych składników. Dopuszczalne są standardowe dodatki "
                "(sól, pieprz, oliwa, podstawowe przyprawy) spoza listy. Format JSON obowiązkowy!"
            )

            # ── Budowanie promptu: _get_prompt() + KITCHEN_PROMPT z prompts.py ─────
            # exclusions scala: allergies z bazy + avoid_foods + preferowane + tryb
            # _get_prompt() gwarantuje bezpieczeństwo: None → 'brak', KeyError → fallback
            _kitchen_system = (
                "Jesteś kulinarzem AI FitAI. Generujesz przepisy na podstawie "
                "dostępnych składników. ZAWSZE odpowiadaj WYŁĄCZNIE ważnym, "
                "prawidłowo sformatowanym JSON (tablica 4 przepisów). "
                'Każdy przepis musi mieć pola: "nazwa", "składniki", "opis", '
                '"kalorie", "białko", "węglowodany", "tłuszcze".'
            )

            # Scal exclusions: alergie z bazy + unikane + preferowane + tryb
            _excl_parts = []
            _excl_parts.append(f"alergie: {user.allergies.strip() if user.allergies else 'brak'}")
            if avoid_str and avoid_str != "brak":
                _excl_parts.append(f"unikane: {avoid_str}")
            if preferred_str and preferred_str != "brak":
                _excl_parts.append(f"preferowane: {preferred_str}")
            _excl_parts.append(f"tryb: {mode_instruction}")
            _exclusions_full = " | ".join(_excl_parts)

            try:
                user_msg = _get_prompt(
                    KITCHEN_PROMPT, _KITCHEN_PROMPT_FB,
                    ingredients=ingredients_str,
                    goal=user.goal or "ogólna sprawność",
                    remaining_calories=meal_kcal,
                    # Fix 1: jawny fallback 'brak' zamiast pustego stringa
                    exclusions=_exclusions_full or "brak",
                )
                user_msg += (
                    f"\n\nDieta: {user.diet or 'brak'}."
                    f"\nKontekst: {req.extra_context or 'brak'}."
                    "\n\nWygeneruj 4 przepisy w formacie JSON. TYLKO JSON."
                )
                system_prompt = _kitchen_system
            except Exception as _fmt_exc:
                print(f"[AI ERROR] {datetime.now()}: Błąd w module [KitchenGenerate/PromptFormat]: {_fmt_exc}")
                system_prompt = _kitchen_system
                user_msg = (
                    f"Cel: {user.goal or 'brak'}. Dieta: {user.diet or 'brak'}. "
                    f"Alergie: {user.allergies or 'brak'}. Unikane: {avoid_str or 'brak'}.\n"
                    f"Składniki: {ingredients_str}. Kcal/posiłek: ~{meal_kcal}.\n"
                    f"Tryb: {mode_instruction}.\nWygeneruj 4 przepisy w formacie JSON. TYLKO JSON."
                )

            print("[KitchenGenerate] Calling ask_claude()...")
            try:
                response_text = ask_claude(system_prompt, user_msg, max_tokens=4096)
                
                # Check if ask_claude returned _AIError
                if isinstance(response_text, _AIError):
                    print(f"[AI ERROR] {datetime.now()}: Błąd w module [KitchenGenerate/AskClaude]: {response_text}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"Błąd serwisu AI: {str(response_text)}"
                    )
                
                print(f"[KitchenGenerate] Raw AI response (first 200 chars): {response_text[:200]}")
                
                # Try to parse JSON
                try:
                    # Clean up response - remove markdown code blocks if present
                    json_str = response_text.strip()
                    if json_str.startswith("```json"):
                        json_str = json_str[7:]
                    if json_str.startswith("```"):
                        json_str = json_str[3:]
                    if json_str.endswith("```"):
                        json_str = json_str[:-3]
                    json_str = json_str.strip()
                    
                    recipes = json.loads(json_str)
                    print(f"[KitchenGenerate] Parsed {len(recipes)} recipes successfully OK")
                    
                    # Validate structure
                    if not isinstance(recipes, list):
                        print("[KitchenGenerate] ERROR: Response is not a list")
                        raise ValueError("Response must be a list of recipes")
                    
                    if len(recipes) == 0:
                        print("[KitchenGenerate] WARNING: Empty recipes list")
                    
                    # Validate each recipe
                    for i, recipe in enumerate(recipes):
                        if not isinstance(recipe, dict):
                            print(f"[KitchenGenerate] ERROR: Recipe {i} is not a dict")
                            raise ValueError(f"Recipe {i} must be a dict")
                        required = ["nazwa", "składniki", "opis", "kalorie"]
                        for req_field in required:
                            if req_field not in recipe:
                                print(f"[KitchenGenerate] WARNING: Recipe {i} missing field '{req_field}'")
                                recipe[req_field] = "" if req_field != "kalorie" else 0
                    
                    print("[KitchenGenerate] Recipes validated successfully OK")
                    return {"recipes": recipes}
                    
                except json.JSONDecodeError as json_err:
                    print(f"[KitchenGenerate] JSON Parse Error: {json_err}")
                    print(f"[KitchenGenerate] Raw response was: {response_text[:500]}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"AI zwróciło nieprawidłowy format JSON. Spróbuj ponownie."
                    )
            except HTTPException:
                raise
            except Exception as ai_err:
                print(f"[KitchenGenerate] AI call error: {type(ai_err).__name__}: {ai_err}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Błąd połączenia z AI: {str(ai_err)}"
                )
    
    except HTTPException as http_err:
        print(f"[KitchenGenerate] HTTP Exception: {http_err.detail}")
        raise
    except Exception as err:
        print(f"[KitchenGenerate] Unexpected Error: {type(err).__name__}: {err}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Nieoczekiwany błąd podczas generowania przepisów. Spróbuj ponownie."
        )


@app.get("/app/meal-prep-plan", tags=["ai_chef"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def app_meal_prep_plan(request: Request, days: int = 3, extra_context: Optional[str] = None, user: UserDB = Depends(get_current_user)):
    """
    Analizuje wygenerowany plan posiłków użytkownika na N dni
    i zwraca zbiorczą listę zakupów + harmonogram batch-cooking.
    """
    print(f"[MealPrepPlan] Incoming request: days={days}, user={user.name}")
    
    if not 1 <= days <= 7:
        print(f"[MealPrepPlan] ERROR: Invalid days parameter ({days})")
        raise HTTPException(status_code=422, detail="Parametr days musi być między 1 a 7.")

    try:
        with Session(engine) as session:
            # Refresh user from session to ensure we have latest data
            user = session.merge(user)

            kcal_target    = user.calories_target or calc_calories(user)
            protein_target = user.protein_target  or calc_protein(user)

            print(f"[MealPrepPlan] User targets: {kcal_target} kcal, {protein_target}g protein")

            # ── Pobierz wygenerowany plan tygodniowy użytkownika ────────────────
            weekly_plan: dict = {}
            if user.weekly_plan_json:
                try:
                    weekly_plan = json.loads(user.weekly_plan_json)
                except (json.JSONDecodeError, TypeError, ValueError):
                    weekly_plan = {}

            # Spróbuj też wyciągnąć plan z najnowszych logów diety (DailyLogDB.food)
            recent_logs = list(session.exec(
                select(DailyLogDB)
                .where(DailyLogDB.user_id == user.id)
                .order_by(DailyLogDB.log_date.desc())
            ).all())[:days]

            diet_log_summary = []
            for log in reversed(recent_logs):
                if log.food:
                    diet_log_summary.append(f"  {log.log_date}: {log.food}")

            # ── Zbuduj opis planu posiłków ────────────────────────────────────
            # Preferuj weekly_plan jeśli istnieje, fallback do logów
            plan_description = ""
            if weekly_plan:
                day_names = ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"]
                pl_map    = {"Pon":"Poniedziałek","Wt":"Wtorek","Śr":"Środa",
                             "Czw":"Czwartek","Pt":"Piątek","Sob":"Sobota","Niedz":"Niedziela"}
                lines = []
                for day_key, day_full in pl_map.items():
                    if len(lines) >= days:
                        break
                    diet_day = weekly_plan.get("diet", {}).get(day_key, [])
                    if diet_day:
                        meals_str = "; ".join(
                            f"{m.get('name','?')} ({m.get('kcal',0)} kcal, B:{m.get('protein',0)}g)"
                            for m in diet_day
                        )
                        lines.append(f"  {day_full}: {meals_str}")
                plan_description = "\n".join(lines)
            elif diet_log_summary:
                plan_description = "\n".join(diet_log_summary)
            else:
                # Brak danych — poproś AI o wygenerowanie na bazie profilu
                plan_description = (
                    f"Brak zapisanego planu. Wygeneruj optymalny meal-prep dla osoby:\n"
                    f"  Cel: {user.goal}, dieta: {user.diet}, "
                    f"  {kcal_target} kcal/dzień, {protein_target}g białka/dzień, "
                    f"  {user.meals_per_day} posiłków/dzień.\n"
                    f"  Upodobania: {', '.join(user.get_list('preferred_foods_json')) or 'brak danych'}"
                )

            user_msg = (
                f"Profil użytkownika:\n"
                f"  Imię: {user.name} | Cel: {user.goal} | Dieta: {user.diet}\n"
                f"  Dzienny limit: {kcal_target} kcal | Białko: {protein_target}g\n"
                f"  Liczba posiłków/dzień: {user.meals_per_day}\n"
                f"  Alergie: {user.allergies or 'brak'}\n"
                f"  Unikane produkty: {', '.join(user.get_list('avoid_foods_json')) or 'brak'}\n"
                f"  Sprzęt kuchenny: standardowy (piekarnik, patelnia, garnek, blender)\n\n"
                f"Plan posiłków na {days} {'dzień' if days == 1 else 'dni' if days < 5 else 'dni'}:\n"
                f"{plan_description}\n\n"
                f"Kontekst dodatkowy: {extra_context or 'brak'}\n\n"
                f"Wygeneruj kompletny plan meal-prep na {days} dni zgodnie z instrukcjami systemowymi."
            )

            print("[MealPrepPlan] Calling ask_claude()...")
            meal_prep_text = ask_claude(_MEAL_PREP_SYSTEM, user_msg, max_tokens=1400)

            # Check if ask_claude returned _AIError
            if isinstance(meal_prep_text, _AIError):
                print(f"[MealPrepPlan] AI Error: {meal_prep_text}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Błąd serwisu AI: {str(meal_prep_text)}"
                )

            print("[MealPrepPlan] Plan generated successfully OK")
            return {
                "meal_prep_plan": meal_prep_text,
                "meta": {
                    "days":            days,
                    "kcal_target":     kcal_target,
                    "protein_target":  protein_target,
                    "plan_source":     "weekly_plan" if weekly_plan else ("diet_logs" if diet_log_summary else "ai_generated"),
                    "meals_per_day":   user.meals_per_day,
                },
            }

    except HTTPException as http_err:
        print(f"[MealPrepPlan] HTTP Exception: {http_err.detail}")
        raise
    except Exception as err:
        print(f"[MealPrepPlan] Unexpected Error: {type(err).__name__}: {err}")
        raise HTTPException(
            status_code=500,
            detail="Nieoczekiwany błąd podczas generowania meal-prep. Spróbuj ponownie."
        )


# ─── Stats / Progress endpoint ───────────────────────────────────────────────

@app.get("/app/stats", tags=["stats"])
def app_get_stats(days: int = 30, user: UserDB = Depends(get_current_user)):
    """
    Agreguje dane postępów użytkownika z DailyLogDB i ExerciseResultDB.
    Zwraca:
      - weight_entries: ostatnie 30 wpisów wagi (data + wartość + nastrój)
      - training_volume: wolumen treningowy per dzień (serie × powtórzenia × ciężar)
      - diet_compliance_pct: % dni z zalogowanymi posiłkami
      - streak_days: aktualny streak (dni z rzędu z aktywnością)
      - kpi: zmienność wagi, średnie RPE (7d), prognozowana data celu
    """
    with Session(engine) as session:

        # ── Daily logs ────────────────────────────────────────────────────────
        all_logs = list(session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .order_by(DailyLogDB.log_date)
        ).all())

        # Weight entries (last `days`, include mood for tooltip)
        weight_entries = [
            {"date": l.log_date, "weight": l.weight, "mood": l.mood}
            for l in all_logs if l.weight is not None
        ][-days:]

        # Diet compliance: days with food logged / total days with any log
        log_days_total = len({l.log_date for l in all_logs})
        food_days = len({l.log_date for l in all_logs if l.food and l.food.strip()})
        diet_compliance_pct = round((food_days / log_days_total) * 100) if log_days_total else 0

        # Streak
        streak_days = _compute_streak_days_from_logs(all_logs)

        # ── Exercise results → training volume per day ────────────────────────
        ex_results = list(session.exec(
            select(ExerciseResultDB)
            .where(ExerciseResultDB.user_id == user.id)
            .order_by(ExerciseResultDB.session_date)
        ).all())

        volume_by_day: dict = {}
        for r in ex_results:
            vol = r.sets * r.reps * r.weight_kg
            volume_by_day[r.session_date] = volume_by_day.get(r.session_date, 0) + vol

        training_volume = [
            {"date": d, "volume": round(v)}
            for d, v in sorted(volume_by_day.items())
        ][-days:]

        # ── KPI calculations ──────────────────────────────────────────────────
        # 1. Weight delta (start vs latest)
        weight_delta = None
        if weight_entries:
            first_w = weight_entries[0]["weight"]
            last_w = weight_entries[-1]["weight"]
            if first_w and last_w:
                weight_delta = round(last_w - first_w, 1)

        # 2. Average RPE last 7 days
        cutoff_7d = (date.today().toordinal() - 7)
        recent_rpe = [
            r.rpe for r in ex_results
            if r.session_date and date.fromisoformat(r.session_date).toordinal() >= cutoff_7d
        ]
        avg_rpe_7d = round(sum(recent_rpe) / len(recent_rpe), 1) if recent_rpe else None

        # 3. Projected goal date based on weight trend
        goal_date_estimate = None
        target_weight = user.target_weight
        if len(weight_entries) >= 2 and target_weight:
            # Use linear regression on last 14 entries
            recent_w = weight_entries[-14:]
            n = len(recent_w)
            if n >= 2:
                # Simple slope: (last - first) / days_between
                try:
                    d0 = date.fromisoformat(recent_w[0]["date"])
                    d1 = date.fromisoformat(recent_w[-1]["date"])
                    days_span = (d1 - d0).days or 1
                    w0 = recent_w[0]["weight"]
                    w1 = recent_w[-1]["weight"]
                    daily_rate = (w1 - w0) / days_span  # kg/day; negative = losing
                    remaining = target_weight - w1
                    if daily_rate != 0 and (remaining / daily_rate) > 0:
                        days_to_goal = int(remaining / daily_rate)
                        goal_date = date.today().toordinal() + days_to_goal
                        goal_date_estimate = date.fromordinal(goal_date).isoformat()
                except (ValueError, OverflowError):
                    pass

        # ── Stagnation detection ─────────────────────────────────────────────
        # Porównaj średnią wagę: ostatnie 7 vs poprzednie 7 wpisów wagowych
        stagnation_detected = False
        stagnation_info: dict = {}
        goal_lower = (user.goal or "").lower()
        is_reduction_goal = any(x in goal_lower for x in ["redukcj", "odchudzani", "schud"])
        is_mass_goal = any(x in goal_lower for x in ["masa", "budow", "przyty"])

        all_weight_entries = [
            {"date": l.log_date, "weight": l.weight}
            for l in all_logs if l.weight is not None
        ]
        if len(all_weight_entries) >= 14:
            recent_7 = [e["weight"] for e in all_weight_entries[-7:]]
            prev_7 = [e["weight"] for e in all_weight_entries[-14:-7]]
            avg_recent = sum(recent_7) / len(recent_7)
            avg_prev = sum(prev_7) / len(prev_7)
            delta = round(avg_recent - avg_prev, 2)
            if (is_reduction_goal or is_mass_goal) and abs(delta) < 0.1:
                stagnation_detected = True
            stagnation_info = {
                "avg_weight_last_7": round(avg_recent, 2),
                "avg_weight_prev_7": round(avg_prev, 2),
                "delta_kg": delta,
                "goal_type": "redukcja" if is_reduction_goal else ("masa" if is_mass_goal else "inne"),
                "message": (
                    "Brak zmian wagi od 2 tygodni — czas na korektę deficytu lub planu treningowego."
                    if stagnation_detected else
                    f"Waga zmienia się zgodnie z planem ({delta:+.2f} kg / 7 dni)."
                ),
            }

        # ── XP & leveling ────────────────────────────────────────────────────
        xp_info = _xp_to_next_level(user.total_xp or 0)

        # ── Overload detection ────────────────────────────────────────────────
        overload = _check_overload(user.id, session, threshold_pct=0.20)

        # ── Injuries list ─────────────────────────────────────────────────────
        injuries_list = [i.strip() for i in (user.injuries or "").split(",") if i.strip()]

        # ── Update last_weight_change on user record (passive update) ─────────
        if len(all_weight_entries) >= 2:
            w_latest = all_weight_entries[-1]["weight"]
            w_prev = all_weight_entries[-2]["weight"]
            new_delta = round(w_latest - w_prev, 2)
            if user.last_weight_change != new_delta:
                user.last_weight_change = new_delta
                session.commit()

        return {
            "weight_entries": weight_entries,
            "training_volume": training_volume,
            "diet_compliance_pct": diet_compliance_pct,
            "streak_days": streak_days,
            "target_weight": target_weight,
            "kpi": {
                "weight_delta": weight_delta,
                "avg_rpe_7d": avg_rpe_7d,
                "goal_date_estimate": goal_date_estimate,
            },
            # ── v2 extensions ─────────────────────────────────────────────────
            "stagnation_detected": stagnation_detected,
            "stagnation": stagnation_info,
            "xp": xp_info,
            "overload": overload,
            "injuries": injuries_list,
            "last_weight_change": user.last_weight_change,
        }


# ─── Diet: Add meal to today's log ───────────────────────────────────────────

class AddMealRequest(BaseModel):
    meal_id: str                      # Unikalny identyfikator posiłku z katalogu
    meal_name: str                    # Nazwa posiłku do dopisania w logu
    meal_kcal: Optional[int] = None   # Kalorie (opcjonalne — do wzbogacenia logu)
    meal_type: Optional[str] = None   # Typ: Śniadanie / Obiad / Kolacja / Przekąska
    log_date: Optional[str] = None    # ISO date; domyślnie dzisiaj


@app.post("/app/diet/add-meal", tags=["diet"])
def app_diet_add_meal(req: AddMealRequest, user: UserDB = Depends(get_current_user)):
    """
    Dopisuje wybrany posiłek do logu diety bieżącego użytkownika.

    Jeśli dla danego dnia istnieje już wpis w DailyLogDB, nowa pozycja jest
    doklejana do pola `food` (oddzielona separatorem ' | ').
    Jeśli wpisu nie ma, tworzony jest nowy rekord.

    Zwraca zaktualizowany wpis dnia oraz status operacji.
    """
    target_date = req.log_date or date.today().isoformat()

    # Zbuduj czytelny string opisujący posiłek
    meal_entry_parts = [req.meal_name]
    if req.meal_type:
        meal_entry_parts.insert(0, f"[{req.meal_type}]")
    if req.meal_kcal:
        meal_entry_parts.append(f"({req.meal_kcal} kcal)")
    meal_entry = " ".join(meal_entry_parts)

    with Session(engine) as session:
        existing = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .where(DailyLogDB.log_date == target_date)
        ).first()

        if existing:
            # Doklejamy nowy posiłek do istniejącego logu
            if existing.food and existing.food.strip():
                existing.food = f"{existing.food} | {meal_entry}"
            else:
                existing.food = meal_entry
            existing.logged_at = datetime.now().isoformat()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            log_dict = existing.to_dict()
        else:
            # Tworzymy nowy wpis na ten dzień
            new_log = DailyLogDB(
                user_id=user.id,
                log_date=target_date,
                food=meal_entry,
            )
            session.add(new_log)
            session.commit()
            session.refresh(new_log)
            log_dict = new_log.to_dict()

    return {
        "status": "ok",
        "message": f"Dodano '{req.meal_name}' do diety na dzień {target_date}.",
        "meal_added": meal_entry,
        "log": log_dict,
    }


# ─── Auth: Logout ─────────────────────────────────────────────────────────────

@app.post("/app/logout", tags=["auth"])
def app_logout(user: UserDB = Depends(get_current_user)):
    """
    POST /app/logout

    JWT jest bezstanowy — serwer nie przechowuje tokenów, więc nie ma
    po stronie backendu nic do „unieważnienia". Prawdziwe unieważnienie
    realizuje frontend usuwając token z localStorage/sessionStorage.

    Ten endpoint:
    1. Weryfikuje token (get_current_user) — wiadomo, że żądanie pochodzi od autentycznego użytkownika.
    2. Zwraca instrukcję dla frontendu wraz z nazwą klucza do usunięcia.
    3. Opcjonalnie: jeśli wdrożysz token-blacklist (Redis/DB), tutaj dodaj wpis.

    Odpowiedź 200 z clear_storage zawsze — nawet jeśli token już wygasł
    (w takim przypadku get_current_user rzuci 401 wcześniej).
    """
    return {
        "status": "logged_out",
        "message": f"Użytkownik {user.name!r} wylogowany pomyślnie.",
        # Instrukcja dla frontendu: usuń te klucze z localStorage
        "clear_storage": ["fitai_token", "fitai_identity_id", "fitai_user"],
        "user_id": user.id,
        "timestamp": datetime.now().isoformat(),
        # Hint: token wygasa naturalnie po ACCESS_TOKEN_EXPIRE_MINUTES
        # Nie wysyłaj już żadnych requestów tym tokenem po tej odpowiedzi.
        "note": (
            "Usuń token z localStorage. "
            "JWT wygasa po stronie serwera automatycznie po upływie ważności."
        ),
    }


# ─── Version & root ───────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "FitAI API", "version": "2.0.0", "docs": "/docs", "status": "running"}


@app.get("/app/version")
def get_version():
    try:
        with open("package.json", "r") as f:
            version = json.load(f).get("version", "2.0.0")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        version = "2.0.0"
    return {"version": version, "build_date": datetime.now().strftime("%Y-%m-%d"), "api_version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)