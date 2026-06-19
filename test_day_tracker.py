from __future__ import annotations

import json
from datetime import date
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import engine
from app.models import DailyLogDB, ExerciseResultDB, UserDB
from main import app


client = TestClient(app)


_DAY_LABELS_PL = {0: "Pon", 1: "Wt", 2: "Śr", 3: "Czw", 4: "Pt", 5: "Sob", 6: "Niedz"}


def _today_label() -> str:
    return _DAY_LABELS_PL[date.today().weekday()]


def _seed_user_with_plan():
    email = f"day-tracker-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123",
            "nickname": f"daytracker_{uuid.uuid4().hex[:8]}",
            "name": "Day Tracker Test",
            "age": 29,
            "height": 180.0,
            "weight": 82.0,
            "target_weight": 78.0,
            "gender": "mężczyzna",
            "goal": "weight_loss",
            "frequency": "3-4 razy w tygodniu",
            "diet": "Balanced",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    today_label = _today_label()
    weekly_plan = {
        "days": [
            {
                "day": today_label,
                "meals": [
                    {
                        "id": "plan-meal-1",
                        "name": "Owsianka proteinowa",
                        "kcal": 450,
                        "protein": 32,
                        "meal_type": "Śniadanie",
                    },
                    {
                        "id": "plan-meal-2",
                        "name": "Kurczak z ryżem",
                        "kcal": 620,
                        "protein": 48,
                        "meal_type": "Obiad",
                    },
                ],
                "workout": {
                    "title": "Trening siłowy",
                    "exercises": [
                        {
                            "id": "plan-workout-1",
                            "name": "Przysiad",
                            "sets": 4,
                            "reps": 6,
                            "weight_kg": 90,
                            "rpe": 7,
                        },
                    ],
                },
            }
        ],
        "training": {today_label: [{"name": "Przysiad", "sets": 4, "reps": 6, "weight_kg": 90}]},
        "diet": {today_label: [{"name": "Owsianka proteinowa", "kcal": 450, "protein": 32}]},
    }

    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == email)).first()
        assert user is not None
        user.weekly_plan_json = json.dumps(weekly_plan, ensure_ascii=False)
        user.calories_target = 2200
        user.protein_target = 187
        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "token": token,
        "email": email,
        "today_label": today_label,
    }


@pytest.fixture()
def day_tracker_context():
    return _seed_user_with_plan()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_day_today_seeds_plan_items(day_tracker_context):
    response = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"]))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["plan_meals"]) == 2
    assert len(payload["plan_workouts"]) == 1
    assert payload["kcal_consumed"] == 0
    assert payload["protein_consumed"] == 0
    assert len(payload["log"]["meals"]) == 2
    assert len(payload["log"]["workouts"]) == 1

    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == day_tracker_context["email"])).first()
        assert user is not None
        log = session.exec(select(DailyLogDB).where(DailyLogDB.user_id == user.id).where(DailyLogDB.log_date == date.today())).first()
        assert log is not None
        assert log.get_meals()
        assert log.get_workouts()


def test_day_today_merges_plan_items_into_existing_log(day_tracker_context):
    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == day_tracker_context["email"])).first()
        assert user is not None
        log = DailyLogDB(
            user_id=user.id,
            log_date=date.today(),
            notes="Existing day note",
            meals_json="[]",
            workouts_json="[]",
        )
        session.add(log)
        session.commit()

    response = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"]))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["log"]["meals"]) == 2
    assert len(payload["log"]["workouts"]) == 1
    assert payload["log"]["notes"] == "Existing day note"


def test_day_today_accepts_full_lowercase_day_names(day_tracker_context):
    full_days = {
        "Pon": "poniedziałek",
        "Wt": "wtorek",
        "Śr": "środa",
        "Czw": "czwartek",
        "Pt": "piątek",
        "Sob": "sobota",
        "Niedz": "niedziela",
    }
    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == day_tracker_context["email"])).first()
        assert user is not None
        plan = user.get_dict("weekly_plan_json")
        plan["days"][0]["day"] = full_days[day_tracker_context["today_label"]]
        user.set_dict("weekly_plan_json", plan)
        session.add(user)
        session.commit()

    response = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"]))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["plan_meals"]) == 2
    assert len(payload["plan_workouts"]) == 1


def test_toggle_meal_increases_macros_and_xp(day_tracker_context):
    today = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"])).json()
    meal_id = today["plan_meals"][0]["item_id"]
    meal_kcal = today["plan_meals"][0]["kcal"]
    meal_protein = today["plan_meals"][0]["protein"]

    response = client.post(
        "/app/day/item/toggle",
        json={"item_id": meal_id, "item_type": "meal", "checked": True},
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["xp_earned"] == 10
    assert payload["kcal_consumed"] == meal_kcal
    assert payload["protein_consumed"] == meal_protein

    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == day_tracker_context["email"])).first()
        assert user is not None
        assert user.total_xp >= 10
        log = session.exec(select(DailyLogDB).where(DailyLogDB.user_id == user.id).where(DailyLogDB.log_date == date.today())).first()
        assert log is not None
        assert any(item["item_id"] == meal_id and item["checked"] for item in log.get_meals())


def test_toggle_meal_off_recalculates_macros(day_tracker_context):
    today = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"])).json()
    meal_id = today["plan_meals"][0]["item_id"]

    client.post(
        "/app/day/item/toggle",
        json={"item_id": meal_id, "item_type": "meal", "checked": True},
        headers=_auth_headers(day_tracker_context["token"]),
    )
    response = client.post(
        "/app/day/item/toggle",
        json={"item_id": meal_id, "item_type": "meal", "checked": False},
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["kcal_consumed"] == 0
    assert payload["protein_consumed"] == 0


def test_toggle_workout_logs_exercise_result(day_tracker_context):
    today = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"])).json()
    workout_id = today["plan_workouts"][0]["item_id"]

    response = client.post(
        "/app/day/item/toggle",
        json={"item_id": workout_id, "item_type": "workout", "checked": True},
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["xp_earned"] == 20

    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == day_tracker_context["email"])).first()
        assert user is not None
        result = session.exec(select(ExerciseResultDB).where(ExerciseResultDB.user_id == user.id)).first()
        assert result is not None
        assert result.exercise_name == "Przysiad"
        assert result.sets == 4
        assert result.reps == 6
        assert result.weight_kg == 90


def test_add_custom_meal_appends_to_log(day_tracker_context):
    response = client.post(
        "/app/day/item/add",
        json={
            "item_type": "meal",
            "name": "Domowy szejk",
            "source": "custom",
            "kcal": 280,
            "protein": 32,
            "meal_type": "Przekąska",
        },
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    log = response.json()["log"]
    assert any(item["name"] == "Domowy szejk" for item in log["custom_meals"])


def test_add_custom_workout_appends_to_log(day_tracker_context):
    response = client.post(
        "/app/day/item/add",
        json={
            "item_type": "workout",
            "name": "Mobilizacja bioder",
            "source": "custom",
            "sets": 2,
            "reps": 12,
            "weight_kg": 0,
            "rpe": 4,
        },
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    log = response.json()["log"]
    assert any(item["name"] == "Mobilizacja bioder" for item in log["workouts"])


def test_swap_meal_updates_values_and_totals(day_tracker_context):
    today = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"])).json()
    meal_id = today["plan_meals"][1]["item_id"]

    response = client.post(
        "/app/day/item/swap",
        json={
            "item_id": meal_id,
            "item_type": "meal",
            "new_name": "Indyk z batatami",
            "new_kcal": 700,
            "new_protein": 52,
        },
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    log = response.json()["log"]
    updated = next(item for item in log["meals"] if item["item_id"] == meal_id)
    assert updated["name"] == "Indyk z batatami"
    assert updated["kcal"] == 700
    assert updated["protein"] == 52


def test_swap_workout_updates_sets_reps_weight(day_tracker_context):
    today = client.get("/app/day/today", headers=_auth_headers(day_tracker_context["token"])).json()
    workout_id = today["plan_workouts"][0]["item_id"]

    response = client.post(
        "/app/day/item/swap",
        json={
            "item_id": workout_id,
            "item_type": "workout",
            "new_name": "Przysiad pauzowany",
            "sets": 5,
            "reps": 4,
            "weight_kg": 95,
            "rpe": 8,
        },
        headers=_auth_headers(day_tracker_context["token"]),
    )
    assert response.status_code == 200
    log = response.json()["log"]
    updated = next(item for item in log["workouts"] if item["item_id"] == workout_id)
    assert updated["name"] == "Przysiad pauzowany"
    assert updated["sets"] == 5
    assert updated["reps"] == 4
    assert updated["weight_kg"] == 95
    assert updated["rpe"] == 8
