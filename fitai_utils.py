"""
fitai_utils.py — Most między botem Discord a bazą SQLite (fitai.db).

Architektura:
  • load_db()   → czyta WSZYSTKICH użytkowników z SQLite, zwraca dict {user_key: {...}}
  • save_db()   → zapisuje słownik użytkowników z powrotem do SQLite (upsert)
  • get_user()  → pobiera jednego użytkownika jako dict
  • save_user() → zapisuje/aktualizuje jednego użytkownika

Format słownika użytkownika jest identyczny z poprzednim formatem JSON,
więc bot Discord nie wymaga żadnych zmian po swojej stronie.

Nowy kod (API, endpointy) powinien używać sesji SQLModel bezpośrednio
przez fitai_api.engine — te helpery istnieją wyłącznie jako most dla bota.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select


# ─── Połączenie z bazą danych ─────────────────────────────────────────────────

_DB_URL = os.getenv("DATABASE_URL", "sqlite:///fitai.db")

# connect_args tylko dla SQLite — wymagane przy wielowątkowości (bot Discord)
_connect_args = {"check_same_thread": False} if _DB_URL.startswith("sqlite") else {}

engine = create_engine(_DB_URL, connect_args=_connect_args)


# ─── Leniwwy import modelu UserDB z fitai_api ─────────────────────────────────
# Importujemy model tylko gdy jest potrzebny, żeby uniknąć circular imports
# i nie wymagać od bota importowania całego FastAPI przy starcie.

def _get_user_model():
    """Zwraca klasę UserDB z fitai_api (lazy import)."""
    try:
        from fitai_api import UserDB  # noqa: PLC0415
        return UserDB
    except ImportError as exc:
        raise ImportError(
            "Nie można zaimportować UserDB z fitai_api.py. "
            "Upewnij się, że fitai_api.py jest w tym samym katalogu."
        ) from exc


# ─── Serializacja UserDB ↔ dict ───────────────────────────────────────────────
# Konwertuje rekord SQLModel na płaski słownik kompatybilny z formatem JSON,
# którego używał bot Discord (te same klucze co wcześniej w fitai_users.json).

_JSON_LIST_FIELDS = (
    "sports_json",
    "training_focus_json",
    "improvement_areas_json",
    "preferred_foods_json",
    "avoid_foods_json",
    "available_equipment_json",
    "avoid_exercises_json",
    "sport_training_days_json",
)

def _user_to_dict(user: Any) -> dict:
    """
    Serializuje obiekt UserDB do płaskiego słownika.

    Pola *_json zawierające listy są dekodowane do list Pythona.
    Klucze w wynikowym słowniku odpowiadają kluczom używanym przez bota Discord.
    """
    raw: dict = {}

    # Wszystkie kolumny skalarne przez SQLModel __fields__ / model_fields
    for field_name in user.model_fields:
        raw[field_name] = getattr(user, field_name, None)

    # Dekoduj pola JSON (przechowywane jako string) → list
    for json_field in _JSON_LIST_FIELDS:
        value = raw.get(json_field)
        short_key = json_field.removesuffix("_json")   # np. "sports_json" → "sports"
        if isinstance(value, str):
            try:
                raw[short_key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                raw[short_key] = []
        else:
            raw[short_key] = value or []

    # Dekoduj weekly_plan_json i diet_logs_json jeśli istnieją
    for plan_field in ("weekly_plan_json", "diet_logs_json"):
        value = raw.get(plan_field)
        if isinstance(value, str):
            try:
                raw[plan_field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                raw[plan_field] = {}

    return raw


def _dict_to_user(user_key: str, data: dict, UserDB: Any) -> Any:
    """
    Tworzy lub aktualizuje obiekt UserDB na podstawie słownika z bota.

    Pola list są kodowane z powrotem do JSON string przed zapisem do SQLite.
    """
    # Zakoduj listy → JSON string
    encoded: dict = {k: v for k, v in data.items()}
    for json_field in _JSON_LIST_FIELDS:
        short_key = json_field.removesuffix("_json")
        if short_key in encoded:
            encoded[json_field] = json.dumps(encoded.pop(short_key), ensure_ascii=False)

    # Zakoduj plany/logi jeśli przyszły jako dict/list
    for plan_field in ("weekly_plan_json", "diet_logs_json"):
        if plan_field in encoded and not isinstance(encoded[plan_field], str):
            encoded[plan_field] = json.dumps(encoded[plan_field], ensure_ascii=False)

    # Zbuduj obiekt UserDB — tylko pola istniejące w modelu
    valid_fields = set(UserDB.model_fields.keys())
    filtered = {k: v for k, v in encoded.items() if k in valid_fields}
    filtered["user_key"] = user_key

    return UserDB(**filtered)


# ─── Główny interfejs dla bota Discord ───────────────────────────────────────

def load_db() -> dict:
    """
    Wczytuje wszystkich użytkowników z fitai.db.

    Zwraca słownik w formacie:
        {
            "web:abc123": {"name": "Jan", "weight": 80, "sports": [...], ...},
            "discord:987654321": {"name": "Ania", ...},
            ...
        }
    Klucze to user_key (np. "web:<identity_id>" lub "discord:<user_id>").
    """
    UserDB = _get_user_model()
    try:
        with Session(engine) as session:
            users = session.exec(select(UserDB)).all()
            return {user.user_key: _user_to_dict(user) for user in users}
    except Exception as exc:
        print(f"[fitai_utils] load_db() błąd odczytu z SQLite: {exc}")
        return {}


def save_db(db: dict) -> None:
    """
    Zapisuje słownik użytkowników do fitai.db (upsert po user_key).

    Przyjmuje ten sam format co load_db():
        {
            "discord:123456": {"name": "Jan", "weight": 80, ...},
            ...
        }
    Istniejące rekordy są aktualizowane; nowe są tworzone.
    Rekordy nieobecne w `db` NIE są usuwane (bezpieczna operacja).
    """
    UserDB = _get_user_model()
    try:
        with Session(engine) as session:
            for user_key, data in db.items():
                existing = session.exec(
                    select(UserDB).where(UserDB.user_key == user_key)
                ).first()

                if existing:
                    # Aktualizacja: nadpisz tylko pola przekazane w data
                    valid_fields = set(UserDB.model_fields.keys())
                    for json_field in _JSON_LIST_FIELDS:
                        short_key = json_field.removesuffix("_json")
                        if short_key in data:
                            val = data[short_key]
                            setattr(
                                existing, json_field,
                                json.dumps(val, ensure_ascii=False)
                                if isinstance(val, (list, dict)) else val
                            )
                    for field, value in data.items():
                        if field in valid_fields and not field.endswith("_json"):
                            setattr(existing, field, value)
                    existing.updated_at = datetime.now().isoformat()
                    session.add(existing)
                else:
                    # Nowy użytkownik
                    new_user = _dict_to_user(user_key, data, UserDB)
                    new_user.updated_at = datetime.now().isoformat()
                    session.add(new_user)

            session.commit()
    except Exception as exc:
        print(f"[fitai_utils] save_db() błąd zapisu do SQLite: {exc}")


def get_user(user_id: str) -> dict | None:
    """
    Pobiera jednego użytkownika jako dict.

    `user_id` może być:
      • pełnym user_key: "discord:123456789" lub "web:abc123"
      • samym ID Discorda: "123456789"  (automatyczne dopasowanie prefiksu)

    Zwraca None jeśli użytkownik nie istnieje.
    """
    UserDB = _get_user_model()
    try:
        with Session(engine) as session:
            # Szukaj dokładnego dopasowania
            user = session.exec(
                select(UserDB).where(UserDB.user_key == str(user_id))
            ).first()

            # Fallback: spróbuj z prefiksem "discord:"
            if not user and not str(user_id).startswith(("web:", "discord:")):
                user = session.exec(
                    select(UserDB).where(UserDB.user_key == f"discord:{user_id}")
                ).first()

            return _user_to_dict(user) if user else None
    except Exception as exc:
        print(f"[fitai_utils] get_user({user_id!r}) błąd: {exc}")
        return None


def save_user(user_id: str, data: dict) -> None:
    """
    Zapisuje lub aktualizuje jednego użytkownika.

    `user_id` używany jest jako user_key jeśli nie zawiera prefiksu.
    Bot Discord powinien przekazywać "discord:<id>" dla spójności.
    """
    UserDB = _get_user_model()

    # Normalizacja klucza: gołe ID → dodaj prefiks discord:
    user_key = (
        str(user_id)
        if str(user_id).startswith(("web:", "discord:"))
        else f"discord:{user_id}"
    )

    try:
        with Session(engine) as session:
            existing = session.exec(
                select(UserDB).where(UserDB.user_key == user_key)
            ).first()

            if existing:
                valid_fields = set(UserDB.model_fields.keys())
                for json_field in _JSON_LIST_FIELDS:
                    short_key = json_field.removesuffix("_json")
                    if short_key in data:
                        val = data[short_key]
                        setattr(
                            existing, json_field,
                            json.dumps(val, ensure_ascii=False)
                            if isinstance(val, (list, dict)) else val
                        )
                for field, value in data.items():
                    if field in valid_fields and not field.endswith("_json"):
                        setattr(existing, field, value)
                existing.updated_at = datetime.now().isoformat()
                session.add(existing)
            else:
                new_user = _dict_to_user(user_key, data, UserDB)
                new_user.updated_at = datetime.now().isoformat()
                session.add(new_user)

            session.commit()
    except Exception as exc:
        print(f"[fitai_utils] save_user({user_key!r}) błąd: {exc}")


# ─── Nutrition calculations (niezmienione) ────────────────────────────────────

def calc_calories(profile: dict) -> int:
    """Mifflin-St Jeor + TDEE multiplier + goal adjustment."""
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