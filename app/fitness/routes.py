"""
Fitness Routes — Profile, dashboard, daily checkin, exercise/drill logging
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
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
    ProfileUpdateRequest,
    SportConfigRequest,
    WaterLogRequest,
)
from app.fitness.utils import upsert_user_from_profile

router = APIRouter(prefix="/app", tags=["fitness"])


def _web_user_key(identity_id: str) -> str:
    return f"web:{identity_id}"


@router.post("/onboarding")
def app_onboarding(
    payload: AppOnboardingRequest,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_key = _web_user_key(payload.identity_id)
    try:
        user = upsert_user_from_profile(
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
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Database error — please try again later") from exc


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
            )

        session.add(entry)

        # ── XP awards ────────────────────────────────────────────────────────
        # ANTI-SPAM: Track czy to nowy wpis czy update
        is_new_entry = existing is None
        had_previous_workout = existing and existing.workout

        xp_earned = _XP_CHECKIN
        
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
