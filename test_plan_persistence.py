from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.jwt_utils import create_access_token
from app.database import engine
from app.models import UserDB
from main import app


client = TestClient(app)


_DAY_LABELS_PL = {0: "Pon", 1: "Wt", 2: "Śr", 3: "Czw", 4: "Pt", 5: "Sob", 6: "Niedz"}


def _seed_user() -> tuple[UserDB, str]:
    suffix = uuid.uuid4().hex[:10]
    user = UserDB(
        user_key=f"test-plan:{suffix}",
        email=f"plan-{suffix}@example.com",
        nickname=f"plan_{suffix}",
        name="Plan Persistence Test",
        age=30,
        height=180.0,
        weight=82.0,
        start_weight=82.0,
        target_weight=78.0,
        gender="mężczyzna",
        goal="weight_loss",
        frequency="3-4 razy w tygodniu",
        diet="Balanced",
        calories_target=2200,
        protein_target=180,
    )
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_access_token(user.id, user.email or "", user.role)
        return user, token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_saved_weekly_plan_survives_profile_reload_and_feeds_my_day():
    user, token = _seed_user()
    today = _DAY_LABELS_PL[date.today().weekday()]
    weekly_plan = {
        "days": [
            {
                "day": today,
                "meals": [
                    {"id": "meal-custom-1", "name": "Mój zapisany obiad", "kcal": 650, "protein": 45},
                ],
                "workout": {
                    "title": "Mój zapisany trening",
                    "exercises": [
                        {"id": "workout-custom-1", "name": "Moje zapisane ćwiczenie", "sets": 4, "reps": 8},
                    ],
                },
            }
        ],
        "diet": {
            today: [{"id": "meal-custom-1", "name": "Mój zapisany obiad", "kcal": 650, "protein": 45}],
        },
        "training": {
            today: [{"id": "workout-custom-1", "name": "Moje zapisane ćwiczenie", "sets": 4, "reps": 8}],
        },
    }

    save_response = client.put(
        "/app/plan/current",
        json={"plan": weekly_plan},
        headers=_auth_headers(token),
    )
    assert save_response.status_code == 200

    profile_response = client.get("/app/profile", headers=_auth_headers(token))
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["weekly_plan"]["diet"][today][0]["name"] == "Mój zapisany obiad"
    assert profile["weekly_plan"]["training"][today][0]["name"] == "Moje zapisane ćwiczenie"

    today_response = client.get("/app/day/today", headers=_auth_headers(token))
    assert today_response.status_code == 200
    today_payload = today_response.json()
    assert today_payload["plan_meals"][0]["name"] == "Mój zapisany obiad"
    assert today_payload["plan_workouts"][0]["name"] == "Moje zapisane ćwiczenie"

    with Session(engine) as session:
        db_user = session.get(UserDB, user.id)
        assert db_user is not None
        assert db_user.get_dict("weekly_plan_json")["source"] == "user_saved"
