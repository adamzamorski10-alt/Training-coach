"""
Fitness Dashboard — Dashboard building, streak computation, log helpers
"""

from datetime import date, datetime
from sqlmodel import Session, select

from app.models import DailyLogDB, UserDB
from app.fitness.calculations import calc_daily_macros, day_type, day_type_label


def get_user_logs(user: UserDB, session: Session) -> list[DailyLogDB]:
    """Pobierz wszystkie dzienne raporty użytkownika."""
    return list(
        session.exec(
            select(DailyLogDB)
            .where(DailyLogDB.user_id == user.id)
            .order_by(DailyLogDB.log_date.desc())
        ).all()
    )


def compute_streak_days_from_logs(logs: list[DailyLogDB]) -> int:
    """
    Liczy najdłuższy streak (liczę od dzisiaj wstecz).
    Streak zlicza dni z check-inem (food/workout/weight), bez przerw.
    """
    if not logs:
        return 0
    
    today = date.today()
    logs_by_date = {log.log_date: log for log in logs}
    
    current_date = today
    streak = 0
    while True:
        if current_date in logs_by_date:
            log = logs_by_date[current_date]
            # Day counts if it has ANY data logged (food, workout, or weight)
            if log.food or log.workout or log.weight is not None:
                streak += 1
                # Move to previous day
                current_date = current_date - __import__("datetime").timedelta(days=1)
                continue
        break
    
    return streak


def build_dashboard(user: UserDB, logs: list[DailyLogDB]) -> dict:
    """Buduje pełny dashboard dla użytkownika."""
    today = date.today()
    today_log = next((l for l in logs if l.log_date == today), None)
    
    # Macros
    kcal = user.calories_target or 2000
    focus = user.get_list("training_focus_json")
    day_type_key = day_type(datetime.now().strftime("%A"), focus[0].lower() if focus else "klatka")
    macros = calc_daily_macros(kcal, day_type_key)
    
    # Weight trend (last 14 days)
    weight_logs = [l for l in logs if l.weight is not None][:14]
    weight_trend = [{"date": l.log_date.isoformat(), "weight": l.weight} for l in reversed(weight_logs)]
    
    # Weekly stats
    week_ago = today - __import__("datetime").timedelta(days=7)
    week_logs = [l for l in logs if l.log_date >= week_ago]
    workouts_week = len([l for l in week_logs if l.workout])
    
    return {
        "user_id": user.id,
        "name": user.name,
        "level": __import__("app.fitness.calculations", fromlist=["_xp_to_level"])._xp_to_level(user.total_xp),
        "total_xp": user.total_xp,
        "streak_days": user.streak_days,
        "calories_target": user.calories_target,
        "protein_target": user.protein_target,
        "weight": user.weight,
        "weight_trend": weight_trend,
        "today": {
            "date": today,
            "food": today_log.food if today_log else None,
            "workout": today_log.workout if today_log else None,
            "mood": today_log.mood if today_log else None,
            "weight": today_log.weight if today_log else None,
            "logged": today_log is not None,
        },
        "weekly_stats": {
            "workouts": workouts_week,
            "logs_count": len(week_logs),
        },
        "macros_today": macros,
        "day_type": day_type_key,
        "day_type_label": day_type_label(day_type_key),
    }
