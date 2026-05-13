"""
Quick integration test for modularized app
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("=" * 80)
print("TEST: Modularized FitAI App Structure")
print("=" * 80)

# TEST 1: Health check
print("\n✅ TEST 1: GET /health")
print("-" * 80)
response = client.get("/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
assert response.status_code == 200
assert "status" in response.json()

# TEST 2: Auth register
print("\n✅ TEST 2: POST /auth/register")
print("-" * 80)
response = client.post(
    "/auth/register",
    json={
        "email": "test_etap2@example.com",
        "password": "SecurePassword123",
        "name": "Test User",
        "age": 25,
        "height": 180.0,
        "weight": 75.0,
        "target_weight": 70.0,
        "gender": "mężczyzna",
        "goal": "weight_loss",
        "frequency": "3-4 razy w tygodniu",
        "diet": "High-Protein",
    },
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"User ID: {result.get('user_id', 'N/A')}")
print(f"Token: {result.get('access_token', '')[:50]}...")
assert response.status_code == 200
token = result["access_token"]

# TEST 3: Auth me
print("\n✅ TEST 3: GET /auth/me (with token)")
print("-" * 80)
response = client.get(
    "/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Status: {response.status_code}")
profile = response.json()
print(f"Name: {profile.get('name')}")
print(f"Calories Target: {profile.get('calories_target')} kcal")
print(f"Protein Target: {profile.get('protein_target')}g")
assert response.status_code == 200

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED — Modularized App Structure OK")
print("=" * 80)
