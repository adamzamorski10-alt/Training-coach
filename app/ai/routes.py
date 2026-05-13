"""
AI Routes — Diet plans, workout suggestions, weekly analysis
"""

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from sqlmodel import Session, select

from app.auth import get_current_user, _rate_limit_key
from app.ai.service import ask_ai, AIError, fallback_diet_plan, fallback_workout_plan
from app.config import AI_RATE_PER_HOUR, AI_RATE_PER_MINUTE
from app.database import engine
from app.fitness.calculations import calc_calories, calc_daily_macros, day_type, day_type_label
from app.models import DailyLogDB, ExerciseResultDB, UserDB
from app.schemas import AIRequest

router = APIRouter(prefix="/ai", tags=["ai"])
limiter = Limiter(key_func=_rate_limit_key)


@router.post("/diet")
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_diet_plan(
    request: Request,
    req: AIRequest,
    user: UserDB = Depends(get_current_user),
):
    """Generate personalized diet plan based on user profile, macros, and preferences."""
    with Session(engine) as session:
        kcal = user.calories_target or calc_calories(user)
        day_of_week = datetime.now().strftime("%A")

        # Wyznacz typ dnia i makro carb cycling
        focus = user.get_list("training_focus_json")
        day_type_key = day_type(day_of_week, focus[0].lower() if focus else "klatka")
        macros = calc_daily_macros(kcal, day_type_key)

        system = (
            "Jesteś dietetykiem sportowym. Piszesz po polsku. "
            "Tworzysz konkretne, zróżnicowane i zdrowe plany posiłków z dokładną gramaturą."
        )
        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Typ dnia (carb cycling): {day_type_label(day_type_key)}\n"
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
            result = ask_ai(system, user_msg, 1000)
            if isinstance(result, AIError):
                return {
                    "plan": fallback_diet_plan(macros["kcal"], macros["protein_g"]),
                    "calories_target": kcal,
                    "protein_target": user.protein_target,
                    "macros": macros,
                    "fallback": True,
                }
            return {
                "plan": result,
                "calories_target": kcal,
                "protein_target": user.protein_target,
                "macros": macros,
            }
        except Exception as exc:
            return {
                "plan": fallback_diet_plan(macros["kcal"], macros["protein_g"]),
                "calories_target": kcal,
                "protein_target": user.protein_target,
                "macros": macros,
                "fallback": True,
            }


@router.post("/workout")
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_workout_plan(
    request: Request,
    req: AIRequest,
    user: UserDB = Depends(get_current_user),
):
    """Generate personalized workout plan based on user profile and progression history."""
    with Session(engine) as session:
        logs = list(
            session.exec(
                select(DailyLogDB)
                .where(DailyLogDB.user_id == user.id)
                .order_by(DailyLogDB.log_date.desc())
            ).all()
        )[:7]
        recent_workouts = [l.workout for l in logs if l.workout]

        # Pobierz dane progresji dla AI
        ex_results = list(
            session.exec(
                select(ExerciseResultDB)
                .where(ExerciseResultDB.user_id == user.id)
                .order_by(ExerciseResultDB.session_date.desc())
            ).all()
        )[:30]

        day = datetime.now().strftime("%A")
        system = (
            "Jesteś doświadczonym trenerem personalnym. Piszesz po polsku. "
            "Tworzysz efektywne i bezpieczne plany treningowe z progresją obciążenia."
        )
        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Dzień tygodnia: {day}\n"
            f"Ostatnie treningi (7 dni): {', '.join(recent_workouts) if recent_workouts else 'brak'}\n"
            f"Historia ćwiczeń (30 dni): {len(ex_results)} wpisów\n"
            f"Kontekst: {req.extra_context or 'brak'}\n\n"
            "Utwórz plan treningowy na DZIŚ — nazwa sesji, 5-6 ćwiczeń z seriami, "
            "powtórzeniami i wskazówkami technicznymi. "
            f"Cel: {user.goal}, sporty: {', '.join(user.get_list('sports_json'))}"
        )
        try:
            result = ask_ai(system, user_msg, 900)
            if isinstance(result, AIError):
                return {
                    "plan": fallback_workout_plan(user.goal),
                    "fallback": True,
                }
            return {"plan": result}
        except Exception as exc:
            return {
                "plan": fallback_workout_plan(user.goal),
                "fallback": True,
            }


@router.post("/weekly")
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def ai_weekly_analysis(
    request: Request,
    req: AIRequest,
    user: UserDB = Depends(get_current_user),
):
    """Generate weekly analysis and recommendations."""
    with Session(engine) as session:
        week_ago = (datetime.now().date() - __import__("datetime").timedelta(days=7)).isoformat()
        week_logs = list(
            session.exec(
                select(DailyLogDB)
                .where(DailyLogDB.user_id == user.id)
                .where(DailyLogDB.log_date >= week_ago)
                .order_by(DailyLogDB.log_date.asc())
            ).all()
        )

        system = (
            "Jesteś osobistym asystentem fitness. Piszesz po polsku. "
            "Analizujesz tygodnie i tworzysz konkretne plany na kolejny tydzień."
        )
        
        week_summary = {
            "days_logged": len(week_logs),
            "workouts": len([l for l in week_logs if l.workout]),
            "avg_mood": sum(
                int(l.mood.split("/")[0]) if "/" in str(l.mood) else 5
                for l in week_logs if l.mood
            ) / max(len([l for l in week_logs if l.mood]), 1),
        }

        user_msg = (
            f"Profil: {json.dumps(user.to_profile_dict(), ensure_ascii=False)}\n"
            f"Statystyka ostatniego tygodnia:\n"
            f"- Dni z logami: {week_summary['days_logged']}/7\n"
            f"- Treningi: {week_summary['workouts']}\n"
            f"- Średni nastrój: {week_summary['avg_mood']:.1f}/10\n"
            f"\nKontekst: {req.extra_context or 'brak'}\n\n"
            "Oceń ostatni tydzień i podaj KONKRETNY plan na następny tydzień z fokusem na cele użytkownika."
        )
        
        try:
            result = ask_ai(system, user_msg, 1000)
            if isinstance(result, AIError):
                return {
                    "analysis": "AI niedostępne. Spróbuj ponownie za chwilę.",
                    "week_stats": week_summary,
                    "fallback": True,
                }
            return {
                "analysis": result,
                "week_stats": week_summary,
            }
        except Exception as exc:
            return {
                "analysis": "AI niedostępne. Spróbuj ponownie za chwilę.",
                "week_stats": week_summary,
                "fallback": True,
            }
