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

from fastapi import FastAPI, HTTPException
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

app = FastAPI(title="FitAI API", version="1.0.0")
ai_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    if origin.strip()
]

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
