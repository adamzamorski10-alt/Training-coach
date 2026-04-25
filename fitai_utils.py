import json
import os
from pathlib import Path
from filelock import FileLock
from datetime import datetime

DATA_FILE = Path("fitai_users.json")
DB_LOCK = FileLock(f"{DATA_FILE}.lock")

def _load_db_unlocked() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def _save_db_unlocked(db: dict):
    temp_file = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, DATA_FILE)

def load_db() -> dict:
    with DB_LOCK:
        return _load_db_unlocked()

def save_db(db: dict):
    with DB_LOCK:
        _save_db_unlocked(db)

def get_user(user_id: str) -> dict | None:
    db = load_db()
    return db.get(str(user_id))

def save_user(user_id: str, data: dict):
    with DB_LOCK:
        db = _load_db_unlocked()
        db[str(user_id)] = data
        _save_db_unlocked(db)

def calc_calories(profile: dict) -> int:
    """Oblicza zapotrzebowanie kaloryczne (Mifflin-St Jeor / Harris-Benedict)."""
    w = profile.get("weight", 75)
    h = profile.get("height", 175)
    a = profile.get("age", 25)
    gender = str(profile.get("gender", "mężczyzna")).lower()

    if "kobieta" in gender or "female" in gender:
        bmr = 10 * w + 6.25 * h - 5 * a - 161
    else:
        bmr = 10 * w + 6.25 * h - 5 * a + 5

    freq = str(profile.get("frequency", "")).lower()
    multipliers = {
        "sedentaryczny": 1.2,
        "1-2": 1.375,
        "3-4": 1.55,
        "5-6": 1.725,
        "codziennie": 1.9,
    }
    
    mult = 1.2
    for key, val in multipliers.items():
        if key in freq:
            mult = val
            break

    tdee = int(bmr * mult)
    goal = str(profile.get("goal", "")).lower()
    if any(x in goal for x in ["redukcj", "odchudzani", "schud"]):
        tdee -= 400
    elif any(x in goal for x in ["masa", "budow", "przyty"]):
        tdee += 300
    return tdee

def calc_protein(profile: dict) -> int:
    w = profile.get("weight", 75)
    goal = str(profile.get("goal", "")).lower()
    if "masa" in goal:
        return int(w * 2.0)
    if "redukcj" in goal:
        return int(w * 2.2)
    return int(w * 1.6)