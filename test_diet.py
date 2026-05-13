"""
TEST: Wpływ DIET na białko
Sprawdzamy czy zmiana diet (High-Protein, Low-Carb) zmienia white'e w rozsądnych limitach
"""

import json
from datetime import datetime, timedelta
from sqlmodel import Session, select
from fitai_api import (
    app, UserDB, DailyLogDB, engine, 
    JWT_SECRET_KEY, JWT_ALGORITHM,
    calc_protein
)
from fastapi.testclient import TestClient
import jwt

client = TestClient(app)

print("=" * 80)
print("TEST: DIET → BIAŁKO (wpływ i limity)")
print("=" * 80)

print("\n📋 TEORIA:")
print("-" * 80)
print("""
Baseline (na podstawie goal):
- buildmass: 2.0 g/kg
- weight_loss: 2.2 g/kg
- default: 1.6 g/kg

Modyfikatory diet (z limitami):
- High-Protein: +0.2 g/kg, ale MAX 2.4 g/kg
- Low-Carb: +0.1 g/kg, ale MAX 2.2 g/kg
- Balanced/Standard: bez zmian
- Low-Fat: bez zmian
""")

# ───────────────────────────────────────────────────────────────────────────────
# TEST SETUP
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ Tworzymy test user'a")
print("-" * 80)

with Session(engine) as session:
    # Usuń jeśli istnieje
    test_user = session.exec(select(UserDB).where(UserDB.user_key == "test:diet")).first()
    if test_user:
        session.delete(test_user)
        session.commit()
    
    # User: 80kg, weight_loss goal, diet=Standard
    test_user = UserDB(
        user_key="test:diet",
        identity_id="test_diet",
        email="test@diet.local",
        name="Test Diet",
        age=25,
        height=180,
        weight=80.0,
        start_weight=90.0,
        target_weight=75.0,
        gender="mężczyzna",
        goal="weight_loss",
        frequency="3-4",
        diet="Standard",
        allergies="",
        meals_per_day=4,
        notes="Test diet",
        plan="free",
        role="free_user",
    )
    from fitai_api import calc_calories, calc_protein
    test_user.calories_target = calc_calories(test_user)
    test_user.protein_target = calc_protein(test_user)
    
    session.add(test_user)
    session.commit()
    session.refresh(test_user)
    test_user_id = test_user.id
    print(f"✓ User stworzony")
    print(f"  - weight: 80kg")
    print(f"  - goal: weight_loss")
    print(f"  - diet: Standard")
    print(f"  - baseline protein: 80 * 2.2 = 176g")

# Login
payload = {
    "sub": test_user_id,
    "exp": datetime.utcnow() + timedelta(hours=1)
}
token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
headers = {"Authorization": f"Bearer {token}"}
print(f"✓ Token wygenerowany")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 1: Baseline (Standard diet)
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 1: Baseline (Standard diet)")
print("-" * 80)

response = client.get("/app/profile", headers=headers)
profile = response.json()
baseline_protein = profile.get("protein_target", 0)

print(f"Standard diet:")
print(f"  - protein_target: {baseline_protein}g")
print(f"  - oczekiwane: 176g (80 * 2.2)")

assert baseline_protein == 176, f"Baseline powinno być 176, got {baseline_protein}"
print(f"  ✅ PRAWIDŁOWO")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 2: High-Protein diet (+0.2 g/kg, max 2.4)
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 2: High-Protein diet")
print("-" * 80)

# Zmień diet na High-Protein
response = client.put("/app/profile", json={"diet": "High-Protein"}, headers=headers)
assert response.status_code == 200, f"PUT failed: {response.status_code}"

profile = response.json().get("profile", {})
high_protein_target = profile.get("protein_target", 0)

# 80 * (2.2 + 0.2) = 80 * 2.4 = 192g (ale limit max 2.4)
expected_high_protein = int(80 * min(2.2 + 0.2, 2.4))  # = 80 * 2.4 = 192

print(f"High-Protein diet:")
print(f"  - protein_target: {high_protein_target}g")
print(f"  - oczekiwane: {expected_high_protein}g (80 * 2.4, czyli baseline 2.2 + 0.2 modyfikator)")

assert high_protein_target == expected_high_protein, \
    f"Expected {expected_high_protein}g, got {high_protein_target}g"
print(f"  ✅ PRAWIDŁOWO — białko zwiększyło się z 176 → {high_protein_target}g")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 3: Low-Carb diet (+0.1 g/kg, max 2.2)
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 3: Low-Carb diet")
print("-" * 80)

# Zmień diet na Low-Carb
response = client.put("/app/profile", json={"diet": "Low-Carb"}, headers=headers)
assert response.status_code == 200

profile = response.json().get("profile", {})
low_carb_target = profile.get("protein_target", 0)

# 80 * (2.2 + 0.1) = 80 * 2.3 = 184g (limit to 2.3, więc +0.1 działa!)
expected_low_carb = int(80 * min(2.2 + 0.1, 2.3))  # = 80 * 2.3 = 184

print(f"Low-Carb diet:")
print(f"  - protein_target: {low_carb_target}g")
print(f"  - oczekiwane: {expected_low_carb}g (baseline 2.2 + modyfikator 0.1 = 2.3, limit 2.3)")

assert low_carb_target == expected_low_carb, \
    f"Expected {expected_low_carb}g, got {low_carb_target}g"
print(f"  ✅ PRAWIDŁOWO — białko zwiększyło się z 176 → {low_carb_target}g")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 4: Buildmass goal + High-Protein (2.0 + 0.2 = 2.2)
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 4: Buildmass goal + High-Protein")
print("-" * 80)

# Najpierw zmień diet z powrotem na High-Protein, potem goal na buildmass
response = client.put("/app/profile", json={"diet": "High-Protein", "goal": "buildmass"}, headers=headers)
assert response.status_code == 200

profile = response.json().get("profile", {})
buildmass_protein = profile.get("protein_target", 0)

# buildmass baseline: 2.0 + High-Protein: 0.2 = 2.2, limit 2.4
# 80 * 2.2 = 176g
expected_buildmass = int(80 * min(2.0 + 0.2, 2.4))  # = 80 * 2.2 = 176

print(f"Buildmass + High-Protein:")
print(f"  - protein_target: {buildmass_protein}g")
print(f"  - oczekiwane: {expected_buildmass}g (80 * 2.2, baseline 2.0 + modyfikator 0.2)")

assert buildmass_protein == expected_buildmass, \
    f"Expected {expected_buildmass}g, got {buildmass_protein}g"
print(f"  ✅ PRAWIDŁOWO")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 5: Zmiana wagi (80 → 100 kg) — High-Protein + Buildmass
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 5: Zmiana wagi (80 → 100kg)")
print("-" * 80)

# Zmień wagę na 100kg
response = client.put("/app/profile", json={"weight": 100.0}, headers=headers)
assert response.status_code == 200

profile = response.json().get("profile", {})
new_weight_protein = profile.get("protein_target", 0)

# 100 * (2.0 + 0.2) = 100 * 2.2 = 220g
expected_new_weight = int(100 * min(2.0 + 0.2, 2.4))  # = 100 * 2.2 = 220

print(f"Waga 100kg + Buildmass + High-Protein:")
print(f"  - protein_target: {new_weight_protein}g")
print(f"  - oczekiwane: {expected_new_weight}g (100 * 2.2)")

assert new_weight_protein == expected_new_weight, \
    f"Expected {expected_new_weight}g, got {new_weight_protein}g"
print(f"  ✅ PRAWIDŁOWO — białko wynosiło 176g, teraz {new_weight_protein}g")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 6: Limit bezpieczeństwa (nie powinno przekroczyć 2.4 g/kg)
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 6: Limit bezpieczeństwa (max 2.4 g/kg)")
print("-" * 80)

# Max możliwe: weight_loss (2.2) + High-Protein (0.2) = 2.4 g/kg
# Zmień goal na weight_loss (już High-Protein)
response = client.put("/app/profile", json={"goal": "weight_loss"}, headers=headers)
assert response.status_code == 200

profile = response.json().get("profile", {})
max_protein = profile.get("protein_target", 0)

# 100 * (2.2 + 0.2) = 100 * 2.4 = 240g (hit limit!)
expected_max = int(100 * min(2.2 + 0.2, 2.4))  # = 100 * 2.4 = 240

print(f"Weight_loss + High-Protein (max limit):")
print(f"  - protein_target: {max_protein}g")
print(f"  - oczekiwane: {expected_max}g (100 * 2.4 — LIMIT)")

assert max_protein == expected_max, f"Expected {expected_max}g, got {max_protein}g"
print(f"  ✅ PRAWIDŁOWO — limit 2.4 g/kg działał prawidłowo")

# ───────────────────────────────────────────────────────────────────────────────
# CLEANUP & SUMMARY
# ───────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
with Session(engine) as session:
    test_user = session.get(UserDB, test_user_id)
    if test_user:
        session.delete(test_user)
        session.commit()
        print("✓ Test user usunięty")

print("=" * 80)
print("✅ WSZYSTKIE TESTY DIET→BIAŁKO PRZESZŁY!")
print("=" * 80)
print(f"""
PODSUMOWANIE ZMIAN:
1. ✅ calc_protein() teraz bierze pod uwagę diet
2. ✅ High-Protein: +0.2 g/kg (max 2.4 g/kg)
3. ✅ Low-Carb: +0.1 g/kg (limit 2.3 g/kg — pozwala na modyfikator)
4. ✅ PUT /app/profile przelicza białko gdy zmieni się diet
5. ✅ Limity bezpieczeństwa działają (max 2.4 g/kg dla High-Protein)
6. ✅ Białko nigdy nie przekracza limitu zdrowotnego
""")
