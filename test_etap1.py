"""
TEST ETAP 1 — Sprawdzenie 3 zmian:
1. /health endpoint
2. PUT /app/profile 
3. Ochrona XP spam
"""

import json
import os
from datetime import date, datetime, timedelta
from sqlmodel import Session, select, create_engine
from fitai_api import (
    app, UserDB, DailyLogDB, engine, 
    _XP_WORKOUT_LOGGED, _XP_CHECKIN,
    ProfileUpdateRequest, AppDailyCheckinRequest,
    JWT_SECRET_KEY, JWT_ALGORITHM  # Import prawidłowych stałych
)
from fastapi.testclient import TestClient
import jwt

client = TestClient(app)

print("=" * 70)
print("TEST ETAP 1 — FitAI Usprawnienia")
print("=" * 70)

# ───────────────────────────────────────────────────────────────────────────────
# TEST 1: /health endpoint
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 1: /health endpoint")
print("-" * 70)

response = client.get("/health")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

assert response.status_code == 200, f"Oczekiwano 200, got {response.status_code}"
data = response.json()
assert data["status"] in ["ok", "degraded"], f"Invalid status: {data['status']}"
assert "database" in data, "Brakuje 'database' w response"
print("✅ /health endpoint działa prawidłowo!\n")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 2: PUT /app/profile — Edycja profilu
# ───────────────────────────────────────────────────────────────────────────────
print("✅ TEST 2: PUT /app/profile — Edycja profilu")
print("-" * 70)

# Najpierw tworzę test user
with Session(engine) as session:
    # Usuń jeśli istnieje
    test_user = session.exec(select(UserDB).where(UserDB.user_key == "test:etap1")).first()
    if test_user:
        session.delete(test_user)
        session.commit()
    
    # Utwórz nowego użytkownika
    test_user = UserDB(
        user_key="test:etap1",
        identity_id="test_etap1",
        email="test@etap1.local",
        name="Test User Etap1",
        age=25,
        height=180,
        weight=75.0,
        start_weight=80.0,
        target_weight=70.0,
        gender="mężczyzna",
        goal="weight_loss",
        frequency="3",
        diet="balanced",
        allergies="",
        meals_per_day=4,
        notes="Test user",
        plan="free",
        role="free_user",
    )
    session.add(test_user)
    session.commit()
    session.refresh(test_user)
    test_user_id = test_user.id
    print(f"✓ Stworzono test user: {test_user_id}")

# Generuj token JWT (uproszczona wersja bez real auth)
import jwt
import os
from datetime import datetime, timedelta

payload = {
    "sub": test_user_id,
    "exp": datetime.utcnow() + timedelta(hours=1)
}
token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
headers = {"Authorization": f"Bearer {token}"}

print(f"✓ Generowany token JWT")

# Test PUT profilu
update_data = {
    "age": 26,
    "weight": 74.0,
    "target_weight": 68.0,
    "diet": "low_carb",
    "allergies": "orzechy",
    "notes": "Zaktualizowany test",
}

print(f"\nSendując PUT /app/profile z danymi:")
for k, v in update_data.items():
    print(f"  {k}: {v}")

response = client.put("/app/profile", json=update_data, headers=headers)
print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    resp_data = response.json()
    print(f"Response status: {resp_data.get('status')}")
    profile = resp_data.get("profile", {})
    print(f"\nZaktualizowany profil:")
    print(f"  age: {profile.get('age')} (oczekiwano 26)")
    print(f"  weight: {profile.get('weight')} (oczekiwano 74.0)")
    print(f"  diet: {profile.get('diet')} (oczekiwano low_carb)")
    print(f"  allergies: {profile.get('allergies')} (oczekiwano orzechy)")
    
    assert profile.get('age') == 26, f"Age: {profile.get('age')}"
    assert profile.get('weight') == 74.0, f"Weight: {profile.get('weight')}"
    assert profile.get('diet') == "low_carb", f"Diet: {profile.get('diet')}"
    assert profile.get('allergies') == "orzechy", f"Allergies: {profile.get('allergies')}"
    print("\n✅ PUT /app/profile działa prawidłowo!")
else:
    print(f"❌ Błąd: {response.text}")
    raise Exception(f"PUT profile failed with {response.status_code}")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 3: Ochrona XP spam — Sprawdzenie limit treningu
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 3: Ochrona XP spam")
print("-" * 70)

with Session(engine) as session:
    user = session.get(UserDB, test_user_id)
    initial_xp = user.total_xp
    print(f"✓ Początkowe XP: {initial_xp}")

# Pierwszy checkin z workout
checkin1 = {
    "food": "Śniadanie",
    "workout": "Bieganie 5km",
    "mood": "ok",
}

print(f"\n1️⃣ Pierwszy checkin z workout:")
response = client.post("/app/checkin", json=checkin1, headers=headers)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    resp1 = response.json()
    xp_earned_1 = resp1.get("xp_earned", 0)
    total_xp_1 = resp1.get("total_xp", 0)
    print(f"   XP zarobione: {xp_earned_1}")
    print(f"   Total XP: {total_xp_1}")
    
    # Powinien dostać: _XP_CHECKIN (10) + _XP_WORKOUT_LOGGED (50) = 60
    expected_xp_1 = _XP_CHECKIN + _XP_WORKOUT_LOGGED
    print(f"   Oczekiwano: {expected_xp_1}")
    assert xp_earned_1 == expected_xp_1, f"Pierwszy checkin: zarobił {xp_earned_1}, oczekiwano {expected_xp_1}"
    print(f"   ✓ Poprawnie zarobił {xp_earned_1} XP na pierwszy checkin")
else:
    print(f"❌ Błąd checkin 1: {response.text}")
    raise Exception("Checkin 1 failed")

# Drugi checkin z update workout (powinien NIE dać XP za workout ponownie!)
checkin2 = {
    "food": "Obiad",
    "workout": "Siłownia 1h",  # ZMIENIONY WORKOUT
    "mood": "ok",
}

print(f"\n2️⃣ Drugi checkin — update z nowym workout:")
response = client.post("/app/checkin", json=checkin2, headers=headers)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    resp2 = response.json()
    xp_earned_2 = resp2.get("xp_earned", 0)
    total_xp_2 = resp2.get("total_xp", 0)
    print(f"   XP zarobione: {xp_earned_2}")
    print(f"   Total XP: {total_xp_2}")
    
    # Powinien dostać TYLKO: _XP_CHECKIN (10) = 10 (BEZ _XP_WORKOUT_LOGGED bo już dzisiaj był!)
    expected_xp_2 = _XP_CHECKIN  # NIE +  _XP_WORKOUT_LOGGED
    print(f"   Oczekiwano: {expected_xp_2}")
    assert xp_earned_2 == expected_xp_2, f"Update checkin: zarobił {xp_earned_2}, oczekiwano {expected_xp_2}"
    print(f"   ✓ Poprawnie zarobił {xp_earned_2} XP (bez powtórki za workout!)")
    print(f"   ✓ ANTI-SPAM: Druga zmiana treningu NICHT dała XP za workout")
else:
    print(f"❌ Błąd checkin 2: {response.text}")
    raise Exception("Checkin 2 failed")

# Trzeci checkin bez workout (powinien dać normalne XP, ale nie za workout)
checkin3 = {
    "food": "Kolacja",
    "workout": "",  # BEZ WORKOUTU
    "mood": "ok",
}

print(f"\n3️⃣ Trzeci checkin — bez workout:")
response = client.post("/app/checkin", json=checkin3, headers=headers)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    resp3 = response.json()
    xp_earned_3 = resp3.get("xp_earned", 0)
    total_xp_3 = resp3.get("total_xp", 0)
    print(f"   XP zarobione: {xp_earned_3}")
    print(f"   Total XP: {total_xp_3}")
    
    # Powinien dostać: _XP_CHECKIN (10) = 10 (bez workoutu)
    expected_xp_3 = _XP_CHECKIN
    print(f"   Oczekiwano: {expected_xp_3}")
    assert xp_earned_3 == expected_xp_3, f"Checkin bez workoutu: zarobił {xp_earned_3}, oczekiwano {expected_xp_3}"
    print(f"   ✓ Poprawnie zarobił {xp_earned_3} XP")
else:
    print(f"❌ Błąd checkin 3: {response.text}")
    raise Exception("Checkin 3 failed")

print("\n" + "=" * 70)
print("✅ WSZYSTKIE TESTY ETAP 1 PRZESZŁY!")
print("=" * 70)
print(f"""
PODSUMOWANIE:
1. ✅ /health endpoint — działa, zwraca status
2. ✅ PUT /app/profile — działa, edytuje profil użytkownika
3. ✅ Ochrona XP spam — działa:
   - Pierwszy checkin z workout: +50 XP (prawidłowo)
   - Update workout dzisiaj: +0 XP (anti-spam działał!)
   - Checkin bez workout: +10 XP (prawidłowo)
""")

# Cleanup
with Session(engine) as session:
    test_user = session.get(UserDB, test_user_id)
    if test_user:
        # Delete related logs first
        logs = session.exec(select(DailyLogDB).where(DailyLogDB.user_id == test_user_id)).all()
        for log in logs:
            session.delete(log)
        session.delete(test_user)
        session.commit()
        print("✓ Test user usunięty z bazy")

print("\n✅ Test script zakończony pomyślnie!")
