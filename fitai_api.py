"""
FitAI Backend API — FastAPI
============================
Wymagania: pip install fastapi uvicorn anthropic python-dotenv pydantic

Uruchomienie: uvicorn fitai_api:app --reload --port 8000

Endpointy:
  POST /users/           - Utwórz/zaktualizuj profil
  GET  /users/{id}       - Pobierz profil
  POST /users/{id}/logs  - Dodaj dzienny raport
  GET  /users/{id}/logs  - Pobierz historię
  POST /ai/diet          - AI plan diety
  POST /ai/workout       - AI plan treningowy
  POST /ai/analyze-log   - AI analiza raportu
  POST /ai/weekly        - AI podsumowanie tygodnia
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import json
import anthropic
import os
from dotenv import load_dotenv
from fitai_utils import load_db, save_db, calc_calories, calc_protein, _load_db_unlocked, _save_db_unlocked, DB_LOCK

load_dotenv()

app = FastAPI(title="FitAI API", version="1.01")
ai_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Permisywny CORS dla development i Netlify production
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://training-coach-app.netlify.app",
    "https://training-coach-api.onrender.com",
]
# Dodaj custom origins z .env jeśli są dostępne
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


# ─── Modele danych ────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    name: str
    age: int
    height: float  # cm
    weight: float  # kg
    target_weight: float
    gender: str  # mężczyzna / kobieta / inna
    goal: str
    frequency: str  # jak często trenuje
    sports: List[str] = []
    diet: str  # rodzaj diety
    allergies: str = ""
    preferred_foods: List[str] = []  # ulubione produkty
    avoid_foods: List[str] = []  # rzeczy do unikania w diecie
    available_equipment: List[str] = []  # dostępny sprzęt
    avoid_exercises: List[str] = []  # rzeczy do unikania w treningu
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


def _web_user_id(identity_id: str) -> str:
    return f"web:{identity_id}"


def _normalize_plan(plan_raw: str) -> str:
    plan = (plan_raw or "").strip().lower()
    if plan in {"pro", "premium", "paid"}:
        return "pro"
    return "free"


def _role_for_plan(plan: str) -> str:
    return "pro_user" if plan == "pro" else "free_user"


def _compute_streak_days(logs: List[dict]) -> int:
    if not logs:
        return 0

    unique_days = sorted(
        {
            l.get("date")
            for l in logs
            if l.get("date")
        },
        reverse=True,
    )
    if not unique_days:
        return 0

    streak = 0
    expected_day = date.today()
    for day_str in unique_days:
        try:
            day_obj = date.fromisoformat(day_str)
        except ValueError:
            continue

        if day_obj == expected_day:
            streak += 1
            expected_day = expected_day.fromordinal(expected_day.toordinal() - 1)
        elif day_obj < expected_day:
            break
    return streak


def _build_dashboard(profile: dict) -> dict:
    logs = sorted(profile.get("logs", []), key=lambda x: x.get("date", ""))
    calories_target = profile.get("calories_target", calc_calories(profile))
    protein_target = profile.get("protein_target", calc_protein(profile))

    weight_points = [
        {"date": l.get("date"), "weight": l.get("weight")}
        for l in logs
        if l.get("weight") is not None
    ][-30:]

    last_7 = logs[-7:]
    workout_days = sum(1 for l in last_7 if l.get("workout"))
    consistency = round((workout_days / 7) * 100) if last_7 else 0

    # Prosty estimate realizacji na podstawie opisu jedzenia.
    calorie_hit = 0
    protein_hit = 0
    for l in last_7:
        food_text = (l.get("food") or "").lower()
        if any(k in food_text for k in ["kurczak", "jaj", "twar", "protein", "ryba", "indyk"]):
            protein_hit += 1
        if food_text:
            calorie_hit += 1

    calorie_adherence = round((calorie_hit / len(last_7)) * 100) if last_7 else 0
    protein_adherence = round((protein_hit / len(last_7)) * 100) if last_7 else 0

    return {
        "weight_series": weight_points,
        "workout_consistency_pct": consistency,
        "calorie_adherence_pct": calorie_adherence,
        "protein_adherence_pct": protein_adherence,
        "streak_days": _compute_streak_days(logs),
        "targets": {
            "calories": calories_target,
            "protein": protein_target,
        },
    }


def _is_profile_ready_for_plan(profile: dict) -> bool:
    required = [profile.get("name"), profile.get("goal"), profile.get("frequency"), profile.get("diet"), profile.get("weight"), profile.get("target_weight")]
    return all(v not in (None, "") for v in required)


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


def _build_weekly_plan(profile: dict) -> dict:
    meal_catalog = _default_meal_catalog(profile.get("diet", "Brak preferencji"))
    pool = _exercise_pool()
    
    # Preferowane partie treningowe
    focus = [x.lower() for x in profile.get("training_focus", []) if isinstance(x, str)]
    improve = [x.lower() for x in profile.get("improvement_areas", []) if isinstance(x, str)]
    preferred = focus + [x for x in improve if x not in focus]
    if not preferred:
        preferred = ["klatka", "plecy", "nogi", "brzuch", "barki"]

    # Personalizacja: ulubione produkty i sprzęt dostępny
    preferred_foods = [x.lower() for x in profile.get("preferred_foods", []) if isinstance(x, str)]
    avoid_foods = [x.lower() for x in profile.get("avoid_foods", []) if isinstance(x, str)]
    available_equipment = [x.lower() for x in profile.get("available_equipment", []) if isinstance(x, str)]
    avoid_exercises = [x.lower() for x in profile.get("avoid_exercises", []) if isinstance(x, str)]

    week_days = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    meal_slots = ["Śniadanie", "Przekąska 1", "Obiad", "Przekąska 2", "Kolacja"]
    days = []

    for i, day_name in enumerate(week_days):
        focus_key = preferred[i % len(preferred)]
        if focus_key not in pool:
            focus_key = "klatka"

        # Filtruj ćwiczenia: usuń te, które są w avoid_exercises
        available_exercises = [
            ex for ex in pool[focus_key] 
            if not any(avoid.lower() in ex["name"].lower() for avoid in avoid_exercises)
        ]
        if not available_exercises:
            available_exercises = pool[focus_key]

        workout_items = []
        for idx, ex in enumerate(available_exercises[:4]):  # Max 4 ćwiczenia
            alternatives = [
                alt for alt in available_exercises 
                if alt["name"] != ex["name"]
            ]
            other_key = preferred[(i + idx + 1) % len(preferred)]
            if other_key in pool:
                alternatives.extend(pool[other_key][:1])
            workout_items.append({**ex, "alternatives": alternatives[:3]})

        # Filtruj posiłki: preferuj ulubione produkty, unikaj avoid_foods
        meals = []
        for slot in meal_slots:
            candidates = meal_catalog.get(slot, [])
            
            # Jeśli mamy preferowane produkty, spróbuj ich użyć
            if preferred_foods:
                preferred_candidates = [c for c in candidates if any(p in c[0].lower() for p in preferred_foods)]
                if preferred_candidates:
                    candidates = preferred_candidates
            
            # Filtruj rzeczy do unikania
            if avoid_foods:
                candidates = [c for c in candidates if not any(avoid.lower() in c[0].lower() for avoid in avoid_foods)]
                if not candidates:
                    candidates = meal_catalog.get(slot, [])  # Jeśli wszystko odfiltrowane, przywróć
            
            main = candidates[i % len(candidates)] if candidates else ("Posiłek", 500)
            alt = [{"name": c[0], "kcal": c[1]} for c in candidates if c[0] != main[0]][:3]
            meals.append({"slot": slot, "name": main[0], "kcal": main[1], "alternatives": alt})

        days.append({
            "day": day_name,
            "workout": {"title": f"Sesja {focus_key.title()}", "focus": focus_key, "exercises": workout_items},
            "meals": meals,
        })

    return {"generated_at": datetime.now().isoformat(), "weekly_goal": profile.get("goal", "Poprawa formy"), "days": days}


# ─── AI helper ────────────────────────────────────────────────────────────────

def ask_claude(system: str, user_msg: str, max_tokens: int = 800) -> str:
    try:
        message = ai_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI temporarily unavailable: {exc}") from exc


# ─── Endpointy użytkowników ───────────────────────────────────────────────────

@app.post("/users/{user_id}")
def create_or_update_user(user_id: str, profile: UserProfile):
    with DB_LOCK:
        db = _load_db_unlocked()
        existing = db.get(user_id, {})
        updated = {
            **existing,
            **profile.model_dump(),
            "start_weight": existing.get("start_weight", profile.weight),
            "created_at": existing.get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "logs": existing.get("logs", []),
        }
        updated["calories_target"] = calc_calories(updated)
        updated["protein_target"] = calc_protein(updated)
        db[user_id] = updated
        _save_db_unlocked(db)
    return {"status": "ok", "user_id": user_id, "calories_target": updated["calories_target"]}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    db = load_db()
    if user_id not in db:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    return db[user_id]


@app.post("/users/{user_id}/logs")
def add_log(user_id: str, log: DailyLog):
    with DB_LOCK:
        db = _load_db_unlocked()
        if user_id not in db:
            raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")

        profile = db[user_id]
        log_entry = {
            "date": date.today().isoformat(),
            "food": log.food,
            "workout": log.workout,
            "mood": log.mood,
            "weight": log.weight,
            "logged_at": datetime.now().isoformat(),
        }

        if "logs" not in profile:
            profile["logs"] = []

        # Zamień jeśli już jest log na dziś
        today = date.today().isoformat()
        profile["logs"] = [l for l in profile["logs"] if l.get("date") != today]
        profile["logs"].append(log_entry)

        if log.weight is not None:
            profile["weight"] = log.weight
            profile["calories_target"] = calc_calories(profile)
            profile["protein_target"] = calc_protein(profile)

        db[user_id] = profile
        _save_db_unlocked(db)
    return {"status": "ok", "log": log_entry}


@app.get("/users/{user_id}/logs")
def get_logs(user_id: str, limit: int = 30):
    db = load_db()
    if user_id not in db:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    logs = db[user_id].get("logs", [])
    return {"logs": sorted(logs, key=lambda x: x["date"], reverse=True)[:limit]}


@app.post("/app/onboarding")
def app_onboarding(payload: AppOnboardingRequest):
    user_id = _web_user_id(payload.identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        existing = db.get(user_id, {})
        logs = existing.get("logs", [])
        plan = _normalize_plan(existing.get("plan", "free"))

        updated = {
            **existing,
            **payload.model_dump(),
            "email": payload.email,
            "identity_id": payload.identity_id,
            "name": payload.name,
            "start_weight": existing.get("start_weight", payload.weight),
            "created_at": existing.get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "plan": plan,
            "role": _role_for_plan(plan),
            "logs": logs,
            "linked_discord_id": existing.get("linked_discord_id"),
            "reminders": existing.get(
                "reminders",
                {
                    "email_enabled": True,
                    "discord_enabled": False,
                    "discord_channel_id": None,
                },
            ),
        }
        updated["calories_target"] = calc_calories(updated)
        updated["protein_target"] = calc_protein(updated)
        updated["streak_days"] = _compute_streak_days(updated["logs"])
        db[user_id] = updated
        _save_db_unlocked(db)
    return {
        "status": "ok",
        "user_id": user_id,
        "plan": updated["plan"],
        "role": updated["role"],
    }


@app.get("/app/profile/{identity_id}")
def app_get_profile(identity_id: str):
    user_id = _web_user_id(identity_id)
    db = load_db()
    profile = db.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
    return profile


@app.get("/app/dashboard/{identity_id}")
def app_dashboard(identity_id: str):
    user_id = _web_user_id(identity_id)
    db = load_db()
    profile = db.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
    return _build_dashboard(profile)


@app.post("/app/checkin/{identity_id}")
def app_daily_checkin(identity_id: str, log: AppDailyCheckinRequest):
    user_id = _web_user_id(identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")

        today = date.today().isoformat()
        log_entry = {
            "date": today,
            "food": log.food,
            "workout": log.workout,
            "mood": log.mood,
            "weight": log.weight,
            "logged_at": datetime.now().isoformat(),
        }

        profile_logs = profile.get("logs", [])
        profile_logs = [l for l in profile_logs if l.get("date") != today]
        profile_logs.append(log_entry)
        profile["logs"] = profile_logs

        if log.weight is not None:
            profile["weight"] = log.weight
            profile["calories_target"] = calc_calories(profile)
            profile["protein_target"] = calc_protein(profile)

        profile["updated_at"] = datetime.now().isoformat()
        profile["streak_days"] = _compute_streak_days(profile_logs)
        db[user_id] = profile
        _save_db_unlocked(db)

    return {
        "status": "ok",
        "log": log_entry,
        "streak_days": profile["streak_days"],
    }


@app.post("/app/link-discord")
def app_link_discord(payload: DiscordLinkRequest):
    user_id = _web_user_id(payload.identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")

        profile["linked_discord_id"] = payload.discord_user_id
        profile["updated_at"] = datetime.now().isoformat()
        db[user_id] = profile
        _save_db_unlocked(db)

    return {
        "status": "ok",
        "linked_discord_id": payload.discord_user_id,
    }


@app.get("/app/reminders/{identity_id}")
def app_get_reminders(identity_id: str):
    user_id = _web_user_id(identity_id)
    db = load_db()
    profile = db.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
    return profile.get(
        "reminders",
        {
            "email_enabled": True,
            "discord_enabled": False,
            "discord_channel_id": None,
        },
    )


@app.post("/app/reminders/{identity_id}")
def app_set_reminders(identity_id: str, prefs: ReminderPrefsRequest):
    user_id = _web_user_id(identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")

        profile["reminders"] = prefs.model_dump()
        profile["updated_at"] = datetime.now().isoformat()
        db[user_id] = profile
        _save_db_unlocked(db)

    return {"status": "ok", "reminders": prefs.model_dump()}


@app.post("/billing/plan/{identity_id}")
def billing_set_plan(identity_id: str, payload: PlanUpdateRequest):
    user_id = _web_user_id(identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")

        plan = _normalize_plan(payload.plan)
        profile["plan"] = plan
        profile["role"] = _role_for_plan(plan)
        profile["updated_at"] = datetime.now().isoformat()
        db[user_id] = profile
        _save_db_unlocked(db)

    return {"status": "ok", "plan": plan, "role": profile["role"]}


@app.post("/billing/stripe/webhook")
async def stripe_webhook(request: Request):
    # Uproszczony webhook: expects JSON payload with identity_id and plan.
    # Verification should be handled at edge function level before forwarding.
    payload = await request.json()
    identity_id = payload.get("identity_id")
    if not identity_id:
        raise HTTPException(status_code=400, detail="Brak identity_id")

    plan = _normalize_plan(payload.get("plan", "free"))
    user_id = _web_user_id(identity_id)

    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
        profile["plan"] = plan
        profile["role"] = _role_for_plan(plan)
        profile["updated_at"] = datetime.now().isoformat()
        db[user_id] = profile
        _save_db_unlocked(db)

    return {"status": "ok", "plan": plan, "role": profile["role"]}


@app.get("/app/reminders-due")
def app_reminders_due():
    db = load_db()
    today = date.today().isoformat()
    due = []
    for user_id, profile in db.items():
        if not user_id.startswith("web:"):
            continue
        reminders = profile.get("reminders", {})
        if not reminders.get("email_enabled") and not reminders.get("discord_enabled"):
            continue

        logs = profile.get("logs", [])
        has_today_log = any(l.get("date") == today for l in logs)
        if has_today_log:
            continue

        due.append(
            {
                "user_id": user_id,
                "email": profile.get("email"),
                "linked_discord_id": profile.get("linked_discord_id"),
                "reminders": reminders,
                "streak_days": profile.get("streak_days", 0),
            }
        )

    return {"due": due, "count": len(due)}


@app.get("/app/plan/{identity_id}")
def app_get_plan(identity_id: str):
    user_id = _web_user_id(identity_id)
    db = load_db()
    profile = db.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
    plan = profile.get("weekly_plan")
    if not plan:
        raise HTTPException(status_code=404, detail="Plan nie został jeszcze wygenerowany")
    return plan


@app.post("/app/plan/{identity_id}/generate")
def app_generate_plan(identity_id: str, payload: PlanGenerateRequest):
    user_id = _web_user_id(identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
        if not _is_profile_ready_for_plan(profile):
            raise HTTPException(status_code=400, detail="Najpierw uzupełnij pełny onboarding")
        if payload.force or not profile.get("weekly_plan"):
            profile["weekly_plan"] = _build_weekly_plan(profile)
            profile["updated_at"] = datetime.now().isoformat()
            db[user_id] = profile
            _save_db_unlocked(db)
    return {"status": "ok", "plan": profile.get("weekly_plan")}


@app.post("/app/plan/{identity_id}/swap")
def app_swap_plan_item(identity_id: str, payload: PlanSwapRequest):
    user_id = _web_user_id(identity_id)
    with DB_LOCK:
        db = _load_db_unlocked()
        profile = db.get(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profil onboarding nie istnieje")
        plan = profile.get("weekly_plan")
        if not plan:
            raise HTTPException(status_code=404, detail="Plan nie został jeszcze wygenerowany")

        days = plan.get("days", [])
        if payload.day_index < 0 or payload.day_index >= len(days):
            raise HTTPException(status_code=400, detail="Niepoprawny day_index")
        day = days[payload.day_index]
        section = (payload.section or "").strip().lower()

        if section == "meal":
            meals = day.get("meals", [])
            if payload.item_index < 0 or payload.item_index >= len(meals):
                raise HTTPException(status_code=400, detail="Niepoprawny item_index dla meal")
            item = meals[payload.item_index]
            alternatives = item.get("alternatives", [])
            if payload.alternative_index < 0 or payload.alternative_index >= len(alternatives):
                raise HTTPException(status_code=400, detail="Niepoprawny alternative_index")
            current = {"name": item.get("name"), "kcal": item.get("kcal")}
            selected = alternatives[payload.alternative_index]
            item["name"] = selected.get("name")
            item["kcal"] = selected.get("kcal")
            new_alt = [a for i, a in enumerate(alternatives) if i != payload.alternative_index]
            new_alt.append(current)
            item["alternatives"] = new_alt
        elif section == "exercise":
            exercises = day.get("workout", {}).get("exercises", [])
            if payload.item_index < 0 or payload.item_index >= len(exercises):
                raise HTTPException(status_code=400, detail="Niepoprawny item_index dla exercise")
            item = exercises[payload.item_index]
            alternatives = item.get("alternatives", [])
            if payload.alternative_index < 0 or payload.alternative_index >= len(alternatives):
                raise HTTPException(status_code=400, detail="Niepoprawny alternative_index")
            selected = alternatives[payload.alternative_index]
            current = {"name": item.get("name"), "sets": item.get("sets"), "reps": item.get("reps"), "notes": item.get("notes"), "how_to": item.get("how_to")}
            item["name"] = selected.get("name")
            item["sets"] = selected.get("sets")
            item["reps"] = selected.get("reps")
            item["notes"] = selected.get("notes")
            item["how_to"] = selected.get("how_to")
            new_alt = [a for i, a in enumerate(alternatives) if i != payload.alternative_index]
            new_alt.append(current)
            item["alternatives"] = new_alt
        else:
            raise HTTPException(status_code=400, detail="section musi być meal albo exercise")
        profile["weekly_plan"] = plan
        profile["updated_at"] = datetime.now().isoformat()
        db[user_id] = profile
        _save_db_unlocked(db)
    return {"status": "ok", "plan": profile.get("weekly_plan")}


# ─── AI endpointy ─────────────────────────────────────────────────────────────

@app.post("/ai/diet")
def ai_diet_plan(req: AIRequest):
    db = load_db()
    if req.user_id not in db:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    profile = db[req.user_id]
    kcal = calc_calories(profile)
    protein = calc_protein(profile)

    system = (
        "Jesteś dietetykiem sportowym. Piszesz po polsku. "
        "Tworzysz konkretne, zróżnicowane i zdrowe plany posiłków z dokładną gramaturą."
    )
    day = datetime.now().strftime("%A")
    user_msg = (
        f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Docelowe kalorie: {kcal} kcal, białko: {protein}g, "
        f"tłuszcze: {int(kcal*0.25/9)}g, węglowodany: {int(kcal*0.45/4)}g\n"
        f"Dzień: {day}\n"
        f"Dieta: {profile.get('diet', 'brak preferencji')}, "
        f"alergie: {profile.get('allergies', 'brak')}\n"
        f"Posiłków dziennie: {profile.get('meals_per_day', 4)}\n\n"
        f"Kontekst dodatkowy: {req.extra_context or 'brak'}\n\n"
        "Utwórz szczegółowy plan diety na DZIŚ z godzinami, pełnymi nazwami produktów, "
        "gramaturą i kaloriami każdego posiłku. Na końcu łączne makroskładniki."
    )
    response = ask_claude(system, user_msg, max_tokens=1000)
    return {"plan": response, "calories_target": kcal, "protein_target": protein}


@app.post("/ai/workout")
def ai_workout_plan(req: AIRequest):
    db = load_db()
    if req.user_id not in db:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    profile = db[req.user_id]

    recent_workouts = [
        l.get("workout", "")
        for l in profile.get("logs", [])[-7:]
        if l.get("workout")
    ]
    day = datetime.now().strftime("%A")
    system = (
        "Jesteś doświadczonym trenerem personalnym. Piszesz po polsku. "
        "Tworzysz efektywne i bezpieczne plany treningowe."
    )
    user_msg = (
        f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Dzień tygodnia: {day}\n"
        f"Ostatnie treningi (7 dni): {chr(10).join(recent_workouts) or 'brak danych'}\n"
        f"Kontekst: {req.extra_context or 'brak'}\n\n"
        "Utwórz plan treningowy na DZIŚ — nazwa sesji, 5-6 ćwiczeń z seriami, "
        "powtórzeniami, obciążeniem (% 1RM lub konkretne) i wskazówkami technicznymi. "
        "Unikaj partii zmęczonych z ostatnich dni. "
        f"Cel: {profile.get('goal', '?')}, sporty: {', '.join(profile.get('sports', []))}"
    )
    response = ask_claude(system, user_msg, max_tokens=900)
    return {"plan": response}


@app.post("/ai/analyze-log")
def ai_analyze_log(req: AIRequest):
    db = load_db()
    if req.user_id not in db:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    profile = db[req.user_id]
    logs = profile.get("logs", [])
    today_log = next((l for l in reversed(logs) if l.get("date") == date.today().isoformat()), None)

    if not today_log:
        raise HTTPException(status_code=400, detail="Brak raportu na dziś")

    kcal = calc_calories(profile)
    system = (
        "Jesteś osobistym asystentem fitness. Piszesz po polsku. "
        "Analizujesz raporty i tworzysz konkretne plany na kolejny dzień."
    )
    user_msg = (
        f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Docelowe kalorie: {kcal} kcal\n\n"
        f"Raport z dziś:\n"
        f"- Co jadłem: {today_log.get('food', 'nie podano')}\n"
        f"- Trening: {today_log.get('workout', 'nie podano')}\n"
        f"- Samopoczucie: {today_log.get('mood', 'nie podano')}\n"
        f"- Waga: {today_log.get('weight', 'nie podano')} kg\n\n"
        "Oceń dzień (kalorie, jakość treningu, postęp do celu) i podaj KONKRETNY plan na jutro: "
        "lista 4 posiłków z kaloriami + opis treningu. Uwzględnij zmęczenie/ból z raportu. Max 400 słów."
    )
    response = ask_claude(system, user_msg, max_tokens=1000)
    return {"analysis": response}


@app.post("/ai/weekly")
def ai_weekly_summary(req: AIRequest):
    db = load_db()
    if req.user_id not in db:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    profile = db[req.user_id]
    week_logs = profile.get("logs", [])[-7:]

    system = (
        "Jesteś analitykiem fitness. Piszesz po polsku. "
        "Tworzysz motywujące ale realistyczne podsumowania tygodniowe."
    )
    user_msg = (
        f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Logi z ostatnich 7 dni: {json.dumps(week_logs, ensure_ascii=False)}\n\n"
        "Podaj tygodniowe podsumowanie: "
        "1) Krótka ocena tygodnia (co szło dobrze, co źle), "
        "2) Postęp do celu, "
        "3) Top 3 konkretne rekomendacje na następny tydzień (dieta + trening). "
        "Max 300 słów. Bądź motywujący."
    )
    response = ask_claude(system, user_msg, max_tokens=800)
    return {"summary": response}


@app.get("/")
def root():
    return {
        "name": "FitAI API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/app/version")
def get_version():
    """Zwraca wersję i datę ostatniego updateu"""
    import json
    from datetime import datetime
    
    try:
        with open("package.json", "r") as f:
            pkg = json.load(f)
        version = pkg.get("version", "1.0.0")
    except:
        version = "1.0.0"
    
    return {
        "version": version,
        "build_date": datetime.now().strftime("%Y-%m-%d"),
        "api_version": "1.02",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
