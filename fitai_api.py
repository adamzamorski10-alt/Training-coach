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
from typing import Any, Dict, List, Optional

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
from sqlalchemy import text as _text
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select


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

    logs: List["DailyLogDB"] = Relationship(back_populates="user")
    exercise_results: List["ExerciseResultDB"] = Relationship(back_populates="user")

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

    user: Optional[UserDB] = Relationship(back_populates="logs")

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

    user: Optional[UserDB] = Relationship(back_populates="exercise_results")

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
    success_count: int                          # trafienia / powtórzenia
    total_attempts: int                         # łączna liczba prób
    rpe: int = Field(ge=1, le=10)              # 1 = bardzo lekko, 10 = maksymalny wysiłek
    notes: str = ""
    logged_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "drill_name": self.drill_name,
            "session_date": self.session_date,
            "success_count": self.success_count,
            "total_attempts": self.total_attempts,
            "accuracy_pct": round(self.success_count / self.total_attempts * 100) if self.total_attempts else 0,
            "rpe": self.rpe,
            "notes": self.notes,
            "logged_at": self.logged_at,
        }


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
    "https://training-coach-app.netlify.app",
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
        print("[FitAI] ✅ Groq: klient zainicjalizowany (primary AI).")
    else:
        print(
            "[FitAI] ⚠️  GROQ_API_KEY nie jest ustawiony. "
            "Endpointy AI będą używać wyłącznie Gemini (fallback). "
            "Dodaj GROQ_API_KEY do pliku .env, aby włączyć primary AI."
        )

    # ── 2. Inicjalizacja Google Gemini ────────────────────────────────────────
    _gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if _gemini_key:
        genai.configure(api_key=_gemini_key)
        _gemini_ready = True
        print("[FitAI] ✅ Gemini: klient zainicjalizowany (fallback AI).")
    else:
        print(
            "[FitAI] ⚠️  GEMINI_API_KEY nie jest ustawiony. "
            "Fallback AI jest wyłączony. "
            "Dodaj GEMINI_API_KEY do pliku .env, aby aktywować fallback."
        )

    if not _groq_key and not _gemini_key:
        print(
            "[FitAI] ❌ ŻADEN klucz AI nie jest ustawiony (GROQ_API_KEY, GEMINI_API_KEY). "
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
    training_focus: List[str] = []
    improvement_areas: List[str] = []
    sports: List[str] = []
    diet: str
    allergies: str = ""
    preferred_foods: List[str] = []
    avoid_foods: List[str] = []
    available_equipment: List[str] = []
    avoid_exercises: List[str] = []
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
    sports: List[str] = []
    training_focus: List[str] = []
    improvement_areas: List[str] = []
    diet: str
    allergies: str = ""
    preferred_foods: List[str] = []
    avoid_foods: List[str] = []
    available_equipment: List[str] = []
    avoid_exercises: List[str] = []
    meals_per_day: int = 4
    notes: str = ""


class AppDailyCheckinRequest(BaseModel):
    food: str = ""
    workout: str = ""
    mood: str = ""
    weight: Optional[float] = None


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
    """Wynik sesji drilla sportowego z oceną RPE."""
    drill_name: str
    success_count: int
    total_attempts: int
    rpe: int = Field(ge=1, le=10, description="Rate of Perceived Exertion 1-10")
    notes: str = ""
    session_date: Optional[str] = None  # ISO date; jeśli brak → today


class SportConfigRequest(BaseModel):
    """Konfiguracja modułu sportowego użytkownika."""
    sport_focus: str                            # np. "koszykówka"
    sport_specialization: str = ""             # np. "rzuty"
    sport_training_days: List[str] = []        # np. ["Środa", "Sobota"]


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


# ─── Progressive Overload / RPE helpers ───────────────────────────────────────

_RPE_LOW_THRESHOLD = 6    # ≤6 → too easy → increase load
_RPE_HIGH_THRESHOLD = 9   # ≥9 → too hard → decrease or keep

_WEIGHT_INCREMENT_KG = 2.5
_REPS_INCREMENT = 1


def _suggest_progression(
    exercise_name: str,
    recent_results: List[ExerciseResultDB],
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

SPORT_DRILLS_DB: Dict[str, Dict[str, List[dict]]] = {
    "koszykówka": {
        "rzuty": [
            {
                "name": "Rzuty osobiste",
                "total_attempts": 20,
                "description": "Standardowe rzuty wolne z linii rzutów osobistych.",
                "progression_tip": "Cel: ≥15/20 (75%) przez 2 sesje z rzędu → zwiększ do 25 prób.",
            },
            {
                "name": "Rzuty za 3 punkty",
                "total_attempts": 20,
                "description": "5 rzutów z 4 różnych pozycji za łukiem (corners, wings, top).",
                "progression_tip": "Cel: ≥10/20 (50%) → dodaj 5 prób lub utrudnij pozycje.",
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
    recent_results: List[DrillResultDB],
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
_XP_THRESHOLDS = [0, 500, 1200, 2200, 3500, 5500, 8000, 11500, 16000, 22000, 30000]

# XP per akcja
_XP_CHECKIN = 20         # codzienne logowanie check-inu
_XP_MEAL_LOGGED = 5      # zaznaczenie posiłku
_XP_WEIGHT_LOGGED = 15   # wpis wagi
_XP_WORKOUT_LOGGED = 30  # wpis treningu
_XP_STREAK_BONUS = 10    # bonus za każdy dzień streaku (cumulatywnie)


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
    by_exercise: Dict[str, Dict[str, float]] = {}
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


def _compute_streak_days_from_logs(logs: List[DailyLogDB]) -> int:
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

def _build_dashboard(user: UserDB, logs: List[DailyLogDB]) -> dict:
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

    _sport_drills: List[dict] = []
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

    shuffled_meals: Dict[str, list] = {}
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
    shuffled_pool: Dict[str, list] = {}
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
    Wywołuje Groq API (model llama-3-70b-versatile).
    Rzuca wyjątek przy każdym błędzie — caller decyduje o fallbacku.
    """
    if _groq_client is None:
        raise RuntimeError("Groq client nie jest zainicjalizowany (brak GROQ_API_KEY)")

    completion = _groq_client.chat.completions.create(
        model="llama3-70b-8192",      # aktualny identyfikator modelu w Groq API
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
    )
    return completion.choices[0].message.content


def _call_gemini(system: str, user_msg: str, max_tokens: int) -> str:
    """
    Wywołuje Google Gemini API (model gemini-1.5-flash).
    Rzuca wyjątek przy każdym błędzie.
    """
    if not _gemini_ready:
        raise RuntimeError("Gemini client nie jest zainicjalizowany (brak GEMINI_API_KEY)")

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
    )
    response = model.generate_content(user_msg)
    return response.text


def ask_ai(system: str, user_msg: str, max_tokens: int = 800) -> str:
    """
    Główna funkcja AI z architekturą Groq → Gemini fallback.

    Sekwencja:
      1. Próbuje Groq (llama3-70b-8192) — szybki, darmowy tier.
      2. Jeśli Groq zwróci błąd (limit zapytań, brak klucza, błąd sieci)
         → automatycznie przechodzi na Gemini (gemini-1.5-flash).
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
            print("[FitAI] AI: odpowiedź z Groq ✅")
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
            print("[FitAI] AI: odpowiedź z Gemini (fallback) ✅")
            return text
        except Exception as e:
            print(f"[FitAI] Gemini: błąd ({type(e).__name__}: {e}) — serwuję odpowiedź lokalną.")
    else:
        print("[FitAI] AI: Gemini niedostępny (brak klucza) — serwuję odpowiedź lokalną.")

    # ── Krok 3: Lokalny fallback ──────────────────────────────────────────────
    return _AIError(_fallback_response("oba dostawcy AI niedostępni", system_hint))


# Alias wsteczny — wszystkie istniejące wywołania ask_claude() działają bez zmian
ask_claude = ask_ai


# ─── DB helpers ───────────────────────────────────────────────────────────────

def _get_user_or_404(user_key: str, session: Session) -> UserDB:
    user = session.exec(select(UserDB).where(UserDB.user_key == user_key)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    return user


def _get_user_logs(user: UserDB, session: Session) -> List[DailyLogDB]:
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
            session.delete(existing)
            session.flush()
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

        by_exercise: Dict[str, List[ExerciseResultDB]] = {}
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
            session.delete(existing)
            session.flush()
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
        return {
            "status": "ok",
            "log": entry.to_dict(),
            "streak_days": user.streak_days,
            "today_eaten": entry.get_eaten_meals() if hasattr(entry, "get_eaten_meals") else [],
            "xp_earned": xp_earned,
            "total_xp": user.total_xp,
            "level": _xp_to_level(user.total_xp),
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

    return {
        "status": "ok",
        "added_ml": ml,
        "water_liters_today": total_liters,
        "water_ml_today": round(total_liters * 1000),
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
    """Zapisuje wynik drilla sportowego i zwraca sugestię progresji."""
    session_date = payload.session_date or date.today().isoformat()

    with Session(engine) as session:

        result = DrillResultDB(
            user_id=user.id,
            drill_name=payload.drill_name,
            session_date=session_date,
            success_count=payload.success_count,
            total_attempts=payload.total_attempts,
            rpe=payload.rpe,
            notes=payload.notes,
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

        return {
            "status": "ok",
            "result": result.to_dict(),
            "progression": progression,
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
        by_name: Dict[str, list] = {}
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
            f"Typ dnia (carb cycling): {day_type}\n"
            f"Makroskładniki DZIŚ: {macros['kcal']} kcal, "
            f"białko {macros['protein_g']}g, węgle {macros['carbs_g']}g, tłuszcze {macros['fat_g']}g\n"
            f"Dzień: {day_of_week}\n"
            f"Dieta: {user.diet}, alergie: {user.allergies or 'brak'}\n"
            f"Posiłków dziennie: {user.meals_per_day}\n\n"
            f"Kontekst: {req.extra_context or 'brak'}\n\n"
            "Utwórz szczegółowy plan diety na DZIŚ z godzinami, pełnymi nazwami produktów, "
            "gramaturą i kaloriami każdego posiłku. Na końcu łączne makroskładniki."
        )
        return {"plan": ask_claude(system, user_msg, 1000), "calories_target": kcal, "protein_target": protein, "macros": macros}


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
        by_name: Dict[str, list] = {}
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
        return {"plan": ask_claude(system, user_msg, 900)}


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
            f"Makro na dziś ({day_type}): {macros}\n\n"
            f"Raport z dziś:\n"
            f"- Co jadłem: {today_log.food or 'nie podano'}\n"
            f"- Trening: {today_log.workout or 'nie podano'}\n"
            f"- Samopoczucie: {today_log.mood or 'nie podano'}\n"
            f"- Waga: {today_log.weight or 'nie podano'} kg\n\n"
            "Oceń dzień i podaj KONKRETNY plan na jutro z makroskładnikami. Max 400 słów."
        )
        return {"analysis": ask_claude(system, user_msg, 1000)}


@app.post("/ai/weekly", tags=["ai"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_weekly_summary(request: Request, req: AIRequest, user: UserDB = Depends(get_current_user)):
    with Session(engine) as session:
        logs = list(session.exec(
            select(DailyLogDB).where(DailyLogDB.user_id == user.id).order_by(DailyLogDB.log_date.desc())
        ).all())[:7]
        system = (
            "Jesteś analitykiem fitness. Piszesz po polsku. "
            "Tworzysz motywujące ale realistyczne podsumowania tygodniowe."
        )
        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Logi z ostatnich 7 dni: {json.dumps([l.to_dict() for l in logs], ensure_ascii=False)}\n\n"
            "Podaj tygodniowe podsumowanie: ocena tygodnia, postęp do celu, "
            "top 3 rekomendacje na kolejny tydzień (dieta + trening). Max 300 słów."
        )
        return {"summary": ask_claude(system, user_msg, 800)}


# ─── XP / Injuries endpoints ─────────────────────────────────────────────────

class InjuryUpdateRequest(BaseModel):
    injuries: List[str] = []   # lista kontuzji, np. ["kolano lewe", "bark prawy"]


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
    ingredients: List[str]                  # np. ["kurczak 300g", "brokuły", "jajka"]
    extra_context: Optional[str] = None     # np. "jestem po treningu siłowym"


class MealPrepRequest(BaseModel):
    days: int = 3                           # ile dni planu uwzględnić (1-7)
    extra_context: Optional[str] = None


# ── SYSTEM PROMPTS ─────────────────────────────────────────────────────────────

_FRIDGE_SYSTEM = """\
Jesteś kulinarnym asystentem sportowym. Piszesz WYŁĄCZNIE po polsku.
Zasady odpowiedzi:
1. Zwróć dokładnie JEDEN przepis — najlepiej pasujący do celu i dostępnych składników.
2. Format odpowiedzi (zachowaj nagłówki):
   ## 🍳 [Nazwa potrawy]
   **Czas przygotowania:** X min
   **Makroskładniki (porcja):** Kcal: X | Białko: Xg | Węgle: Xg | Tłuszcze: Xg
   ### Składniki
   - [ilość] [produkt]  ← tylko to co ma użytkownik + max 2 łatwo dostępne brakujące
   ### Przygotowanie
   Numerowane kroki (max 6). Konkretne, bez lania wody.
   ### 💡 Wskazówka
   Jedno zdanie o modyfikacji pasującej do celu użytkownika.
3. Nie pytaj o nic. Nie dodawaj komentarzy poza formatem. Nie proponuj alternatyw.
"""

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
    if not req.ingredients:
        raise HTTPException(status_code=422, detail="Lista składników nie może być pusta.")
    if len(req.ingredients) > 30:
        raise HTTPException(status_code=422, detail="Maksymalnie 30 składników naraz.")

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

        user_msg = (
            f"Profil użytkownika:\n"
            f"  Imię: {user.name}\n"
            f"  Cel: {user.goal}\n"
            f"  Dieta: {user.diet}\n"
            f"  Cel kaloryczny/dzień: {kcal_target} kcal | białko: {protein_target}g\n"
            f"  Docelowy kcal na 1 posiłek: ~{meal_kcal} kcal (±20%)\n"
            f"  Alergie/wykluczenia: {user.allergies or 'brak'}\n"
            f"  Unikane produkty: {avoid_str}\n"
            f"  Preferowane smaki/produkty: {preferred_str}\n"
            f"  Kontuzje (unikaj ciężkostrawnych potraw): {user.injuries or 'brak'}\n\n"
            f"Mam w lodówce: {ingredients_str}\n\n"
            f"Kontekst dodatkowy: {req.extra_context or 'brak'}\n\n"
            "Wygeneruj 1 przepis zgodnie z instrukcjami systemowymi."
        )

        recipe_text = ask_claude(_FRIDGE_SYSTEM, user_msg, max_tokens=900)

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


@app.get("/app/meal-prep-plan", tags=["ai_chef"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def app_meal_prep_plan(request: Request, days: int = 3, extra_context: Optional[str] = None, user: UserDB = Depends(get_current_user)):
    """
    Analizuje wygenerowany plan posiłków użytkownika na N dni
    i zwraca zbiorczą listę zakupów + harmonogram batch-cooking.
    """
    if not 1 <= days <= 7:
        raise HTTPException(status_code=422, detail="Parametr days musi być między 1 a 7.")

    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)

        kcal_target    = user.calories_target or calc_calories(user)
        protein_target = user.protein_target  or calc_protein(user)

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

        meal_prep_text = ask_claude(_MEAL_PREP_SYSTEM, user_msg, max_tokens=1400)

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