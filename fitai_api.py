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

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

load_dotenv()

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

    id: Optional[int] = Field(default=None, primary_key=True)
    user_key: str = Field(unique=True, index=True)          # "web:<identity_id>" lub legacy user_id
    identity_id: Optional[str] = None
    email: Optional[str] = None
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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DailyLogDB(SQLModel, table=True):
    __tablename__ = "daily_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    log_date: str = Field(index=True)           # ISO date string
    food: str = ""
    workout: str = ""
    mood: str = ""
    weight: Optional[float] = None
    logged_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    user: Optional[UserDB] = Relationship(back_populates="logs")

    def to_dict(self) -> dict:
        return {
            "date": self.log_date,
            "food": self.food,
            "workout": self.workout,
            "mood": self.mood,
            "weight": self.weight,
            "logged_at": self.logged_at,
        }


class ExerciseResultDB(SQLModel, table=True):
    """Historyczne wyniki ćwiczeń – serce systemu progresji."""
    __tablename__ = "exercise_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
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

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
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


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="FitAI API", version="2.0")
ai_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
    except Exception:
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
    key = (diet or "").lower()
    if "wega" in key:
        return {
            "Śniadanie": [("Owsianka proteinowa z owocami", 520), ("Tofu scramble + pieczywo", 500), ("Pudding chia + masło orzechowe", 480)],
            "Przekąska 1": [("Shake roślinny + banan", 280), ("Hummus + warzywa", 260), ("Jogurt kokosowy + orzechy", 300)],
            "Obiad": [("Tempeh, ryż, brokuł", 720), ("Makaron z sosem soczewicowym", 690), ("Bowl: tofu, komosa, warzywa", 700)],
            "Przekąska 2": [("Kanapka z pastą z ciecierzycy", 310), ("Mix owoców + migdały", 290), ("Baton roślinny", 260)],
            "Kolacja": [("Sałatka z fasolą i awokado", 520), ("Wrap pełnoziarnisty z tofu", 560), ("Krem z soczewicy", 500)],
        }
    return {
        "Śniadanie": [("Owsianka + odżywka białkowa", 520), ("Jajecznica + pieczywo", 510), ("Skyr + granola + owoce", 480)],
        "Przekąska 1": [("Shake białkowy + banan", 280), ("Serek wiejski + orzechy", 300), ("Jogurt naturalny + owoce", 250)],
        "Obiad": [("Kurczak, ryż, brokuł", 730), ("Indyk, ziemniaki, surówka", 700), ("Łosoś, kasza, warzywa", 750)],
        "Przekąska 2": [("Kanapka z indykiem", 320), ("Twaróg + owoce", 290), ("Baton proteinowy", 260)],
        "Kolacja": [("Sałatka z tuńczykiem", 520), ("Wrap pełnoziarnisty z kurczakiem", 560), ("Omlet warzywny", 500)],
    }


def _exercise_pool() -> dict:
    return {
        "klatka": [
            {"name": "Wyciskanie sztangi leżąc", "sets": "4", "reps": "6-8", "notes": "Łopatki ściągnięte, stopy stabilnie.", "how_to": "Opuszczaj sztangę do dolnej części klatki, prowadząc łokcie około 45 stopni."},
            {"name": "Wyciskanie hantli na skosie", "sets": "3", "reps": "8-10", "notes": "Kontroluj fazę opuszczania.", "how_to": "Ustaw ławkę 30-45 stopni i prowadź hantle po łuku nad klatkę."},
            {"name": "Rozpiętki na bramie", "sets": "3", "reps": "12-15", "notes": "Skup się na napięciu klatki.", "how_to": "Prowadź dłonie półkolem i zatrzymaj ruch na końcu spięcia."},
        ],
        "nogi": [
            {"name": "Przysiad ze sztangą", "sets": "4", "reps": "6-8", "notes": "Neutralny kręgosłup i kontrola kolan.", "how_to": "Cofnij biodra, zejdź do stabilnej głębokości i wróć dynamicznie."},
            {"name": "Rumuński martwy ciąg", "sets": "3", "reps": "8-10", "notes": "Ruch inicjuj biodrem.", "how_to": "Prowadź sztangę blisko nóg, utrzymuj napięty brzuch i prosty grzbiet."},
            {"name": "Wykroki chodzone", "sets": "3", "reps": "10/strona", "notes": "Pilnuj stabilności miednicy.", "how_to": "Długi krok, zejście w dół, odepchnięcie z pięty przedniej nogi."},
        ],
        "plecy": [
            {"name": "Podciąganie nachwytem", "sets": "4", "reps": "6-10", "notes": "Aktywuj łopatki przed ruchem.", "how_to": "Zwis aktywny, podciągnięcie klatki do drążka bez bujania."},
            {"name": "Wiosłowanie hantlem", "sets": "3", "reps": "8-12", "notes": "Łokieć blisko tułowia.", "how_to": "W stabilnym podparciu przyciągaj hantel do biodra i wolno opuszczaj."},
            {"name": "Ściąganie drążka do klatki", "sets": "3", "reps": "10-12", "notes": "Unikaj przeprostu odcinka lędźwiowego.", "how_to": "Prowadź drążek do górnej klatki i kontroluj tor ruchu."},
        ],
        "brzuch": [
            {"name": "Plank", "sets": "3", "reps": "40-60 s", "notes": "Linia bark-biodro-kostka.", "how_to": "Napnij brzuch i pośladki, oddychaj spokojnie, nie unoś bioder."},
            {"name": "Dead bug", "sets": "3", "reps": "10/strona", "notes": "Lędźwia dociśnięte do podłoża.", "how_to": "Opuszczaj naprzemiennie rękę i nogę po przeciwnej stronie."},
            {"name": "Unoszenie nóg w zwisie", "sets": "3", "reps": "8-12", "notes": "Bez bujania.", "how_to": "Unieś nogi przez napięcie brzucha, opuszczaj z kontrolą."},
        ],
        "barki": [
            {"name": "Wyciskanie hantli nad głowę", "sets": "4", "reps": "6-10", "notes": "Brak przeprostu lędźwi.", "how_to": "Prowadź hantle pionowo i kontroluj opuszczanie."},
            {"name": "Unoszenie bokiem", "sets": "3", "reps": "12-15", "notes": "Ruch bez szarpania.", "how_to": "Unieś hantle do poziomu barków z lekkim ugięciem łokci."},
            {"name": "Face pull", "sets": "3", "reps": "12-15", "notes": "Aktywuj tylny akton barków.", "how_to": "Przyciągaj linę do twarzy z rotacją zewnętrzną ramion."},
        ],
    }


def _build_weekly_plan(user: UserDB) -> dict:
    """Builds weekly plan with Carb Cycling macro targets per day.
    On days listed in sport_training_days, a sport drill session replaces the gym workout.
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
    sport_focus = (user.sport_focus or "").lower().strip()           # e.g. "koszykówka"
    sport_spec = (user.sport_specialization or "").lower().strip()   # e.g. "rzuty"
    sport_days = {d.strip() for d in user.get_list("sport_training_days_json")}  # e.g. {"Środa"}

    # Resolve drill list for this user's sport+spec combination
    _sport_drills: List[dict] = []
    if sport_focus and sport_focus in SPORT_DRILLS_DB:
        spec_map = SPORT_DRILLS_DB[sport_focus]
        if sport_spec in spec_map:
            _sport_drills = spec_map[sport_spec]
        elif spec_map:
            # Fallback: first available specialization
            _sport_drills = next(iter(spec_map.values()))

    # Niedziela = dzień odpoczynku
    week_schedule = [
        ("Poniedziałek", False), ("Wtorek", False), ("Środa", False),
        ("Czwartek", False), ("Piątek", False), ("Sobota", False),
        ("Niedziela", True),   # rest day
    ]
    meal_slots = ["Śniadanie", "Przekąska 1", "Obiad", "Przekąska 2", "Kolacja"]
    days = []

    for i, (day_name, is_rest) in enumerate(week_schedule):
        is_sport_day = bool(_sport_drills) and (day_name in sport_days)
        focus_key = "odpoczynek" if is_rest else preferred[i % len(preferred)]
        if focus_key not in pool and not is_rest:
            focus_key = "klatka"

        # Carb Cycling: wyznacz typ dnia i makroskładniki
        day_type = "rest" if is_rest else _day_type(day_name, focus_key)
        macros = calc_daily_macros(base_calories, day_type)

        # ─── Ćwiczenia ────────────────────────────────────────────────────────
        if is_rest:
            workout_items = []
            workout_title = "Odpoczynek / Aktywna regeneracja"
            is_sport_session = False
        elif is_sport_day:
            # Zamień siłownię na sesję drilli sportowych
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
            available_ex = [
                ex for ex in pool[focus_key]
                if not any(a in ex["name"].lower() for a in avoid_exercises)
            ] or pool[focus_key]
            workout_items = []
            for idx, ex in enumerate(available_ex[:4]):
                alts = [a for a in available_ex if a["name"] != ex["name"]]
                other_key = preferred[(i + idx + 1) % len(preferred)]
                if other_key in pool:
                    alts.extend(pool[other_key][:1])
                workout_items.append({**ex, "alternatives": alts[:3]})
            workout_title = f"Sesja {focus_key.title()}"
            is_sport_session = False

        # Posiłki
        meals = []
        for slot in meal_slots:
            candidates = meal_catalog.get(slot, [])
            if preferred_foods:
                pref_c = [c for c in candidates if any(p in c[0].lower() for p in preferred_foods)]
                if pref_c:
                    candidates = pref_c
            if avoid_foods:
                filtered = [c for c in candidates if not any(av in c[0].lower() for av in avoid_foods)]
                candidates = filtered or meal_catalog.get(slot, [])
            main = candidates[i % len(candidates)] if candidates else ("Posiłek", 500)
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



# ─── AI helper ────────────────────────────────────────────────────────────────

def ask_claude(system: str, user_msg: str, max_tokens: int = 800) -> str:
    try:
        message = ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI tymczasowo niedostępne: {exc}") from exc


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

@app.post("/app/exercise-result/{identity_id}")
def log_exercise_result(identity_id: str, payload: ExerciseResultRequest):
    """
    Rejestruje wynik ćwiczenia z oceną RPE.
    Na podstawie historii RPE sugeruje progresję na kolejną sesję.
    """
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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


@app.get("/app/exercise-history/{identity_id}")
def get_exercise_history(identity_id: str, exercise_name: Optional[str] = None, limit: int = 20):
    """Zwraca historię wyników ćwiczeń z sugestią progresji."""
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        query = select(ExerciseResultDB).where(ExerciseResultDB.user_id == user.id)
        if exercise_name:
            query = query.where(ExerciseResultDB.exercise_name == exercise_name)
        results = list(session.exec(query.order_by(ExerciseResultDB.session_date.desc())).all())[:limit]

        data = [r.to_dict() for r in results]
        progression = None
        if exercise_name and results:
            progression = _suggest_progression(exercise_name, results)

        return {"results": data, "progression": progression}


@app.get("/app/progression-summary/{identity_id}")
def get_progression_summary(identity_id: str):
    """Zwraca podsumowanie progresji dla wszystkich ćwiczeń użytkownika."""
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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


@app.get("/app/profile/{identity_id}")
def app_get_profile(identity_id: str):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.user_key == user_key)).first()
        if not user:
            return {
                "name": "", "age": "", "height": "", "weight": "", "target_weight": "",
                "gender": "mężczyzna", "goal": "Redukcja tkanki tłuszczowej",
                "frequency": "3-4 razy w tygodniu", "sports": [], "training_focus": [],
                "improvement_areas": [], "diet": "Brak preferencji", "allergies": "",
                "preferred_foods": [], "avoid_foods": [], "available_equipment": [],
                "avoid_exercises": [], "meals_per_day": 5, "notes": "",
                "plan": "free", "role": "free_user",
            }
        return user.to_profile_dict()


@app.get("/app/dashboard/{identity_id}")
def app_dashboard(identity_id: str):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.user_key == user_key)).first()
        if not user:
            return {"streak_days": 0, "workout_consistency_pct": 0, "targets": {"calories": "-", "protein": "-"}, "weight_series": []}
        logs = _get_user_logs(user, session)
        return _build_dashboard(user, logs)


@app.post("/app/checkin/{identity_id}")
def app_daily_checkin(identity_id: str, log: AppDailyCheckinRequest):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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
        logs = list(session.exec(select(DailyLogDB).where(DailyLogDB.user_id == user.id)).all())
        logs.append(entry)
        user.streak_days = _compute_streak_days_from_logs(logs)
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "log": entry.to_dict(), "streak_days": user.streak_days}


@app.post("/app/link-discord")
def app_link_discord(payload: DiscordLinkRequest):
    user_key = _web_user_key(payload.identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        user.linked_discord_id = payload.discord_user_id
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "linked_discord_id": payload.discord_user_id}


@app.get("/app/reminders/{identity_id}")
def app_get_reminders(identity_id: str):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        return user.get_dict("reminders_json")


@app.post("/app/reminders/{identity_id}")
def app_set_reminders(identity_id: str, prefs: ReminderPrefsRequest):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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


@app.get("/app/plan/{identity_id}")
def app_get_plan(identity_id: str):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.user_key == user_key)).first()
        if not user or not user.weekly_plan_json:
            return {"days": [], "generated_at": None, "weekly_goal": None}
        return user.get_dict("weekly_plan_json")


@app.post("/app/plan/{identity_id}/generate")
def app_generate_plan(identity_id: str, payload: PlanGenerateRequest):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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


@app.post("/app/plan/{identity_id}/swap")
def app_swap_plan_item(identity_id: str, payload: PlanSwapRequest):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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

@app.post("/app/sport-config/{identity_id}")
def set_sport_config(identity_id: str, payload: SportConfigRequest):
    """Konfiguruje moduł sportowy: sport, specjalizacja i dni treningowe."""
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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


@app.get("/app/sport-drills")
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


@app.post("/app/drill-result/{identity_id}")
def log_drill_result(identity_id: str, payload: DrillResultRequest):
    """Zapisuje wynik drilla sportowego i zwraca sugestię progresji."""
    user_key = _web_user_key(identity_id)
    session_date = payload.session_date or date.today().isoformat()

    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)

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


@app.get("/app/drill-history/{identity_id}")
def get_drill_history(identity_id: str, drill_name: Optional[str] = None, limit: int = 20):
    """Pobiera historię wyników drilli dla użytkownika."""
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
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

@app.post("/billing/plan/{identity_id}")
def billing_set_plan(identity_id: str, payload: PlanUpdateRequest):
    user_key = _web_user_key(identity_id)
    with Session(engine) as session:
        user = _get_user_or_404(user_key, session)
        plan = _normalize_plan(payload.plan)
        user.plan = plan
        user.role = _role_for_plan(plan)
        user.updated_at = datetime.now().isoformat()
        session.commit()
        return {"status": "ok", "plan": plan, "role": user.role}


@app.post("/billing/stripe/webhook")
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

@app.post("/ai/diet")
def ai_diet_plan(req: AIRequest):
    with Session(engine) as session:
        user = _get_user_or_404(req.user_id, session)
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


@app.post("/ai/workout")
def ai_workout_plan(req: AIRequest):
    with Session(engine) as session:
        user = _get_user_or_404(req.user_id, session)
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


@app.post("/ai/analyze-log")
def ai_analyze_log(req: AIRequest):
    with Session(engine) as session:
        user = _get_user_or_404(req.user_id, session)
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


@app.post("/ai/weekly")
def ai_weekly_summary(req: AIRequest):
    with Session(engine) as session:
        user = _get_user_or_404(req.user_id, session)
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


# ─── Version & root ───────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "FitAI API", "version": "2.0.0", "docs": "/docs", "status": "running"}


@app.get("/app/version")
def get_version():
    try:
        with open("package.json", "r") as f:
            version = json.load(f).get("version", "2.0.0")
    except Exception:
        version = "2.0.0"
    return {"version": version, "build_date": datetime.now().strftime("%Y-%m-%d"), "api_version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)