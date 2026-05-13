ETAP 3 — QUICK REFERENCE GUIDE
==============================

🚀 START DEV:
  cd c:\Users\adamz\OneDrive\Desktop\Projects\Training_coach
  python -m venv venv  (if needed)
  .\venv\Scripts\activate
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000
  → Open http://localhost:8000/docs

📊 TEST APP:
  python test_etap3_full.py
  → Expected: ✅ ALL ETAP 3 TESTS PASSED!

🗄️  DATABASE:
  # Apply migrations:
  alembic upgrade head
  
  # Create fresh DB:
  python -c "from app.database import create_db_and_tables; create_db_and_tables()"
  
  # Check DB:
  sqlite3 fitai.db ".tables"
  sqlite3 fitai.db "SELECT COUNT(*) FROM users;"

📁 PROJECT STRUCTURE:
  app/
    ├── auth/          (JWT, passwords, auth endpoints)
    ├── fitness/       (nutrition, workouts, profiles)
    ├── ai/            (LLM integration + endpoints)
    ├── health/        (health check)
    ├── config.py      (constants)
    ├── database.py    (SQLModel engine)
    ├── models.py      (ORM tables)
    └── schemas.py     (Pydantic validators)
  main.py            (FastAPI entry)
  alembic/           (DB migrations)

🔧 ADD NEW ENDPOINT:
  1. Define schema in app/schemas.py (if needed)
  2. Create/edit app/module/routes.py
     @router.post("/path")
     def handler(req: ReqSchema, user: UserDB = Depends(get_current_user)):
         ...
         return {...}
  3. Include in app/__init__.py:
     from app.module.routes import router as module_router
     app.include_router(module_router)
  4. Test in http://localhost:8000/docs

🧪 TEST ENDPOINT:
  python test_etap3_full.py
  OR use http://localhost:8000/docs (interactive API docs)

📈 MOST IMPORTANT FILES:
  ✨ app/fitness/calculations.py    (all nutrition math)
  ✨ app/fitness/routes.py          (main endpoints — NEW)
  ✨ app/ai/routes.py               (LLM endpoints — NEW)
  ✨ app/models.py                  (database schema)
  ✨ alembic/env.py                 (migration setup)

⚠️  COMMON ISSUES:
  Q: "Import error from app.auth"
  A: Make sure __init__.py files exist in each folder
  
  Q: "Database locked"
  A: Close other SQLite connections (VS Code's SQLite extension)
  
  Q: "Token expired" (in tests)
  A: Token lasts 7 days, tests usually OK if < 1 day old
  
  Q: "ModuleNotFoundError"
  A: Ensure you're in activated venv and requirements installed

📝 ETAP 3 DELIVERABLES:
  ✅ app/fitness/dashboard.py (142 linii)
  ✅ app/fitness/routes.py (290 linii)
  ✅ app/ai/service.py (118 linii)
  ✅ app/ai/routes.py (221 linii)
  ✅ alembic/versions/XXX.py (migration)
  ✅ test_etap3_full.py (11/11 tests ✅)
  ✅ ETAP_3_SUMMARY.md (detailed changes)
  ✅ ETAP_3_VISUAL_SUMMARY.md (visual guide)

🎯 KEY IMPROVEMENTS:
  ❌ 4450 lines in 1 file → ✅ 15 files with clear purposes
  ❌ 1 monolithic app → ✅ 21 working routes
  ❌ Manual DB updates → ✅ Alembic migrations
  ❌ No tests → ✅ 11 integration tests
  ❌ Hard to extend → ✅ Easy modular structure

🔗 URLS THAT WORK:
  GET  /health
  POST /auth/register
  POST /auth/login
  GET  /auth/me
  GET  /app/profile
  PUT  /app/profile
  GET  /app/dashboard
  POST /app/checkin
  POST /app/exercise-result
  POST /app/drill-result
  POST /app/sport-config
  POST /ai/diet
  POST /ai/workout
  POST /ai/weekly

💡 PRODUCTION DEPLOYMENT:
  1. Set env vars:
     - DATABASE_URL="sqlite:///fitai.db"
     - JWT_SECRET_KEY="32-char hex string"
     - GROQ_API_KEY="your key"
     - AI_PROVIDER="groq"
  
  2. Run migrations:
     alembic upgrade head
  
  3. Start:
     gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000

📊 STATISTICS:
  - Total routes: 21
  - Total files: 15 core modules + 4 test files
  - Total lines of code: ~4500 (same as before, but MUCH better organized)
  - Test coverage: 11/11 integration tests passing ✅
  - Database tables: 4 (users, daily_logs, exercise_results, drill_results)
  - API docs available at: /docs (Swagger UI) and /redoc

🎓 WHAT WAS DONE:
  ETAP 1: Fixed protein calc + macro recalc + anti-SPAM XP
  ETAP 2: Modularized 4450-line monolith into 15 files
  ETAP 3: Implemented remaining routes + AI + Alembic + tests ← YOU ARE HERE

SUMMARY: Production-ready FitAI backend! 🎉
