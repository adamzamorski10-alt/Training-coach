# 📊 Analiza Kodu – FitAI v2.0+

## Spis treści
1. [Przegląd Architektury](#przegląd-architektury)
2. [Komponenty Systemu](#komponenty-systemu)
3. [Mocne Strony](#mocne-strony)
4. [Problemy i Zagrożenia](#problemy-i-zagrożenia)
5. [Techniczne Rekomendacje](#techniczne-rekomendacje)
6. [Rozwinięcie Funkcjonalności](#rozwinięcie-funkcjonalności)

---

## Przegląd Architektury

```
┌─────────────────────────────────────────────────────────────┐
│                      FitAI System                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Frontend   │  │   Bot        │  │  Mobile/API     │   │
│  │ (HTML/React) │  │ (Discord)    │  │  (REST)         │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘   │
│         │                  │                    │             │
│         └──────────────────┼────────────────────┘             │
│                            │ (HTTP/REST)                     │
│                   ┌────────▼─────────┐                       │
│                   │  FastAPI (v2.0)  │                       │
│                   │  - Auth (JWT)    │                       │
│                   │  - Rate Limit    │                       │
│                   │  - AI Router     │                       │
│                   └────────┬─────────┘                       │
│                            │                                 │
│        ┌───────────────────┼──────────────────┐              │
│        │                   │                  │              │
│   ┌────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐    │
│   │  SQLite     │  │  Groq API   │  │  Google Gemini │    │
│   │  (fitai.db) │  │  (Primary)  │  │  (Fallback AI) │    │
│   │  - Users    │  │             │  │                │    │
│   │  - Logs     │  │             │  │                │    │
│   │  - Exercises│  │             │  │                │    │
│   │  - Drills   │  │             │  │                │    │
│   └─────────────┘  └─────────────┘  └────────────────┘    │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ fitai_utils.py – Most JSON → SQLite dla Bota Discord  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Warstwa Bazy Danych

**Tabele SQLModel:**
- `users` – Profile użytkowników (54 pola)
- `daily_logs` – Dzienne wpisy (jedzenie, trening, nastrój, waga)
- `exercise_results` – Historia ćwiczeń (sets, reps, weight_kg, RPE)
- `drill_results` – Wyniki drilli sportowych (accuracy, time, distance)

**Indeksy:**
- `ix_daily_logs_user_date` – Najczęstszy pattern zapytań
- `ix_exercise_results_user_date` + `user_name` – Progresja
- `ix_drill_results_user_date` – Sport drills

---

## Komponenty Systemu

### 1. **Autentykacja i Autoryzacja** (`fitai_api.py: L85-165`)

```python
# JWT + PBKDF2 (stdlib, bez bcrypt)
- _hash_password()      → SHA-256 PBKDF2, 260k iteracji
- _verify_password()    → Bezpieczne porównanie hmac.compare_digest()
- _create_access_token() → JWT HS256, payload: {sub, email, role, exp, jti}
- get_current_user()    → Dependency do ochrony endpointów
- get_current_pro_user(), get_current_admin()
```

**Problemy:**
- ❌ Brak endpoint'ów do edycji profilu - `@app.post("/auth/me")` nie pozwala zmienić danych
- ⚠️ `hashed_password` może być `None` (backward compat z Netlify Identity) - ryzyka nie przejrzyste

### 2. **Modele ORM (SQLModel)**

**UserDB – 54 pola:**
- Bazowe: name, age, height, weight, start_weight, target_weight
- Cele: goal, frequency, diet, allergies, meals_per_day
- Preferencje: sports, training_focus, improvement_areas, preferred_foods, avoid_foods, available_equipment, avoid_exercises
- Sport: sport_focus, sport_specialization, sport_training_days
- Autoryzacja: hashed_password, is_active
- Gamifikacja: total_xp, injuries, last_weight_change
- Timestamps: created_at, updated_at (ISO format strings)
- JSON-encoded arrays: 8 pól (`*_json`)

**Helpers na UserDB:**
```python
get_list(field)      → Deserializes JSON string → list
set_list(field, value) → Serializes list → JSON string
get_dict(field)      → Deserializes JSON string → dict
set_dict(field, value) → Serializes dict → JSON string
to_profile_dict()    → Converts ORM → dict (backward compat)
```

**Potencjalny Problem:**
- ⚠️ Przy zwiększeniu liczby pól może być problema z migracją schematu
- ⚠️ JSON-encoded arrays mogą powodować problemy z wyszukiwaniem (brak indeksów na JSON)

### 3. **Daily Logs i Streaki** (`L1249-1270`)

```python
def _compute_streak_days_from_logs(logs: list[DailyLogDB]) -> int:
    # Liczy dni z rzędu od dzisiaj wstecz z unikalnym dates
    # Logika: jeśli log_date == expected → streak++, expected -= 1 dzień
    # Problem: Jeśli użytkownik zaloguje się o 23:59 a potem o 00:01, 
    #          mogą to być 2 różne dni i streak się zepsucie
```

### 4. **System XP i Poziomów** (`L1123-1165`)

```python
_XP_THRESHOLDS = [0, 100, 200, 300, ..., 1900]   # 20 poziomów
_XP_CHECKIN = 10
_XP_MEAL_LOGGED = 5
_XP_WEIGHT_LOGGED = 15
_XP_WORKOUT_LOGGED = 50       # ⚠️ Wysoko – może generować abuse
_XP_WATER_LOGGED = 5
_XP_STREAK_BONUS = 10 * days  # max 100 XP/dzień

_xp_to_level(total_xp) → zwraca poziom (1-20)
_xp_to_next_level(total_xp) → zwraca % progress do następnego
_award_xp(user, points, session) → dodaje XP i commituje
```

**Problemy:**
- ❌ Brak ochrony przed spam'iem (np. 100x `/app/checkin` na dzień)
- ⚠️ `_XP_WORKOUT_LOGGED = 50` to duża ilość – łatwo manipulować (zalogować fikcyjny trening)

### 5. **Progressive Overload** (`L1175-1245`)

```python
_suggest_progression(exercise_name, recent_results: list[ExerciseResultDB]) -> dict
  → Analizuje ostatnie 3 sesje
  → If avg_RPE ≤ 6 → sugeruj +2.5 kg
  → If avg_RPE ≥ 9 → utrzymaj ciężar, dodaj +1 rep
  → If 7-8 RPE → dodaj +1 rep

_check_overload(user_id, session, threshold_pct=0.20) -> dict
  → Porównuje wolumen (sets × reps × weight) między ostatnimi sesjami
  → Ostrzega jeśli wzrost > 20%
```

**Silne punkty:**
- ✅ RPE-based progression jest naukowy
- ✅ Overload detection chroni przed urazami

**Problemy:**
- ⚠️ Nie sprawdza technicznych błędów (forma ćwiczenia)
- ⚠️ Brak wsparcia dla ćwiczeń gdzie waga nie rośnie liniowo (calisthenics, cardio)

### 6. **Sport Drills Database** (`L1462-1675`)

```python
SPORT_DRILLS_DB = {
    "koszykówka": {
        "rzuty": [
            {"name": "Rzuty osobiste", "total_attempts": 20, ...},
            {"name": "Rzuty za 3 punkty", ...},
            ...
        ],
        "drybling": [...],
        "obrona": [...]
    }
}

_suggest_drill_progression(drill_name, recent_results) -> dict
  → Jeśli accuracy ≥70% i RPE ≤5 → sugeruj +5 prób
  → Jeśli accuracy ≥70% → progresja w górę
  → Else → utrzymaj, lepszy się trening
```

**Dobrze:**
- ✅ Struktura drill'i jest logiczna i łatwa do rozszerzenia
- ✅ Video URL dla każdego drilla

**Brakuje:**
- ❌ Brak struktur dla innych sportów (siatkówka, tenis, pływanie)
- ❌ Brak możliwości dodania custom drill'ów przez użytkownika

### 7. **Generowanie Planów Tygodniowych** (`L1675-2050`)

```python
_build_weekly_plan(user: UserDB) -> dict:
  1. Wczytaj katalog posiłków (bazowy, wegetariański, ketogenny)
  2. Wczytaj pulę ćwiczeń (~7 na każdą partię)
  3. Dla każdego dnia tygodnia:
     - Wyznacz typ dnia (heavy/moderate/rest) → Carb Cycling
     - Wybierz parte (klatka, plecy, nogi, itp.)
     - Wylosuj 4 ćwiczenia bez powtórzeń
     - Przypisz posiłki z filtrowaniem (preferred_foods, avoid_foods)
     - Wygeneruj alternatywy
  4. Zwróć plan JSON

_default_meal_catalog(diet: str) -> dict
  → 7+ dań na każdy slot (śniadanie, kolacja, itp.)
  → Dostępne opcje: standardowa, wegańska, ketogenna
  → Każde danie ma kalorie
```

**Silne punkty:**
- ✅ Carb Cycling (heavy/moderate/rest dni)
- ✅ Filtrowanie preferred/avoid foods
- ✅ Alternatywy dla każdego dania/ćwiczenia
- ✅ Każdy dzień ma inne zestawy (pseudo-random seed po tygodniu)

**Problemy:**
- ⚠️ Katalog dań jest hardcoded – trudne do rozszerzenia bez zmian kodu
- ⚠️ Brak wsparcia dla alergii w filtrowaniu
- ⚠️ Makra są "sztywne" – brak personalizacji po indywidualnym teście

### 8. **AI Integration** (`L1938-2050`)

```python
ask_ai(system: str, user_msg: str, max_tokens: int) -> str
  1. Try Groq (primary)
  2. If fails → Try Gemini (fallback)
  3. If both fail → Return _fallback_response()

_call_groq() → groq.chat.completions.create()
_call_gemini() → genai.GenerativeModel().generate_content()
_fallback_response() → Kontekstowy polski komunikat zastępczy
```

**Problemy:**
- ⚠️ Brak timeout'ów (API może wisieć)
- ⚠️ Brak retry logic (błędy sieciowe nie są obsługiwane)
- ❌ Brak cachingu wyników AI (każde powtórzenie = nowy API call)
- ⚠️ Rate limiting jest na poziomie użytkownika, ale AI endpoint mogą być slow

### 9. **Rate Limiting** (`L45-63`)

```python
slowapi (PySlowAPI)
limiter = Limiter(key_func=_rate_limit_key)

_rate_limit_key(request):
  → Jeśli Bearer token → użyj user_id (sub)
  → Else → użyj IP
  → Effect: Users behind NAT nie są wspólnie penalizowani

Defaults:
  AI_RATE_PER_MINUTE = "10/minute"
  AI_RATE_PER_HOUR = "50/hour"
```

**Dobrze:**
- ✅ Oddzielne limity dla AI callów
- ✅ Intelligent key function (user_id > IP)

**Problem:**
- ⚠️ Limity mogą być zbyt łaskawe dla free tier (50/hour = 6-7 dni pracy)
- ❌ Brak dedykowanych limitów dla drogich operacji (plan generation)

### 10. **Discord Bot** (`fitai_discord_bot.py`)

```python
@tree.command(name="fit", description="Główna komenda FitAI")
async def fit(interaction: discord.Interaction, akcja: str = "pomoc"):
  akcje:
    "profil"    → wyświetl profil embeda
    "raport"    → interaktywna forma do wpisu dziennego
    "dieta"     → plan diety na dziś od AI
    "trening"   → plan treningowy na dziś od AI
    "postepy"   → tygodniowe podsumowanie
    "cel"       → zmień cel
    "pomoc"     → lista komend
```

**Problemy:**
- ⚠️ Brak `setup` komend (profil jest tworzyć manualment)
- ⚠️ Brak walidacji przy wpisie dziennego raportu
- ⚠️ Embed'y nie są paginated (dlougie plany mogą być obcięte)

### 11. **Migracja JSON → SQLite** (`L567-620`)

```python
_migrate_json_to_sqlite():
  1. Szuka fitai_users.json
  2. Czyta stare dane
  3. Konwertuje listy → JSON strings
  4. Importuje do SQLite
  5. Tworzy flagę .json_migrated (one-time operation)
```

**Problemy:**
- ⚠️ Jeśli migracja się nie uda w połowie, brak rollback'u
- ⚠️ Brak walidacji danych (typy mogą się nie zgadzać)
- ❌ Stary JSON file nie jest usuwany (duplikacja danych)

### 12. **Testy** (`test_main.py`)

```python
Pokrycie:
  ✅ test_read_root()              – API up
  ✅ test_create_user()            – POST /users/{user_id}
  ✅ test_get_user_not_found()     – 404 handling
  ✅ test_add_log()                – POST /users/{user_id}/logs
  ✅ test_app_onboarding()         – POST /app/onboarding
  ✅ test_app_get_profile()        – GET /app/profile/{identity_id}
  ✅ test_app_generate_plan()      – POST /app/plan/{identity_id}/generate

Braki:
  ❌ Brak testów auth (login, register, token refresh)
  ❌ Brak testów exercise results
  ❌ Brak testów drill results
  ❌ Brak testów AI endpoints
  ❌ Brak testów rate limiting
  ❌ Brak testów streaka
  ❌ Brak testów XP system
  ❌ Brak testów Carb Cycling
```

---

## Mocne Strony

### 🟢 Architektura
1. **Czysty rozdział odpowiedzialności** – API, Bot, Utils, Models w osobnych plikach
2. **SQLModel + SQLAlchemy** – Type-safe ORM z validacją
3. **Composite indexing** – Optymalizacja zapytań dla typowych patternów
4. **One-time migration helper** – Bezpieczne przejście z JSON na SQLite

### 🟢 Bezpieczeństwo
1. **JWT + PBKDF2** – Bezpieczna autentykacja bez `bcrypt` (dependencies)
2. **Password hashing** – 260k iteracji SHA-256
3. **Rate limiting** – Chronienie przed DDoS i spam'em
4. **CORS configured** – Tylko zaufane originy
5. **Bearer scheme** – Standard OAuth/JWT

### 🟢 Funkcjonalność
1. **Progressive Overload** – RPE-based sugestie dla postępu
2. **Carb Cycling** – Dynamiczne makra (heavy/moderate/rest dni)
3. **XP/Leveling** – Gamifikacja dla engagementu
4. **Sport Drills** – Specjalny moduł dla sportowców
5. **AI Integration** – Groq + Gemini (fallback)
6. **Meal Planning** – Personalizacja (diet type, alergeny)
7. **Discord Integration** – Dostęp z bota

### 🟢 Kod
1. **Komentarze po polsku** – Łatwy dla zespołu
2. **Type hints** – Mypy-compatible
3. **Docstrings** – Wyjaśnienia dla endpointów
4. **Error handling** – Fallback responses, 404s, validation

---

## Problemy i Zagrożenia

### 🔴 Krytyczne

| Problem | Lokalizacja | Wpływ | Naprawa |
|---------|------------|-------|--------|
| **Brak rate limitingu na XP endpoints** | `_award_xp()` | Użytkownik może "spam'ować" checkin'i i zyskać 1000 XP/dzień | Dodać `@limiter.limit("5/minute")` na `/app/checkin` i `/app/water` |
| **AI timeout – brak fallback timeout** | `_call_groq()`, `_call_gemini()` | API może wisieć 30 sekund → timeout klienta | `response = groq.chat.completions.create(..., timeout=10)` |
| **SQL Injection w drill name** | `_suggest_drill_progression()` | Jeśli drill name pochodzi z user input bez sanityzacji | Użyć parametrized queries (SQLModel robi to automatycznie) – ale sprawdzić |
| **Passwords stored in plain text dla old users** | `UserDB.hashed_password = None` | Stare konta z Netlify Identity mogą mieć plain text | Wymusić reset hasła dla `hashed_password IS NULL` |
| **Brak versioning API** | `/app/profile` | Zmiany scheatu mogą złamać frontenda | Dodać `/v1/`, `/v2/` prefiksy |

### 🟡 Wysokie

| Problem | Lokalizacja | Wpływ | Naprawa |
|---------|------------|-------|--------|
| **Brak testów dla 80% funkcjonalności** | `test_main.py` | Nieznane regression'y, production bugs | Pisać testy dla auth, exercises, drills |
| **Migracja JSON bez rollback** | `_migrate_json_to_sqlite()` | Jeśli migracja się zepsuje, dane mogą być stracone | Dodać transaction + rollback, backup JSON |
| **Streak logika może być wyłamana** | `_compute_streak_days_from_logs()` | Jeśli użytkownik zaloguje się 2x w jednym dniu, może być double count | Zdeduplikować po `(user_id, log_date)` zamiast po ID logu |
| **No caching for AI responses** | `ask_ai()` | Powtórzenie tego samego query = nowy API call → $$ | Redis/Memcached cache z TTL 24h |
| **Hardcoded meal catalog** | `_default_meal_catalog()` | Ograniczona rozszerzalność, brak custom diet'ów | Przenieść do DB, UI do edycji |
| **Sport drills są hardcoded** | `SPORT_DRILLS_DB` | Tylko koszykówka – brak siatkówki, tenisa, itp. | Przenieść do DB, API do CRUD |
| **XP values nie są balansowe** | `_XP_WORKOUT_LOGGED = 50` | Zalogowanie zmyślonego treningu = +50 XP łatwo manipulować | Wymagać verify (potwierdzenie przez coach lub metrics) |

### 🟠 Średnie

| Problem | Lokalizacja | Wpływ | Naprawa |
|---------|------------|-------|--------|
| **Brak edycji profilu** | Auth endpoints | User musi stworzyć nowy profil żeby zmienić wiek | Dodać `@app.patch("/app/profile")` |
| **JSON encoding dla pól nie jest indeksowany** | `sports_json`, `training_focus_json`, itp. | Zapytania `WHERE sports CONTAINS 'bieganie'` są slow | Użyć JSONB (PostgreSQL) albo normalizować na oddzielne tabele |
| **Brak proper error messages** | Cały kod | User nie wie co poszło nie tak | Standardowy format errors: `{"error": "code", "message": "...", "details": {...}}` |
| **created_at, updated_at jako strings** | `UserDB.created_at` | Trudnie porównanie czasów, nie można sortować po dacie | Zmienić na `datetime` z timezone |
| **Brak soft delete'ów** | Database | Jeśli user się wyloguje/usunie, dane są stracone | Dodać `is_deleted` flag i `deleted_at` timestamp |
| **Bot nie sprawdza czy user ma profile** | Discord Bot | `/fit raport` dla user'a bez profile zwraca dziwny error | Zwrócić user-friendly message z linkiem do setup |
| **No pagination for long lists** | `/app/exercise-history` | Jeśli użytkownik ma 1000 exercise result'ów, zwracamy wszystkie | Dodać limit/offset i cursor-based pagination |

### 🟢 Niskie

| Problem | Lokalizacja | Wpływ | Naprawa |
|---------|------------|-------|--------|
| **Liczba pól w UserDB = 54** | `UserDB` | Model jest duży, trudny do maintenance | Podzielić: UserProfile, UserPreferences, UserGameification |
| **Brak OpenAPI docs** | FastAPI | Dev'erzy nie wiedzą co endpointy robią | `app.title = "FitAI"` + comment docstring = auto docs w `/docs` |
| **Brak structured logging** | Everywhere | Debug'owanie produkcji jest ciężkie | Dodać `logging` module, info level dla key events |
| **Bez connection pooling w SQLite** | `engine = create_engine()` | SQLite nie robi pooling domyślnie | Dodać `NullPool` albo przejść na PostgreSQL dla production |
| **Bez health check endpoint** | API | LB nie wie czy API jest żywe | Dodać `@app.get("/health")` + db ping |

---

## Techniczne Rekomendacje

### Priority 1 (ASAP – do 1 tygodnia)

#### 1.1 Add Rate Limiting na XP Endpoints
```python
@app.post("/app/checkin")
@limiter.limit("5/minute")  # ← DODAJ
def app_checkin(payload: AppDailyCheckinRequest, user: UserDB = Depends(get_current_user)):
    ...
```

#### 1.2 Add AI Timeouts
```python
# W _call_groq():
response = _groq_client.chat.completions.create(
    ...,
    timeout=10  # ← DODAJ
)

# W _call_gemini():
response = genai.GenerativeModel(...).generate_content(
    ...,
    timeout=10   # ← DODAJ
)
```

#### 1.3 Fix Streak Logic
```python
# Zmień _compute_streak_days_from_logs() aby deduplikować po dacie:
unique_dates = sorted(set(l.log_date for l in logs if l.log_date), reverse=True)
# Zamiast:
unique_days = sorted({l.log_date for l in logs if l.log_date}, reverse=True)
```

#### 1.4 Require Password Reset for Old Users
```python
@app.on_event("startup")
def on_startup():
    ...
    # Check for users z hashed_password = None
    with Session(engine) as session:
        old_users = session.exec(
            select(UserDB).where(UserDB.hashed_password == None)
        ).all()
        if old_users:
            print(f"[Warning] {len(old_users)} users with no hashed_password")
```

### Priority 2 (do 2 tygodni)

#### 2.1 Add Comprehensive Tests
```bash
pytest test_main.py -v --cov=fitai_api --cov-report=html
# Target: >80% coverage
```

**Nowe testy:**
- `test_auth_register_login_refresh()` – JWT flow
- `test_exercise_progression()` – RPE logic
- `test_carb_cycling_macros()` – Macro calculation
- `test_rate_limiting()` – Limiter behavior
- `test_ai_fallback()` – Groq + Gemini fallback

#### 2.2 API Versioning
```python
app = FastAPI(title="FitAI API", version="2.0")

# Zmień routes:
# /app/profile          → /v2/app/profile
# /auth/register        → /v2/auth/register
# /users/{user_id}      → /v2/users/{user_id}
```

#### 2.3 Add Health Check
```python
@app.get("/health", tags=["system"])
def health_check():
    try:
        with Session(engine) as session:
            session.exec(select(1))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}, 503
```

#### 2.4 Centralized Error Handling
```python
class ErrorResponse(BaseModel):
    error: str          # error code: "invalid_input", "not_found", "unauthorized"
    message: str        # human-readable message
    details: dict = {}  # Additional context

@app.exception_handler(ValueError)
def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_input", "message": str(exc)},
    )
```

### Priority 3 (do 1 miesiąca)

#### 3.1 Move Catalog to Database
```python
# Nowe tabele:
class MealDB(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    slot: str            # "Śniadanie", "Obiad", itp.
    diet_type: str       # "standardowa", "wegetariańska", "ketogenna"
    name: str
    kcal: int
    ingredients: str = ""
    created_by: str = "system"  # admin or user_id
    is_active: bool = True
    
# API endpoints:
@app.post("/v2/meals", tags=["admin"])
def create_meal(data: MealCreateRequest, user: UserDB = Depends(get_current_admin)):
    ...

@app.get("/v2/meals", tags=["data"])
def list_meals(diet_type: str = None):
    ...
```

#### 3.2 Sport Drills → Database
```python
class SportDrillDB(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=..., primary_key=True)
    sport: str           # "koszykówka", "siatkówka", itp.
    specialization: str  # "rzuty", "drybling", itp.
    drill_name: str
    total_attempts: int  # baseline
    description: str
    progression_tip: str
    video_url: Optional[str] = None
    created_by: str
    is_active: bool = True
```

#### 3.3 User Profile Edit Endpoint
```python
@app.patch("/v2/app/profile", tags=["profile"])
def update_profile(
    updates: UserProfileUpdate,  # zawiera TYLKO pola do aktualizacji
    user: UserDB = Depends(get_current_user)
):
    with Session(engine) as session:
        user = session.get(UserDB, user.id)
        for field, value in updates.dict(exclude_unset=True).items():
            if field in UserDB.model_fields:
                setattr(user, field, value)
        user.updated_at = datetime.now().isoformat()
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.to_profile_dict()
```

#### 3.4 AI Response Caching
```python
import hashlib

def _cache_key(system: str, user_msg: str) -> str:
    return hashlib.md5(f"{system}:{user_msg}".encode()).hexdigest()

# Pseudo-code Redis:
def ask_ai_cached(system: str, user_msg: str, max_tokens: int = 800) -> str:
    key = _cache_key(system, user_msg)
    cached = redis_client.get(key)
    if cached:
        return cached
    
    result = ask_ai(system, user_msg, max_tokens)
    redis_client.setex(key, 86400, result)  # 24h TTL
    return result
```

### Priority 4 (do 2-3 miesięcy)

#### 4.1 Split UserDB into Smaller Models
```python
class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_key: str = Field(unique=True)
    email: str = Field(unique=True)
    name: str
    hashed_password: Optional[str]
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserProfile(SQLModel, table=True):
    id: str = Field(primary_key=True, foreign_key="user.id")
    age: int
    height: float
    weight: float
    goal: str
    # ... 20 pól

class UserPreferences(SQLModel, table=True):
    user_id: str = Field(foreign_key="user.id")
    sports: list[str]  # JSONB lub relation
    preferred_foods: list[str]
    avoid_foods: list[str]
    # ...

class UserGameification(SQLModel, table=True):
    user_id: str = Field(foreign_key="user.id")
    total_xp: int
    streak_days: int
    injuries: list[str]
    # ...
```

#### 4.2 PostgreSQL Migration (dla production)
```bash
# SQLite → PostgreSQL
1. Export data z SQLite
2. Zmień DATABASE_URL = "postgresql://user:pass@localhost/fitai"
3. Dodaj connection pooling: Psycopg2 + pgBouncer
4. Reindex composite indexes
```

#### 4.3 Async Support
```python
# Zmień na async endpoints:
@app.post("/app/checkin", tags=["checkin"])
async def app_checkin(payload: AppDailyCheckinRequest, user: UserDB = Depends(get_current_user)):
    # Zwraca szybciej dzięki async I/O
    ...
```

---

## Rozwinięcie Funkcjonalności

### 🚀 Funkcje do Dodania

1. **Social Features**
   - Competitions (tygodniowe, co najczęściej ćwiczy)
   - Friend lists + activity sharing
   - Leaderboards (global, by sport, by XP)

2. **Advanced Analytics**
   - 1RM estimation (z RPE + reps)
   - Strength deficit analysis
   - Recovery metrics (HRV, sleep tracking integration)
   - Body composition tracking (BodPod, DEXA)

3. **Nutrition**
   - Meal logging z photo recognition (ML)
   - Barcode scanning (UPC)
   - Macro tracking history
   - Restaurant menu integration

4. **Mobile App**
   - React Native (iOS/Android)
   - Offline support (SQLite local)
   - Camera dla workout logging
   - Notifications (na o6:00 "czas na trening!")

5. **Coach Portal**
   - Assign plans to multiple clients
   - Review logs + give feedback
   - Billing integration (Stripe)
   - Analytics dashboard

6. **Integrations**
   - Fitbit / Apple Watch (calorie burn data)
   - Strava (running/cycling)
   - MyFitnessPal (food import)
   - Notion (workout notes export)

---

## Checklist Produkcji

- [ ] Rate limiting na wszystkich user-facing endpoints
- [ ] Tests >80% coverage
- [ ] Health check endpoint
- [ ] Structured logging
- [ ] Backup strategy dla DB
- [ ] Error tracking (Sentry)
- [ ] API documentation (Swagger `/docs`)
- [ ] Security audit (OWASP Top 10)
- [ ] Performance testing (load, stress)
- [ ] Database migration strategy (Alembic)
- [ ] CD/CI pipeline (GitHub Actions, GitLab CI)
- [ ] Monitoring (datadog, New Relic)
- [ ] Incident response plan

---

**Ostatnia aktualizacja:** 5 maja 2026  
**Autor:** Automatyczna analiza  
**Wersja API:** 2.0+
