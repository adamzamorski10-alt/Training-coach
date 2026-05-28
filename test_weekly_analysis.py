from datetime import date
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import engine
from app.models import UserDB
from main import app


client = TestClient(app)


def _day_label_pl(day_date: date) -> str:
    return {0: "Pon", 1: "Wt", 2: "Śr", 3: "Czw", 4: "Pt", 5: "Sob", 6: "Niedz"}[day_date.weekday()]


def test_weekly_analysis_endpoint_returns_7_day_summary():
    email = f"weekly-analysis-{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Weekly Analysis Test",
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
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]

    today = date.today()
    today_label = _day_label_pl(today)

    with Session(engine) as session:
        user = session.exec(select(UserDB).where(UserDB.email == email)).first()
        assert user is not None
        user.weekly_plan_json = f'{{"training": {{"{today_label}": [{{"name": "Squat"}}]}}, "diet": {{}}}}'
        session.add(user)
        session.commit()

    assert client.post(
        "/app/checkin",
        json={
            "food": "Breakfast",
            "workout": "Leg day",
            "mood": "Good",
            "weight": 81.5,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200

    assert client.post(
        "/app/exercise-result",
        json={
            "exercise_name": "Squat",
            "sets": 4,
            "reps": 8,
            "weight_kg": 100.0,
            "rpe": 8,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200

    assert client.post(
        "/app/drill-result",
        json={
            "drill_name": "Free throws",
            "success_count": 18,
            "total_attempts": 20,
            "rpe": 6,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200

    assert client.post(
        "/app/water",
        json={"ml": 2500},
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200

    response = client.get(
        "/app/weekly-analysis",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["days"]) == 7
    assert payload["summary"]["active_days"] >= 1
    assert payload["summary"]["checkin_days"] >= 1
    assert payload["summary"]["total_exercises"] >= 1
    assert payload["summary"]["total_drills"] >= 1

    today_payload = next(day for day in payload["days"] if day["date"] == today.isoformat())
    assert today_payload["day_label"] == today_label
    assert today_payload["checkin_done"] is True
    assert today_payload["food_logged"] is True
    assert today_payload["water_ml"] >= 2500
    assert today_payload["exercises_logged"] >= 1
    assert today_payload["drills_logged"] >= 1