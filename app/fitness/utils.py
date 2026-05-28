"""
Fitness Utilities — User profile helpers, meal catalogs, exercise pools
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.fitness.calculations import calc_calories, calc_protein
from app.models import UserDB


def upsert_user_from_profile(
    user_key: str,
    payload: dict,
    session: Session,
    *,
    identity_id: Optional[str] = None,
    email: Optional[str] = None,
) -> UserDB:
    """Create or update user from profile dict (legacy + new)."""
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

    for field in [
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
    ]:
        if field in payload:
            setattr(user, field, payload[field])

    if identity_id:
        user.identity_id = identity_id
    if email:
        user.email = email
    if not user.start_weight:
        user.start_weight = user.weight

    for list_field, key in [
        ("sports_json", "sports"),
        ("training_focus_json", "training_focus"),
        ("improvement_areas_json", "improvement_areas"),
        ("preferred_foods_json", "preferred_foods"),
        ("avoid_foods_json", "avoid_foods"),
        ("available_equipment_json", "available_equipment"),
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
    user.updated_at = datetime.now()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
