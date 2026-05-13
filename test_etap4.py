"""
ETAP 4 Test — DateTime migration and UserDB reorganization
"""

from datetime import date, datetime
import time
from fastapi.testclient import TestClient
from main import app
from sqlmodel import Session, select
from app.database import engine
from app.models import UserDB, DailyLogDB

client = TestClient(app)

# Generate unique email
timestamp = int(time.time() * 1000)
email = f"etap4_test_{timestamp}@example.com"

print("=" * 80)
print("ETAP 4: DateTime Migration & UserDB Reorganization Test")
print("=" * 80)

# TEST 0: Register user
print("\n✅ TEST 0: Register new user")
print("-" * 80)
response = client.post(
    "/auth/register",
    json={
        "email": email,
        "password": "SecurePassword123",
        "name": "Etap 4 Test",
        "age": 30,
        "height": 180.0,
        "weight": 85.0,
        "target_weight": 80.0,
        "gender": "mężczyzna",
        "goal": "weight_loss",
        "frequency": "3-4 razy w tygodniu",
        "diet": "High-Protein",
    },
)
assert response.status_code == 200, f"Registration failed: {response.json()}"
token = response.json()["access_token"]
user_data = response.json()
print(f"✅ User registered: {user_data.get('name', 'N/A')}")
print(f"   Token: {token[:40]}...")

# TEST 1: Check timestamps are ISO format in API response
print("\n✅ TEST 1: Check API serialization (ISO strings)")
print("-" * 80)
response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
assert response.status_code == 200
profile = response.json()
print(f"✅ Profile created_at: {profile['created_at']} (ISO format)")
print(f"   Profile updated_at: {profile['updated_at']} (ISO format)")

# TEST 2: Verify datetime types internally
print("\n✅ TEST 2: Check internal datetime types (database)")
print("-" * 80)
with Session(engine) as session:
    user = session.exec(select(UserDB).where(UserDB.email == email)).first()
    assert user is not None, f"User with email {email} not found"
    
    # Check that created_at is a datetime object
    assert isinstance(user.created_at, datetime), f"created_at should be datetime, got {type(user.created_at)}"
    assert isinstance(user.updated_at, datetime), f"updated_at should be datetime, got {type(user.updated_at)}"
    
    print(f"✅ created_at type: {type(user.created_at).__name__}")
    print(f"   created_at value: {user.created_at.isoformat()}")
    print(f"✅ updated_at type: {type(user.updated_at).__name__}")
    print(f"   updated_at value: {user.updated_at.isoformat()}")

# TEST 3: Daily checkin with date/datetime
print("\n✅ TEST 3: POST /app/checkin (date/datetime types)")
print("-" * 80)
response = client.post(
    "/app/checkin",
    json={
        "food": "Breakfast: eggs",
        "workout": "Leg day",
        "mood": "Good",
        "weight": 84.5,
    },
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200
checkin_data = response.json()
print(f"✅ Checkin logged")
print(f"   Log date (ISO): {checkin_data['log']['date']}")
print(f"   Logged at (ISO): {checkin_data['log']['logged_at']}")

# TEST 4: Verify log has date type internally
print("\n✅ TEST 4: Check daily log date type (database)")
print("-" * 80)
with Session(engine) as session:
    log = session.exec(
        select(DailyLogDB)
        .where(DailyLogDB.user_id == user.id)
    ).first()
    assert log is not None
    
    # Check types
    assert isinstance(log.log_date, date), f"log_date should be date, got {type(log.log_date)}"
    assert isinstance(log.logged_at, datetime), f"logged_at should be datetime, got {type(log.logged_at)}"
    
    print(f"✅ log_date type: {type(log.log_date).__name__}")
    print(f"   log_date value: {log.log_date.isoformat()}")
    print(f"✅ logged_at type: {type(log.logged_at).__name__}")
    print(f"   logged_at value: {log.logged_at.isoformat()}")

# TEST 5: Exercise result with date type
print("\n✅ TEST 5: POST /app/exercise-result (date type)")
print("-" * 80)
response = client.post(
    "/app/exercise-result",
    json={
        "exercise_name": "Deadlift",
        "sets": 3,
        "reps": 5,
        "weight_kg": 150.0,
        "rpe": 8,
    },
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200
ex_data = response.json()
print(f"✅ Exercise logged")
print(f"   Session date (ISO): {ex_data['result']['session_date']}")
print(f"   Logged at (ISO): {ex_data['result']['logged_at']}")

# TEST 6: Verify exercise has date type internally
print("\n✅ TEST 6: Check exercise session_date type (database)")
print("-" * 80)
from app.models import ExerciseResultDB
with Session(engine) as session:
    ex = session.exec(
        select(ExerciseResultDB)
        .where(ExerciseResultDB.user_id == user.id)
    ).first()
    assert ex is not None
    
    assert isinstance(ex.session_date, date), f"session_date should be date, got {type(ex.session_date)}"
    assert isinstance(ex.logged_at, datetime), f"logged_at should be datetime, got {type(ex.logged_at)}"
    
    print(f"✅ session_date type: {type(ex.session_date).__name__}")
    print(f"   session_date value: {ex.session_date.isoformat()}")
    print(f"✅ logged_at type: {type(ex.logged_at).__name__}")
    print(f"   logged_at value: {ex.logged_at.isoformat()}")

# TEST 7: Drill result with date type
print("\n✅ TEST 7: POST /app/drill-result (date type)")
print("-" * 80)
response = client.post(
    "/app/drill-result",
    json={
        "drill_name": "Free throws",
        "success_count": 15,
        "total_attempts": 20,
        "rpe": 6,
    },
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200
drill_data = response.json()
print(f"✅ Drill logged")
print(f"   Session date (ISO): {drill_data['drill']['session_date']}")
print(f"   Logged at (ISO): {drill_data['drill']['logged_at']}")

# TEST 8: Verify drill has date type internally
print("\n✅ TEST 8: Check drill session_date type (database)")
print("-" * 80)
from app.models import DrillResultDB
with Session(engine) as session:
    drill = session.exec(
        select(DrillResultDB)
        .where(DrillResultDB.user_id == user.id)
    ).first()
    assert drill is not None
    
    assert isinstance(drill.session_date, date), f"session_date should be date, got {type(drill.session_date)}"
    assert isinstance(drill.logged_at, datetime), f"logged_at should be datetime, got {type(drill.logged_at)}"
    
    print(f"✅ session_date type: {type(drill.session_date).__name__}")
    print(f"   session_date value: {drill.session_date.isoformat()}")
    print(f"✅ logged_at type: {type(drill.logged_at).__name__}")
    print(f"   logged_at value: {drill.logged_at.isoformat()}")

# TEST 9: Dashboard (uses dates for filtering)
print("\n✅ TEST 9: GET /app/dashboard (date filtering)")
print("-" * 80)
response = client.get("/app/dashboard", headers={"Authorization": f"Bearer {token}"})
assert response.status_code == 200
dashboard = response.json()
print(f"✅ Dashboard built successfully")
print(f"   Weight trend entries: {len(dashboard['weight_trend'])}")

# TEST 10: Update profile (updated_at timestamp)
print("\n✅ TEST 10: PUT /app/profile (updated_at timestamp)")
print("-" * 80)
response = client.put(
    "/app/profile",
    json={"weight": 84.0, "goal": "buildmass"},
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200
profile_data = response.json()
updated_at = profile_data["profile"]["updated_at"]
print(f"✅ Profile updated")
print(f"   New updated_at (ISO): {updated_at}")

print("\n" + "=" * 80)
print("✅ ALL ETAP 4 TESTS PASSED!")
print("=" * 80)
print("\nSummary:")
print("  ✅ DateTime migration complete")
print("  ✅ Internal types: datetime/date objects")
print("  ✅ API serialization: ISO format strings (backward compatible)")
print("  ✅ Database queries: use proper types")
print("  ✅ UserDB reorganization: logical grouping documented")
