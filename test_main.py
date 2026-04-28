import pytest
from fastapi.testclient import TestClient
from fitai_api import app
import os
import json

client = TestClient(app)
TEST_USER_ID = "test_pytest_user"

def test_read_root():
    """Sprawdza czy API w ogóle wstaje."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "FitAI API"

def test_create_user():
    """Testuje tworzenie profilu użytkownika."""
    user_data = {
        "name": "Tester",
        "age": 30,
        "height": 180,
        "weight": 80,
        "target_weight": 75,
        "gender": "mężczyzna",
        "goal": "Redukcja",
        "frequency": "3-4 razy w tygodniu",
        "sports": ["bieganie"],
        "diet": "Zbilansowana",
        "meals_per_day": 3
    }
    response = client.post(f"/users/{TEST_USER_ID}", json=user_data)
    assert response.status_code == 200
    assert "calories_target" in response.json()

def test_get_user_not_found():
    """Sprawdza obsługę błędów dla nieistniejącego użytkownika."""
    response = client.get("/users/non_existent_user_999")
    assert response.status_code == 404

def test_add_log():
    """Testuje dodawanie wpisu do dziennika."""
    log_data = {
        "food": "Kurczak z ryżem",
        "workout": "Bieganie 5km",
        "mood": "Świetnie",
        "weight": 79.5
    }
    response = client.post(f"/users/{TEST_USER_ID}/logs", json=log_data)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_app_onboarding():
    """Testuje aplikacyjny onboarding (web panel)."""
    identity_id = "test_identity_123"
    payload = {
        "identity_id": identity_id,
        "email": "test@example.com",
        "name": "Test User",
        "age": 30,
        "height": 180,
        "weight": 80,
        "target_weight": 75,
        "gender": "mężczyzna",
        "goal": "Redukcja tkanki tłuszczowej",
        "frequency": "3-4 razy w tygodniu",
        "sports": ["siłownia", "bieganie"],
        "training_focus": ["klatka", "plecy"],
        "improvement_areas": ["brzuch", "nogi"],
        "diet": "Zbilansowana",
        "allergies": "orzeszki",
        "meals_per_day": 5,
        "notes": "Test notes"
    }
    response = client.post("/app/onboarding", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["plan"] == "free"
    assert data["role"] == "free_user"


def test_app_get_profile():
    """Testuje pobranie profilu z panelu."""
    identity_id = "test_identity_123"
    response = client.get(f"/app/profile/{identity_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["goal"] == "Redukcja tkanki tłuszczowej"


def test_app_generate_plan():
    """Testuje generowanie planu tygodniowego."""
    identity_id = "test_identity_123"
    payload = {"force": True}
    response = client.post(f"/app/plan/{identity_id}/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    plan = data["plan"]
    assert "days" in plan
    assert len(plan["days"]) == 7
    day = plan["days"][0]
    assert "day" in day
    assert "meals" in day
    assert "workout" in day
    assert len(day["meals"]) == 5
    assert len(day["workout"]["exercises"]) > 0


def test_app_get_plan():
    """Testuje pobranie planu."""
    identity_id = "test_identity_123"
    response = client.get(f"/app/plan/{identity_id}")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert len(data["days"]) == 7


def test_app_swap_meal():
    """Testuje zmianę posiłku na alternatywę."""
    identity_id = "test_identity_123"
    payload = {
        "day_index": 0,
        "section": "meal",
        "item_index": 0,
        "alternative_index": 0
    }
    response = client.post(f"/app/plan/{identity_id}/swap", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    plan = data["plan"]
    meal = plan["days"][0]["meals"][0]
    assert "name" in meal
    assert "alternatives" in meal


def test_app_swap_exercise():
    """Testuje zmianę ćwiczenia na alternatywę."""
    identity_id = "test_identity_123"
    payload = {
        "day_index": 0,
        "section": "exercise",
        "item_index": 0,
        "alternative_index": 0
    }
    response = client.post(f"/app/plan/{identity_id}/swap", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    plan = data["plan"]
    exercise = plan["days"][0]["workout"]["exercises"][0]
    assert "name" in exercise
    assert "sets" in exercise
    assert "reps" in exercise
    assert "alternatives" in exercise


def test_app_version():
    """Testuje GET /app/version endpoint"""
    response = client.get("/app/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "build_date" in data
    assert "api_version" in data