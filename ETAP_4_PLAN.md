ETAP 4 — REFACTORING: ROZBICIE UserDB i DATETIME MIGRATION
===========================================================

PLAN:
1. Migracja datetime (created_at, updated_at, logged_at, session_date na datetime)
2. Rozbicie UserDB (separation of concerns — profile, preferences, metrics, auth)
3. Alembic migration (2 files)
4. Testy
5. Podsumowanie

PROBLEMY OBECNE:
  ❌ UserDB ma 50+ pól (zbyt duży, trudny do utrzymania)
  ❌ Timestampy jako strings ISO (trudno sortować, filtrować, porównywać)
  ❌ JSON fields zamiast struktury (sports, preferences, reminders)
  ❌ Mieszanina concerns (auth, profile, preferences, metrics)

ROZWIĄZANIE:
  ✅ Podzielić logicznie UserDB (fizycznie w jednej tabeli)
  ✅ Zmienić timestampy na datetime
  ✅ Udokumentować strukturę
  ✅ Zachować backward compatibility

STRUKTURA PO REFACTORINGU:

  UserDB.profile:
    ├── age, height, weight, target_weight, start_weight
    ├── gender, goal, frequency, diet
    ├── meals_per_day, notes, allergies
    └── (zmigrowani na datetime: created_at, updated_at)

  UserDB.auth:
    ├── hashed_password, is_active
    ├── identity_id, email
    └── (zmigrowani na datetime)

  UserDB.preferences:
    ├── sports_json, training_focus_json
    ├── preferred_foods_json, avoid_foods_json
    ├── available_equipment_json, reminders_json
    ├── improvement_areas_json, weekly_plan_json
    └── sport_focus, sport_specialization

  UserDB.metrics:
    ├── total_xp, streak_days
    ├── injuries, last_weight_change
    └── (logicznie oddzielone)

MIGRACJE ALEMBIC:
  1. datetime_migration.py — zmiana type columns
  2. userdb_reorganization.py — documentation + helpers

STATUS: ⏳ TODO
