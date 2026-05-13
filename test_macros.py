"""
TEST: Weryfikacja liczenia KALORII i BIAŁKA
Sprawdzamy czy zmiana weight, goal, frequency zmienia liczenie makroskładników
"""

import json
from datetime import datetime, timedelta
from sqlmodel import Session, select
from fitai_api import (
    app, UserDB, DailyLogDB, engine, 
    JWT_SECRET_KEY, JWT_ALGORITHM,
    calc_calories, calc_protein
)
from fastapi.testclient import TestClient
import jwt

client = TestClient(app)

print("=" * 80)
print("TEST: KALORIE & BIAŁKO — Weryfikacja liczenia")
print("=" * 80)

# ───────────────────────────────────────────────────────────────────────────────
# Teoria:
# ───────────────────────────────────────────────────────────────────────────────
print("\n📚 TEORIA LICZENIA:")
print("-" * 80)
print("""
BMR (Basal Metabolic Rate) — Mifflin-St Jeor:
  - Mężczyzna: BMR = 10*waga + 6.25*wzrost - 5*wiek + 5
  - Kobieta: BMR = 10*waga + 6.25*wzrost - 5*wiek - 161

TDEE = BMR * multiplier (zależy od aktywności):
  - codziennie: 1.9
  - 5-6 dni/tyg: 1.725
  - 3-4 dni/tyg: 1.55
  - 1-2 dni/tyg: 1.375
  - inne: 1.2

Goal adjustment:
  - redukcja: TDEE - 400 kcal
  - budowa masy: TDEE + 300 kcal
  - inne: TDEE bez zmian

BIAŁKO:
  - Budowa (masa): waga * 2.0 g/kg
  - Redukcja (redukcja): waga * 2.2 g/kg
  - Inne (default): waga * 1.6 g/kg
""")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 1: Tworzenie test user'a
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 1: Tworzenie test user'a")
print("-" * 80)

with Session(engine) as session:
    # Usuń jeśli istnieje
    test_user = session.exec(select(UserDB).where(UserDB.user_key == "test:macros")).first()
    if test_user:
        session.delete(test_user)
        session.commit()
    
    # Utwórz nowego użytkownika
    # Waga: 80kg, Wzrost: 180cm, Wiek: 25, Mężczyzna
    # Częstotliwość: 3-4 dni/tyg, Goal: weight_loss
    test_user = UserDB(
        user_key="test:macros",
        identity_id="test_macros",
        email="test@macros.local",
        name="Test Macros",
        age=25,
        height=180,
        weight=80.0,
        start_weight=90.0,
        target_weight=75.0,
        gender="mężczyzna",
        goal="weight_loss",
        frequency="3-4",
        diet="balanced",
        allergies="",
        meals_per_day=4,
        notes="Test macros",
        plan="free",
        role="free_user",
    )
    # Oblicz kalorie i białko (jest to robione w _upsert_user_from_profile, ale tutaj robimy ręcznie)
    from fitai_api import calc_calories, calc_protein
    test_user.calories_target = calc_calories(test_user)
    test_user.protein_target = calc_protein(test_user)
    
    session.add(test_user)
    session.commit()
    session.refresh(test_user)
    test_user_id = test_user.id
    print(f"✓ Stworzono test user: {test_user_id}")
    print(f"  - Initial calories_target: {test_user.calories_target}")
    print(f"  - Initial protein_target: {test_user.protein_target}")

# Zaloguj się
payload = {
    "sub": test_user_id,
    "exp": datetime.utcnow() + timedelta(hours=1)
}
token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
headers = {"Authorization": f"Bearer {token}"}
print("✓ Wygenerowany token JWT")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 2: Wyliczenie teoretyczne vs rzeczywiste
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 2: Weryfikacja wzorów (80kg, 180cm, 25y, mężczyzna, 3-4 dni, weight_loss)")
print("-" * 80)

# BMR = 10*80 + 6.25*180 - 5*25 + 5 = 800 + 1125 - 125 + 5 = 1805
bmr_expected = 10 * 80 + 6.25 * 180 - 5 * 25 + 5
print(f"1. BMR (Mifflin-St Jeor):")
print(f"   = 10*80 + 6.25*180 - 5*25 + 5")
print(f"   = {bmr_expected} kcal")

# TDEE = 1805 * 1.55 (3-4 dni) = 2798 kcal
tdee_no_goal = int(bmr_expected * 1.55)
print(f"\n2. TDEE (bez goal adjustmentu):")
print(f"   = {bmr_expected} * 1.55 (3-4 dni)")
print(f"   = {tdee_no_goal} kcal")

# Weight loss: TDEE - 400 = 2398 kcal
tdee_final = tdee_no_goal - 400
print(f"\n3. TDEE Final (weight_loss -400 kcal):")
print(f"   = {tdee_no_goal} - 400")
print(f"   = {tdee_final} kcal (OCZEKIWANA KALKULACJA)")

# Białko (weight_loss): 80 * 2.2 = 176g
protein_expected = int(80 * 2.2)
print(f"\n4. Białko (weight_loss: waga * 2.2):")
print(f"   = 80 * 2.2")
print(f"   = {protein_expected}g (OCZEKIWANE)")

# Pobierz profil i sprawdź
print(f"\n5. Pobieranie profilu z API...")
response = client.get("/app/profile", headers=headers)
assert response.status_code == 200, f"Błąd GET profile: {response.status_code}"
profile = response.json()

actual_calories = profile.get("calories_target", 0)
actual_protein = profile.get("protein_target", 0)

print(f"   API zwraca:")
print(f"   - calories_target: {actual_calories} kcal")
print(f"   - protein_target: {actual_protein}g")

if actual_calories == tdee_final and actual_protein == protein_expected:
    print(f"\n   ✅ WSZYSTKO PRAWIDŁOWO!")
else:
    print(f"\n   ⚠️  NIEZGODNOŚĆ:")
    if actual_calories != tdee_final:
        print(f"      Kalorie: spodziewano {tdee_final}, got {actual_calories}")
    if actual_protein != protein_expected:
        print(f"      Białko: spodziewano {protein_expected}, got {actual_protein}")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 3: Zmiana WAGI → przeliczenie makroskładników
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 3: Zmiana wagi (80 → 75 kg)")
print("-" * 80)

# Nowa waga: 75kg
# BMR = 10*75 + 6.25*180 - 5*25 + 5 = 750 + 1125 - 125 + 5 = 1755
bmr_new = 10 * 75 + 6.25 * 180 - 5 * 25 + 5
tdee_new = int(bmr_new * 1.55) - 400
protein_new = int(75 * 2.2)

print(f"Przy nowej wadze 75kg:")
print(f"  - BMR: {bmr_new} kcal")
print(f"  - TDEE (final): {tdee_new} kcal (oczekiwane)")
print(f"  - Białko: {protein_new}g (oczekiwane)")

# PUT aktualizacja
update_response = client.put("/app/profile", json={"weight": 75.0}, headers=headers)
assert update_response.status_code == 200, f"Błąd PUT: {update_response.status_code}"

updated_profile = update_response.json().get("profile", {})
updated_calories = updated_profile.get("calories_target", 0)
updated_protein = updated_profile.get("protein_target", 0)

print(f"\nPo PUT /app/profile:")
print(f"  - calories_target: {updated_calories} kcal")
print(f"  - protein_target: {updated_protein}g")

if updated_calories == tdee_new and updated_protein == protein_new:
    print(f"  ✅ KALORIE I BIAŁKO SIĘ ZAKTUALIZOWAŁY PRAWIDŁOWO!")
else:
    print(f"  ⚠️  NIEZGODNOŚĆ:")
    if updated_calories != tdee_new:
        print(f"     Kalorie: spodziewano {tdee_new}, got {updated_calories}")
    if updated_protein != protein_new:
        print(f"     Białko: spodziewano {protein_new}, got {updated_protein}")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 4: Zmiana GOAL (weight_loss → buildmass) → przeliczenie
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 4: Zmiana goal (weight_loss → buildmass)")
print("-" * 80)

# Goal = buildmass: TDEE + 300 (zamiast - 400)
# TDEE = 1755 * 1.55 = 2720
# Final = 2720 + 300 = 3020 kcal
tdee_buildmass_base = int(bmr_new * 1.55)
tdee_buildmass_final = tdee_buildmass_base + 300
# Białko (buildmass): 75 * 2.0 = 150g
protein_buildmass = int(75 * 2.0)

print(f"Przy goal = buildmass (i waga = 75kg):")
print(f"  - TDEE (final): {tdee_buildmass_final} kcal (oczekiwane)")
print(f"  - Białko: {protein_buildmass}g (oczekiwane)")

# PUT zmiana goal
goal_response = client.put("/app/profile", json={"goal": "buildmass"}, headers=headers)
assert goal_response.status_code == 200, f"Błąd PUT: {goal_response.status_code}"

goal_profile = goal_response.json().get("profile", {})
goal_calories = goal_profile.get("calories_target", 0)
goal_protein = goal_profile.get("protein_target", 0)

print(f"\nPo PUT /app/profile (goal=buildmass):")
print(f"  - calories_target: {goal_calories} kcal")
print(f"  - protein_target: {goal_protein}g")

if goal_calories == tdee_buildmass_final and goal_protein == protein_buildmass:
    print(f"  ✅ KALORIE I BIAŁKO SIĘ ZMIENIŁ PRAWIDŁOWO!")
else:
    print(f"  ⚠️  NIEZGODNOŚĆ:")
    if goal_calories != tdee_buildmass_final:
        print(f"     Kalorie: spodziewano {tdee_buildmass_final}, got {goal_calories}")
    if goal_protein != protein_buildmass:
        print(f"     Białko: spodziewano {protein_buildmass}, got {goal_protein}")

# ───────────────────────────────────────────────────────────────────────────────
# TEST 5: Zmiana FREQUENCY (3-4 → codziennie) → przeliczenie
# ───────────────────────────────────────────────────────────────────────────────
print("\n✅ TEST 5: Zmiana frequency (3-4 → codziennie)")
print("-" * 80)

# Frequency = codziennie: multiplier = 1.9
# TDEE = 1755 * 1.9 = 3335 kcal
# Final (buildmass) = 3335 + 300 = 3635 kcal
tdee_daily_base = int(bmr_new * 1.9)
tdee_daily_final = tdee_daily_base + 300

print(f"Przy frequency = codziennie (i goal = buildmass, waga = 75kg):")
print(f"  - TDEE (final): {tdee_daily_final} kcal (oczekiwane)")
print(f"  - Białko: {protein_buildmass}g (bez zmian, bo waga się nie zmieniła)")

# PUT zmiana frequency
freq_response = client.put("/app/profile", json={"frequency": "codziennie"}, headers=headers)
assert freq_response.status_code == 200, f"Błąd PUT: {freq_response.status_code}"

freq_profile = freq_response.json().get("profile", {})
freq_calories = freq_profile.get("calories_target", 0)
freq_protein = freq_profile.get("protein_target", 0)

print(f"\nPo PUT /app/profile (frequency=codziennie):")
print(f"  - calories_target: {freq_calories} kcal")
print(f"  - protein_target: {freq_protein}g")

if freq_calories == tdee_daily_final and freq_protein == protein_buildmass:
    print(f"  ✅ KALORIE I BIAŁKO SIĘ ZMIENIŁ PRAWIDŁOWO!")
else:
    print(f"  ⚠️  NIEZGODNOŚĆ:")
    if freq_calories != tdee_daily_final:
        print(f"     Kalorie: spodziewano {tdee_daily_final}, got {freq_calories}")
    if freq_protein != protein_buildmass:
        print(f"     Białko: spodziewano {protein_buildmass}, got {freq_protein}")

# ───────────────────────────────────────────────────────────────────────────────
# CLEANUP
# ───────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
with Session(engine) as session:
    test_user = session.get(UserDB, test_user_id)
    if test_user:
        logs = session.exec(select(DailyLogDB).where(DailyLogDB.user_id == test_user_id)).all()
        for log in logs:
            session.delete(log)
        session.delete(test_user)
        session.commit()
        print("✓ Test user usunięty z bazy")

print("=" * 80)
print("✅ TEST KALORIE & BIAŁKO — ZAKOŃCZONY")
print("=" * 80)
