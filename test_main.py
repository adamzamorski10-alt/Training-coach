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