"""
Fitness Routes — Profile, dashboard, daily checkin, exercise/drill logging
"""

import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.config import (
    _XP_CHECKIN,
    _XP_MEAL_LOGGED,
    _XP_STREAK_BONUS,
    _XP_WEIGHT_LOGGED,
    _XP_WORKOUT_LOGGED,
)
from app.database import engine, get_session
from app.fitness.calculations import (
    _XP_WATER_LOGGED,
    _xp_to_next_level,
    award_xp,
    calc_calories,
    calc_protein,
    calc_daily_macros,
    day_type,
    day_type_label,
    suggest_drill_progression,
    suggest_progression,
)
from app.fitness.dashboard import (
    build_dashboard,
    compute_streak_days_from_logs,
    get_user_logs,
)
from app.models import DailyLogDB, DrillResultDB, ExerciseResultDB, UserDB
from app.schemas import (
    AppDailyCheckinRequest,
    AppOnboardingRequest,
    DrillResultRequest,
    ExerciseResultRequest,
    NicknameChangeRequest,
    ProfileUpdateRequest,
    SportConfigRequest,
    WaterLogRequest,
)
from app.fitness.utils import upsert_user_from_profile

router = APIRouter(prefix="/app", tags=["fitness"])


class NicknameChangeRequest(BaseModel):
    new_nickname: str


_DAY_LABELS_PL = {0: "Pon", 1: "Wt", 2: "Śr", 3: "Czw", 4: "Pt", 5: "Sob", 6: "Niedz"}
_DAY_FULL_NAMES_PL = {
    0: "Poniedziałek",
    1: "Wtorek",
    2: "Środa",
    3: "Czwartek",
    4: "Piątek",
    5: "Sobota",
    6: "Niedziela",
}


def _web_user_key(identity_id: str) -> str:
    return f"web:{identity_id}"


def _round_float(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(float(value), 1)


def _planned_items_count(day_plan) -> int:
    if isinstance(day_plan, list):
        return len(day_plan)
    if isinstance(day_plan, dict):
        total = 0
        for item in day_plan.values():
            total += _planned_items_count(item) if isinstance(item, (list, dict)) else int(bool(item))
        return total
    return 0


def _daily_log_has_data(log: DailyLogDB) -> bool:
    return any([
        bool((log.food or "").strip()),
        bool((log.workout or "").strip()),
        bool((log.mood or "").strip()),
        log.weight is not None,
        log.water_liters is not None,
        log.sleep_hours is not None,
        log.sleep_quality is not None,
        log.energy_level is not None,
        log.stress_level is not None,
        log.mood_score is not None,
        log.rpe is not None,
        log.meals_eaten is not None,
        log.workouts_done is not None,
        bool((log.notes or "").strip()),
    ])


def _latest_non_null(logs: list[DailyLogDB], field_name: str):
    for log in sorted(logs, key=lambda item: item.logged_at, reverse=True):
        value = getattr(log, field_name, None)
        if value is not None:
            return value
    return None


def _safe_weekly_plan(weekly_plan_json: Optional[str]) -> dict:
    try:
        return json.loads(weekly_plan_json or "{}") if weekly_plan_json else {}
    except json.JSONDecodeError:
        return {}


@router.get("/weekly-analysis")
def get_weekly_analysis(
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Zwraca spójny tygodniowy przegląd wszystkich modułów użytkownika."""
    try:
        today = date.today()
        week_start = today - timedelta(days=6)

        daily_logs = list(
            session.exec(
                select(DailyLogDB)
                .where(DailyLogDB.user_id == user.id)
                .where(DailyLogDB.log_date >= week_start)
                .where(DailyLogDB.log_date <= today)
                .order_by(DailyLogDB.log_date)
            ).all()
        )
        exercise_results = list(
            session.exec(
                select(ExerciseResultDB)
                .where(ExerciseResultDB.user_id == user.id)
                .where(ExerciseResultDB.session_date >= week_start)
                .where(ExerciseResultDB.session_date <= today)
                .order_by(ExerciseResultDB.session_date)
            ).all()
        )
        drill_results = list(
            session.exec(
                select(DrillResultDB)
                .where(DrillResultDB.user_id == user.id)
                .where(DrillResultDB.session_date >= week_start)
                .where(DrillResultDB.session_date <= today)
                .order_by(DrillResultDB.session_date)
            ).all()
        )
        weekly_plan = _safe_weekly_plan(user.weekly_plan_json)
        training_plan = weekly_plan.get("training", {}) if isinstance(weekly_plan, dict) else {}

        daily_logs_by_date: dict[date, list[DailyLogDB]] = {}
        for log in daily_logs:
            daily_logs_by_date.setdefault(log.log_date, []).append(log)

        exercise_by_date: dict[date, list[ExerciseResultDB]] = {}
        for result in exercise_results:
            exercise_by_date.setdefault(result.session_date, []).append(result)

        drill_by_date: dict[date, list[DrillResultDB]] = {}
        for result in drill_results:
            drill_by_date.setdefault(result.session_date, []).append(result)

        days_list = []
        all_rpe_values: list[float] = []
        weight_points: list[float] = []

        for offset in range(7):
            current_date = week_start + timedelta(days=offset)
            day_label = _DAY_LABELS_PL[current_date.weekday()]
            day_full = _DAY_FULL_NAMES_PL[current_date.weekday()]
            day_logs = daily_logs_by_date.get(current_date, [])
            day_exercises = exercise_by_date.get(current_date, [])
            day_drills = drill_by_date.get(current_date, [])

            planned_exercises = _planned_items_count(training_plan.get(day_label, [])) if isinstance(training_plan, dict) else 0
            exercises_logged = len(day_exercises)
            exercise_completion_pct = int(round((exercises_logged / planned_exercises) * 100)) if planned_exercises else 0
            total_volume_kg = round(
                sum((result.sets or 0) * (result.reps or 0) * float(result.weight_kg or 0) for result in day_exercises),
                1,
            )
            exercise_rpe_values = [result.rpe for result in day_exercises if result.rpe is not None]
            avg_exercise_rpe = round(sum(exercise_rpe_values) / len(exercise_rpe_values), 1) if exercise_rpe_values else None
            if exercise_rpe_values:
                all_rpe_values.extend(exercise_rpe_values)

            drill_accuracy_values = [
                round((result.success_count / result.total_attempts) * 100, 1)
                for result in day_drills
                if result.total_attempts and result.total_attempts > 0
            ]
            drill_rpe_values = [result.rpe for result in day_drills if result.rpe is not None]
            avg_drill_accuracy_pct = round(sum(drill_accuracy_values) / len(drill_accuracy_values), 1) if drill_accuracy_values else None
            avg_drill_rpe = round(sum(drill_rpe_values) / len(drill_rpe_values), 1) if drill_rpe_values else None
            if drill_rpe_values:
                all_rpe_values.extend(drill_rpe_values)

            food_logged = any(bool((log.food or "").strip()) for log in day_logs)
            meals_values = [log.meals_eaten for log in day_logs if log.meals_eaten is not None]
            meals_eaten = meals_values[-1] if meals_values else None
            water_liters = sum(float(log.water_liters or 0) for log in day_logs)
            water_ml = round(water_liters * 1000) if water_liters > 0 else 0
            water_pct = min(100, int(round((water_ml / 2500) * 100))) if water_ml else 0

            checkin_done = any(_daily_log_has_data(log) for log in day_logs)
            sleep_hours = _latest_non_null(day_logs, "sleep_hours")
            sleep_quality = _latest_non_null(day_logs, "sleep_quality")
            energy_level = _latest_non_null(day_logs, "energy_level")
            stress_level = _latest_non_null(day_logs, "stress_level")
            mood_score = _latest_non_null(day_logs, "mood_score")
            daily_rpe = _latest_non_null(day_logs, "rpe")
            weight = _latest_non_null(day_logs, "weight")
            if daily_rpe is not None:
                all_rpe_values.append(daily_rpe)
            if weight is not None:
                weight_points.append(float(weight))

            days_list.append({
                "date": current_date.isoformat(),
                "day_label": day_label,
                "day_full": day_full,
                "is_today": current_date == today,
                "exercises_logged": exercises_logged,
                "exercises_planned": planned_exercises,
                "exercise_completion_pct": exercise_completion_pct,
                "total_volume_kg": total_volume_kg,
                "avg_exercise_rpe": avg_exercise_rpe,
                "drills_logged": len(day_drills),
                "avg_drill_accuracy_pct": avg_drill_accuracy_pct,
                "avg_drill_rpe": avg_drill_rpe,
                "food_logged": food_logged,
                "meals_eaten": meals_eaten,
                "water_ml": water_ml,
                "water_pct": water_pct,
                "checkin_done": checkin_done,
                "sleep_hours": _round_float(sleep_hours),
                "sleep_quality": sleep_quality,
                "energy_level": energy_level,
                "stress_level": stress_level,
                "mood_score": mood_score,
                "daily_rpe": daily_rpe,
                "weight": _round_float(weight),
            })

        plan_days = [day for day in days_list if day["exercises_planned"] > 0]
        water_days = [day["water_ml"] for day in days_list if day["water_ml"] > 0]
        summary = {
            "active_days": len([day for day in days_list if day["exercises_logged"] > 0 or day["drills_logged"] > 0]),
            "checkin_days": len([day for day in days_list if day["checkin_done"]]),
            "total_exercises": sum(day["exercises_logged"] for day in days_list),
            "total_drills": sum(day["drills_logged"] for day in days_list),
            "total_volume_kg": round(sum(day["total_volume_kg"] for day in days_list), 1),
            "weekly_plan_completion_pct": int(round(sum(day["exercise_completion_pct"] for day in plan_days) / len(plan_days))) if plan_days else 0,
            "best_training_day": max(plan_days, key=lambda day: (day["exercise_completion_pct"], day["exercises_logged"]))["day_label"] if plan_days else None,
            "food_logged_days": len([day for day in days_list if day["food_logged"]]),
            "avg_water_ml": int(round(sum(water_days) / len(water_days))) if water_days else 0,
            "water_goal_days": len([day for day in days_list if day["water_ml"] >= 2000]),
            "avg_sleep_hours": round(sum(day["sleep_hours"] for day in days_list if day["sleep_hours"] is not None) / len([day for day in days_list if day["sleep_hours"] is not None]), 1) if any(day["sleep_hours"] is not None for day in days_list) else None,
            "avg_sleep_quality": round(sum(day["sleep_quality"] for day in days_list if day["sleep_quality"] is not None) / len([day for day in days_list if day["sleep_quality"] is not None]), 1) if any(day["sleep_quality"] is not None for day in days_list) else None,
            "avg_energy_level": round(sum(day["energy_level"] for day in days_list if day["energy_level"] is not None) / len([day for day in days_list if day["energy_level"] is not None]), 1) if any(day["energy_level"] is not None for day in days_list) else None,
            "avg_stress_level": round(sum(day["stress_level"] for day in days_list if day["stress_level"] is not None) / len([day for day in days_list if day["stress_level"] is not None]), 1) if any(day["stress_level"] is not None for day in days_list) else None,
            "avg_mood_score": round(sum(day["mood_score"] for day in days_list if day["mood_score"] is not None) / len([day for day in days_list if day["mood_score"] is not None]), 1) if any(day["mood_score"] is not None for day in days_list) else None,
            "avg_rpe": round(sum(all_rpe_values) / len(all_rpe_values), 1) if all_rpe_values else None,
            "streak_days": user.streak_days,
            "xp_this_week": len([day for day in days_list if day["exercises_logged"] > 0 or day["drills_logged"] > 0]) * 50 + len([day for day in days_list if day["checkin_done"]]) * 10,
            "weight_change": round(weight_points[-1] - weight_points[0], 1) if len(weight_points) >= 2 else None,
        }

        return {"days": days_list, "summary": summary}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc


@router.post("/onboarding")
def app_onboarding(
    payload: AppOnboardingRequest,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    db_user = session.get(UserDB, user.id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="Użytkownik nie znaleziony. Zarejestruj się przez /auth/register.",
        )

    payload_dict = payload.model_dump()
    update_fields = [
        "name",
        "age",
        "height",
        "weight",
        "target_weight",
        "gender",
        "goal",
        "frequency",
        "diet",
        "allergies",
        "meals_per_day",
        "notes",
    ]
    for field in update_fields:
        if field in payload_dict and payload_dict[field] is not None:
            setattr(db_user, field, payload_dict[field])

    for list_field, key in [
        ("sports_json", "sports"),
        ("training_focus_json", "training_focus"),
        ("improvement_areas_json", "improvement_areas"),
        ("preferred_foods_json", "preferred_foods"),
        ("avoid_foods_json", "avoid_foods"),
        ("available_equipment_json", "available_equipment"),
        ("avoid_exercises_json", "avoid_exercises"),
    ]:
        if key in payload_dict and payload_dict[key]:
            db_user.set_list(list_field, payload_dict[key])

    db_user.calories_target = calc_calories(db_user)
    db_user.protein_target = calc_protein(db_user)
    db_user.updated_at = datetime.now()

    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Błąd zapisu profilu") from exc

    return {
        "status": "ok",
        "user_id": db_user.id,
        "nickname": db_user.nickname,
        "plan": db_user.plan,
        "role": db_user.role,
    }


@router.get("/profile")
def get_profile(user: UserDB = Depends(get_current_user)):
    """Zwraca pełny profil zalogowanego użytkownika."""
    return user.to_profile_dict()


@router.put("/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    user: UserDB = Depends(get_current_user),
):
    """
    Aktualizuje profil użytkownika.
    Tylko niepuste pola są zmieniane — reszta pozostaje bez zmian.
    
    WAŻNE: Kalorie i białko zawsze się przeliczają jeśli zmieni się
    którykolwiek z: weight, age, goal, frequency, gender, diet
    
    Wpływ diet na białko:
    - High-Protein: +0.2 g/kg (max 2.4 g/kg)
    - Low-Carb: +0.1 g/kg (max 2.2 g/kg)
    - Balanced/Standard/inne: bez modyfikacji
    """
    with Session(engine) as session:
        db_user = session.get(UserDB, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")

        should_recalc_macros = False

        # Aktualizuj tylko podane pola
        if payload.age is not None:
            db_user.age = payload.age
            should_recalc_macros = True
        if payload.weight is not None:
            db_user.weight = payload.weight
            should_recalc_macros = True
        if payload.target_weight is not None:
            db_user.target_weight = payload.target_weight
        if payload.gender is not None:
            db_user.gender = payload.gender
            should_recalc_macros = True
        if payload.goal is not None:
            db_user.goal = payload.goal
            should_recalc_macros = True
        if payload.frequency is not None:
            db_user.frequency = payload.frequency
            should_recalc_macros = True
        if payload.diet is not None:
            db_user.diet = payload.diet
            should_recalc_macros = True  # Dieta wpływa na białko!
        if payload.allergies is not None:
            db_user.allergies = payload.allergies
        if payload.meals_per_day is not None:
            db_user.meals_per_day = payload.meals_per_day
        if payload.notes is not None:
            db_user.notes = payload.notes

        # Przelicz kalorie i białko jeśli którykolwiek z parametrów się zmienił
        if should_recalc_macros:
            db_user.calories_target = calc_calories(db_user)
            db_user.protein_target = calc_protein(db_user)

        db_user.updated_at = datetime.now()  # ← Use datetime object
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        return {
            "status": "ok",
            "message": "Profil zaktualizowany",
            "profile": db_user.to_profile_dict(),
        }

@router.put("/profile/nickname")
def change_nickname(
    payload: NicknameChangeRequest,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    import re

    normalized = payload.new_nickname.strip().lower()
    if not re.match(r"^[a-z0-9_\-.]+$", normalized) or len(normalized) < 3:
        raise HTTPException(status_code=422, detail="Nieprawidłowy nick")

    existing = session.exec(select(UserDB).where(UserDB.nickname == normalized)).first()
    if existing and existing.id != user.id:
        raise HTTPException(status_code=409, detail="Ten nick jest już zajęty")

    db_user = session.get(UserDB, user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")

    old_nickname = db_user.nickname
    db_user.nickname = normalized
    db_user.user_key = f"native:nick:{normalized}"
    db_user.updated_at = datetime.now()
    session.add(db_user)
    try:
        session.commit()
        session.refresh(db_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Nick zajęty")

    return {"status": "ok", "old_nickname": old_nickname, "new_nickname": normalized}

@router.get("/dashboard")
def get_dashboard(user: UserDB = Depends(get_current_user)):
    """Zwraca pełny dashboard użytkownika — stats, macros, weight trend, streak."""
    with Session(engine) as session:
        logs = get_user_logs(user, session)
        return build_dashboard(user, logs)


@router.post("/checkin")
def daily_checkin(
    log: AppDailyCheckinRequest,
    user: UserDB = Depends(get_current_user),
):
    """
    Daily check-in — zaloguj posiłek, trening, nastrój, wagę.
    Automatycznie przyznaje XP, oblicza streak, przelicza macros.
    """
    with Session(engine) as session:
        today = date.today()  # ← Use date object instead of string
        existing = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .where(DailyLogDB.log_date == today)
        ).first()

        if existing:
            # UPSERT — Update istniejący wpis
            if log.food:
                existing.food = log.food
            if log.workout:
                existing.workout = log.workout
            if log.mood:
                existing.mood = log.mood
            if log.weight is not None:
                existing.weight = log.weight
            # Nowe pola — aktualizuj tylko jeśli podane
            if log.sleep_hours is not None:
                existing.sleep_hours = log.sleep_hours
            if log.sleep_quality is not None:
                existing.sleep_quality = log.sleep_quality
            if log.sleep_start is not None:
                existing.sleep_start = log.sleep_start
            if log.sleep_end is not None:
                existing.sleep_end = log.sleep_end
            if log.energy_level is not None:
                existing.energy_level = log.energy_level
            # energy_score to alias energy_level
            if log.energy_score is not None:
                existing.energy_level = log.energy_score
            if log.stress_level is not None:
                existing.stress_level = log.stress_level
            if log.mood_score is not None:
                existing.mood_score = log.mood_score
            if log.rpe is not None:
                existing.rpe = log.rpe
            if log.meals_eaten is not None:
                existing.meals_eaten = log.meals_eaten
            if log.workouts_done is not None:
                existing.workouts_done = log.workouts_done
            if log.notes is not None:
                existing.notes = log.notes
            # Woda — jeśli podana w ml, dodaj do water_liters
            if log.water_ml is not None:
                existing.water_liters = round(
                    (existing.water_liters or 0) + log.water_ml / 1000, 4
                )
            existing.logged_at = datetime.now()  # ← Use datetime object
            entry = existing
        else:
            # Nowy wpis
            entry = DailyLogDB(
                user_id=user.id,
                log_date=today,  # ← Use date object
                food=log.food,
                workout=log.workout,
                mood=log.mood,
                weight=log.weight,
                sleep_hours=log.sleep_hours,
                sleep_quality=log.sleep_quality,
                sleep_start=log.sleep_start,
                sleep_end=log.sleep_end,
                energy_level=log.energy_level or log.energy_score,
                stress_level=log.stress_level,
                mood_score=log.mood_score,
                rpe=log.rpe,
                meals_eaten=log.meals_eaten,
                workouts_done=log.workouts_done,
                notes=log.notes,
                water_liters=round(log.water_ml / 1000, 4) if log.water_ml else None,
            )

        session.add(entry)

        # ── XP awards ────────────────────────────────────────────────────────
        # ANTI-SPAM: Track czy to nowy wpis czy update
        is_new_entry = existing is None
        had_previous_workout = existing and existing.workout

        xp_earned = _XP_CHECKIN

        if log.water_ml is not None and log.water_ml >= 500:
            xp_earned += _XP_WATER_LOGGED
        
        if log.weight is not None:
            xp_earned += _XP_WEIGHT_LOGGED
            # Update last_weight_change
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

        # ANTI-SPAM: Award XP for workout ONLY once per day
        if log.workout and (is_new_entry or (not had_previous_workout)):
            xp_earned += _XP_WORKOUT_LOGGED

        if log.meals_eaten:
            xp_earned += min(log.meals_eaten * _XP_MEAL_LOGGED, 25)

        user.total_xp = (user.total_xp or 0) + xp_earned

        # Compute streak
        all_logs = list(session.exec(select(DailyLogDB).where(DailyLogDB.user_id == user.id)).all())
        all_logs.append(entry)
        user.streak_days = compute_streak_days_from_logs(all_logs)
        
        # Streak bonus
        if user.streak_days > 1:
            streak_bonus = min(user.streak_days * _XP_STREAK_BONUS, 100)
            user.total_xp += streak_bonus
            xp_earned += streak_bonus

        user.updated_at = datetime.now()  # ← Use datetime object
        session.add(user)
        session.commit()

        return {
            "status": "ok",
            "log": entry.to_dict(),
            "streak_days": user.streak_days,
            "xp_earned": xp_earned,
            "total_xp": user.total_xp,
            "level": __import__("app.fitness.calculations", fromlist=["_xp_to_level"])._xp_to_level(
                user.total_xp
            ),
        }


@router.get("/debug/today-log")
def debug_today_log(
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    today = date.today()
    log = session.exec(
        select(DailyLogDB)
        .where(DailyLogDB.user_id == user.id)
        .where(DailyLogDB.log_date == today)
    ).first()
    return {
        "has_log": log is not None,
        "log": log.to_dict() if log else None,
        "user_id": user.id,
        "today": today.isoformat(),
    }


@router.get("/checkin-history")
def get_checkin_history(
    limit: int = 30,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Zwraca historię check-inów użytkownika (ostatnie N dni).
    Używane do statystyk, wykresów i generowania planów.
    """
    logs = list(
        session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .order_by(DailyLogDB.log_date.desc())
        ).all()
    )[:max(1, min(limit, 365))]

    logs_with_data = [l for l in logs if any([
        l.sleep_hours, l.energy_level, l.stress_level,
        l.weight, l.mood_score, l.rpe
    ])]

    avg_sleep = None
    avg_energy = None
    avg_stress = None
    avg_rpe = None

    sleep_vals = [l.sleep_hours for l in logs if l.sleep_hours is not None]
    energy_vals = [l.energy_level for l in logs if l.energy_level is not None]
    stress_vals = [l.stress_level for l in logs if l.stress_level is not None]
    rpe_vals = [l.rpe for l in logs if l.rpe is not None]

    if sleep_vals:
        avg_sleep = round(sum(sleep_vals) / len(sleep_vals), 1)
    if energy_vals:
        avg_energy = round(sum(energy_vals) / len(energy_vals), 1)
    if stress_vals:
        avg_stress = round(sum(stress_vals) / len(stress_vals), 1)
    if rpe_vals:
        avg_rpe = round(sum(rpe_vals) / len(rpe_vals), 1)

    return {
        "logs": [l.to_dict() for l in logs],
        "stats": {
            "total_checkins": len(logs),
            "checkins_with_data": len(logs_with_data),
            "avg_sleep_hours": avg_sleep,
            "avg_energy_level": avg_energy,
            "avg_stress_level": avg_stress,
            "avg_rpe": avg_rpe,
            "streak_days": user.streak_days,
        }
    }


@router.post("/exercise-result")
def log_exercise_result(
    req: ExerciseResultRequest,
    user: UserDB = Depends(get_current_user),
):
    """Zaloguj wynik ćwiczenia — nazwa, serie, powtórzenia, ciężar, RPE."""
    session_date = req.session_date or date.today()  # ← Use date object

    result = ExerciseResultDB(
        user_id=user.id,
        exercise_name=req.exercise_name,
        session_date=session_date,  # ← date object
        sets=req.sets,
        reps=req.reps,
        weight_kg=req.weight_kg,
        rpe=req.rpe,
        notes=req.notes,
    )

    with Session(engine) as session:
        session.add(result)
        session.commit()
        session.refresh(result)

    return {
        "status": "ok",
        "result": result.to_dict(),
        "message": f"Ćwiczenie '{req.exercise_name}' zalogowane",
    }


@router.get("/exercise-history", tags=["exercise"])
def get_exercise_history(
    exercise_name: Optional[str] = None,
    limit: int = 20,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Zwraca historię wyników ćwiczeń z sugestią progresji."""
    try:
        query = select(ExerciseResultDB).where(ExerciseResultDB.user_id == user.id)
        if exercise_name:
            query = query.where(ExerciseResultDB.exercise_name == exercise_name)
        results = list(
            session.exec(query.order_by(ExerciseResultDB.session_date.desc())).all()
        )[:limit]

        progression = None
        if exercise_name and results:
            progression = suggest_progression(exercise_name, results)

        return {
            "results": [result.to_dict() for result in results],
            "progression": progression,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database error — please try again later") from exc


@router.get("/progression-summary", tags=["exercise"])
def get_progression_summary(
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Zwraca podsumowanie progresji dla wszystkich ćwiczeń użytkownika."""
    try:
        all_results = list(
            session.exec(
                select(ExerciseResultDB)
                .where(ExerciseResultDB.user_id == user.id)
                .order_by(ExerciseResultDB.session_date.desc())
            ).all()
        )

        by_exercise: dict[str, list[ExerciseResultDB]] = {}
        for result in all_results:
            by_exercise.setdefault(result.exercise_name, []).append(result)

        summary = []
        for name, history in by_exercise.items():
            summary.append(
                {
                    "exercise_name": name,
                    "total_sessions": len(history),
                    "last_session": history[0].to_dict(),
                    "progression": suggest_progression(name, history),
                }
            )

        return {"exercises": summary, "total_exercises_tracked": len(summary)}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database error — please try again later") from exc


@router.post("/water", tags=["checkin"])
def app_log_water(
    body: WaterLogRequest,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Inkrementuje spożycie wody w DailyLogDB dla bieżącego dnia.
    Body: {"ml": 250}
    """
    ml = int(body.ml)
    if ml <= 0:
        raise HTTPException(status_code=400, detail="Ilość wody musi być większa niż 0 ml.")
    if ml > 5000:
        raise HTTPException(status_code=400, detail="Maksymalna jednorazowa porcja to 5000 ml.")

    liters_to_add = round(ml / 1000, 4)
    today = date.today()

    try:
        db_user = session.get(UserDB, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")

        existing = session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == db_user.id)
            .where(DailyLogDB.log_date == today)
        ).first()

        prev_total = existing.water_liters if existing else 0
        if existing:
            existing.water_liters = round((existing.water_liters or 0) + liters_to_add, 4)
            existing.logged_at = datetime.now()
            session.add(existing)
            total_liters = existing.water_liters
        else:
            entry = DailyLogDB(
                user_id=db_user.id,
                log_date=today,
                water_liters=liters_to_add,
            )
            session.add(entry)
            total_liters = liters_to_add

        xp_info = {}
        if prev_total == 0:
            db_user.total_xp = (db_user.total_xp or 0) + _XP_WATER_LOGGED
            session.add(db_user)
            xp_info = {"xp_earned": _XP_WATER_LOGGED, "total_xp": db_user.total_xp}

        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Database error — please try again later") from exc

    return {
        "status": "ok",
        "added_ml": ml,
        "water_liters_today": total_liters,
        "water_ml_today": round(total_liters * 1000),
        **xp_info,
    }


@router.get("/xp", tags=["gamification"])
def get_xp(user: UserDB = Depends(get_current_user)):
    """Zwraca poziom XP, level i postęp do następnego poziomu."""
    return {
        "total_xp": user.total_xp,
        **_xp_to_next_level(user.total_xp),
        "injuries": [item.strip() for item in (user.injuries or "").split(",") if item.strip()],
    }


@router.post("/drill-result")
def log_drill_result(
    req: DrillResultRequest,
    user: UserDB = Depends(get_current_user),
):
    """Zaloguj wynik drilla sportowego — nazwa, sukces/próby, czas, dystans, RPE."""
    from app.models import DrillResultDB

    session_date = req.session_date or date.today()  # ← Use date object

    drill = DrillResultDB(
        user_id=user.id,
        drill_name=req.drill_name,
        session_date=session_date,  # ← date object
        success_count=req.success_count,
        total_attempts=req.total_attempts,
        rpe=req.rpe,
        notes=req.notes,
        time_seconds=req.time_seconds,
        distance_meters=req.distance_meters,
        duration_seconds=req.duration_seconds,
        weight_kg=req.weight_kg,
    )

    with Session(engine) as session:
        session.add(drill)
        session.commit()
        session.refresh(drill)

    return {
        "status": "ok",
        "drill": drill.to_dict(),
        "message": f"Drill '{req.drill_name}' zalogowany",
    }


@router.get("/drill-history", tags=["sport"])
def get_drill_history(
    drill_name: Optional[str] = None,
    limit: int = 20,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    GET /app/drill-history?drill_name=...&limit=20

    Zawsze zwraca HTTP 200.
    Pusty wynik → {"results": [], "progressions": {}} zamiast 500.
    """
    limit = max(1, min(limit, 200))

    try:
        query = select(DrillResultDB).where(DrillResultDB.user_id == user.id)
        if drill_name and drill_name.strip():
            query = query.where(DrillResultDB.drill_name == drill_name.strip())

        query = query.order_by(DrillResultDB.session_date.desc())
        results = list(session.exec(query).all())[:limit]

        if not results:
            print(
                f"[FitAI][get_drill_history] user_id={user.id} drill='{drill_name}' "
                f"— brak wyników w bazie, zwracam []"
            )
            return {"results": [], "progressions": {}}

        by_name: dict[str, list] = {}
        for result in results:
            by_name.setdefault(result.drill_name, []).append(result)

        progressions = {}
        for name, history in by_name.items():
            try:
                progressions[name] = suggest_drill_progression(name, history)
            except Exception as prog_exc:
                print(
                    f"[FitAI][get_drill_history] WARN progresja drill='{name}' "
                    f"— {type(prog_exc).__name__}: {prog_exc}"
                )
                progressions[name] = {"tip": "Brak danych do analizy progresji."}

        print(
            f"[FitAI][get_drill_history] user_id={user.id} drill='{drill_name}' "
            f"— wyniki={len(results)} unique_drills={len(by_name)}"
        )
        return {
            "results": [result.to_dict() for result in results],
            "progressions": progressions,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database error — please try again later") from exc
    except Exception as exc:
        print(
            f"[FitAI][get_drill_history] ERROR user_id={user.id} drill='{drill_name}' "
            f"— {type(exc).__name__}: {exc}"
        )
        return {"results": [], "progressions": {}}


@router.post("/sport-config")
def configure_sport(
    req: SportConfigRequest,
    user: UserDB = Depends(get_current_user),
):
    """Konfiguruj moduł sportowy — sport, specjalizacja, dni treningowe."""
    with Session(engine) as session:
        db_user = upsert_user_from_profile(
            user.user_key,
            {
                "sport_focus": req.sport_focus,
                "sport_specialization": req.sport_specialization,
                "sport_training_days": req.sport_training_days,
            },
            session,
        )
        return {
            "status": "ok",
            "message": "Sport konfiguracja zaktualizowana",
            "sport_focus": db_user.sport_focus,
            "sport_specialization": db_user.sport_specialization,
            "sport_training_days": db_user.get_list("sport_training_days_json"),
        }
