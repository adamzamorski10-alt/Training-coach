# Raport Audytowy FitAI / Training_coach — Architektura, Bezpieczeństwo, UX/UI i Roadmapa Produkcyjna

**Wersja:** 1.0 · **Data analizy:** 13.06.2026 · **Zakres:** backend FastAPI/SQLModel (Render), frontend SPA (GitHub Pages PWA)

---

## Streszczenie wykonawcze

Projekt FitAI jest na bardzo solidnym etapie technicznym — architektura danych jest poprawna, izolacja per-użytkownik działa, system XP/streak działa, a Service Worker jest napisany na poziomie produkcyjnym (network-first z timeoutem, background sync, force-update). Mimo to znalazłem **jeden krytyczny błąd bezpieczeństwa, który nadal nie został naprawiony** (`JWT_SECRET_KEY` generowany losowo przy każdym restarcie — patrz Sekcja 3.1), oraz kilka architektonicznych decyzji wymagających poprawy przed komercjalizacją: brak `AUTOINCREMENT` dla `user_number` (Sekcja 2.1), `cdn.tailwindcss.com` w produkcji (Sekcja 5), brak rozróżnienia Access/Refresh tokenu (Sekcja 3.2).

---

## Sekcja 1 — Głęboki audyt kodu i krytyczne błędy

### 1.1 Blokowanie bazy SQLite (Concurrency / Database Locks)

**Stan faktyczny:** `database.py` konfiguruje silnik tak:

```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)
```

`check_same_thread: False` rozwiązuje tylko problem wątków — **nie rozwiązuje problemu współbieżnych zapisów**. SQLite domyślnie używa trybu `journal_mode=DELETE`, w którym każdy zapis blokuje cały plik bazy na czas transakcji. Pod FastAPI z wieloma równoległymi requestami (np. dwóch użytkowników klika "Zapisz dzień" w tej samej milisekundzie), drugi request dostanie:

```
sqlite3.OperationalError: database is locked
```

Ponieważ `daily_checkin`, `toggle_day_item`, `app_log_water` i `log_drill_result` wszystkie wykonują `session.commit()` synchronicznie w endpointach FastAPI (zdefiniowanych jako `def`, nie `async def` — FastAPI uruchamia je w threadpoolu, więc równoległość jest realna), ryzyko blokady rośnie proporcjonalnie do liczby aktywnych użytkowników.

**Rekomendacja — włącz WAL mode.** To jedna zmiana, ogromny zysk:

```python
# app/database.py
from sqlalchemy import event

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")  # czekaj 5s zamiast crashować
        cursor.close()
```

`WAL` (Write-Ahead Logging) pozwala na **równoczesne odczyty podczas zapisu** — drastycznie redukuje "database is locked". `busy_timeout=5000` jest siatką bezpieczeństwa: jeśli mimo WAL dojdzie do kolizji, SQLite czeka 5s zamiast natychmiast rzucać wyjątek.

**Dla skali >50 aktywnych użytkowników jednocześnie** — rozważ PostgreSQL (Render ma darmowy plan). SQLModel/SQLAlchemy nie wymaga zmian w kodzie poza `DATABASE_URL`.

---

### 1.2 Exception Handling i odporność na parsowanie LLM

`app/fitness/routes.py` ma solidny wzorzec `try/except SQLAlchemyError`, np. `get_exercise_history`, `app_log_water`, `log_drill_result`, `get_drill_history`. `get_drill_history` ma nawet podwójny fallback (`except SQLAlchemyError` + `except Exception`) żeby **nigdy nie zwrócić 500** — zawsze `{"results": [], "progressions": {}}`. To bardzo dobry wzorzec defensywny.

**Brakujący element — parsowanie odpowiedzi LLM.** Typowy problem: model LLM owija JSON w markdown:

````
```json
{"plan": {...}}
```
````

Jeśli kod robi `json.loads(response_text)` bezpośrednio, **to się wywali** na fence-prefixie. Rekomendowana funkcja pomocnicza (jeśli jeszcze nie istnieje w `app/ai/`):

```python
import json
import re

def extract_json_from_llm(raw_text: str) -> dict:
    """Wyciąga JSON z odpowiedzi LLM, odporny na markdown fences i preambuły."""
    text = raw_text.strip()

    # 1. Usuń markdown code fences ```json ... ``` lub ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    # 2. Jeśli model dodał tekst przed/po JSON-em — wyciągnij od pierwszego { do ostatniego }
    if not fence_match:
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # 3. Ostatnia szansa — usuń trailing commas (częsty błąd LLM)
        text_fixed = re.sub(r",(\s*[\}\]])", r"\1", text)
        try:
            return json.loads(text_fixed)
        except json.JSONDecodeError:
            raise ValueError(f"Nie można sparsować JSON z odpowiedzi LLM: {exc}\nTekst: {text[:200]}")
```

Każde wywołanie modelu AI które zwraca JSON powinno przechodzić przez tę funkcję, owinięte w `try/except ValueError` z fallbackiem (np. zwrotem domyślnego planu lub komunikatem "AI jest chwilowo przeciążone, spróbuj ponownie").

---

### 1.3 Wycieki pamięci i synchronizacja DOM (przełączanie zakładek)

Dla architektury "jedna funkcja przełącza widoczność N paneli", typowe pułapki:

1. **Event listenery dodawane wielokrotnie** — jeśli funkcja przełączająca zakładki jest wywoływana co każde przełączenie i wewnątrz robi `element.addEventListener(...)` bez wcześniejszego `removeEventListener`, listenery się kumulują. Po 20 przełączeniach zakładek jeden klik wywołuje handler 20 razy.

   **Test diagnostyczny:** w konsoli przeglądarki:
   ```js
   getEventListeners(document.getElementById('save-day-btn'))
   ```
   Jeśli liczba rośnie z każdym przełączeniem zakładki — to jest ten problem.

   **Fix:** deleguj eventy na stały, nadrzędny element (event delegation) zamiast podpinać listenery przy każdym przełączeniu:
   ```js
   // Raz, przy starcie — nie w funkcji przełączającej zakładki
   document.getElementById('app-root').addEventListener('click', function(e) {
     const btn = e.target.closest('[data-action]');
     if (!btn) return;
     const action = btn.dataset.action;
     if (action === 'save-day') saveDayData();
     if (action === 'toggle-item') toggleItem(btn.dataset.itemId, btn.dataset.itemType, btn.dataset.checked !== 'true');
     // ...
   });
   ```

2. **`innerHTML = ''` na rodzicu nie usuwa referencji JS** — jeśli gdzieś trzymasz `window._chartInstance = new Chart(...)` i przy przełączeniu zakładki robisz `canvas.remove()` bez `chartInstance.destroy()`, Chart.js zostawia listenery resize na `window` — to realny memory leak przy częstym przełączaniu między zakładką Postępy (wykresy) i innymi.

   **Fix — zawsze przed ponownym renderowaniem wykresu:**
   ```js
   function renderWeightChart(data) {
     if (window._weightChart) {
       window._weightChart.destroy();
       window._weightChart = null;
     }
     const ctx = document.getElementById('weight-chart')?.getContext('2d');
     if (!ctx) return;
     window._weightChart = new Chart(ctx, { /* ... */ });
   }
   ```

3. **`setInterval`/`setTimeout` bez `clearInterval`** — np. jeśli "Mój Dzień" ma auto-refresh `setInterval(loadTodayData, 30000)`, a użytkownik przełącza zakładki 10 razy, masz 10 równoległych interwałów odpytujących `/app/day/today`. To generuje niepotrzebny ruch sieciowy i może powodować "migotanie" UI gdy dwa interwały renderują dane w różnym czasie.

   **Fix:**
   ```js
   let _dayRefreshInterval = null;
   function startDayAutoRefresh() {
     if (_dayRefreshInterval) clearInterval(_dayRefreshInterval);
     _dayRefreshInterval = setInterval(loadTodayData, 30000);
   }
   function stopDayAutoRefresh() {
     if (_dayRefreshInterval) { clearInterval(_dayRefreshInterval); _dayRefreshInterval = null; }
   }
   ```

**Plik do wysłania AI dla naprawy:** `index.html` (cała sekcja `<script>` odpowiedzialna za przełączanie zakładek — poproś AI o wyszukanie wszystkich `setInterval`, `addEventListener` poza event delegation, i `new Chart(`).

---

## Sekcja 2 — Baza danych i system `user_number`

### 2.1 Czy generowanie `user_number` jest bezpieczne produkcyjnie?

Mechanizm rejestracji (`auth/routes.py`, funkcja `register`):
```python
max_number_row = session.exec(
    select(UserDB.user_number)
    .where(UserDB.user_number.is_not(None))
    .order_by(UserDB.user_number.desc())
).first()
next_number = (max_number_row or 0) + 1

user = UserDB(..., user_number=next_number, ...)
session.add(user)
session.commit()
```

**To JEST podatne na race condition.** Scenariusz:

| Czas | Request A (user X) | Request B (user Y) |
|------|---------------------|----------------------|
| T0 | `SELECT MAX(user_number)` → 47 | |
| T1 | | `SELECT MAX(user_number)` → 47 (jeszcze nie skomitowane A) |
| T2 | `next_number = 48`, `INSERT user_number=48` | |
| T3 | `commit()` → sukces | |
| T4 | | `next_number = 48`, `INSERT user_number=48` |
| T5 | | `commit()` → **UniqueViolation / IntegrityError** (bo `user_number` ma `unique=True`) |

**Co się dzieje w obecnym kodzie przy tym konflikcie?** `register()` ma `except IntegrityError: raise HTTPException(409, "Konto z tym e-mailem już istnieje")`. **To jest błędny komunikat** — w tym scenariuszu e-mail NIE jest duplikatem, duplikatem jest `user_number`. Użytkownik B dostanie fałszywy komunikat "konto już istnieje" mimo że jego e-mail jest unikalny, i rejestracja się nie powiedzie mimo że powinna.

**Czy to się zdarzy w praktyce?** Przy małej skali (kilkanaście rejestracji dziennie) szansa na dokładnie taki "dead heat" jest niska, ale nie zerowa — zwłaszcza jeśli dwie osoby klikają "Zarejestruj" w tym samym momencie po np. wspólnej promocji/linku w grupie.

#### Rozwiązanie A — natywny AUTOINCREMENT (rekomendowane)

SQLite ma wbudowany, w 100% atomowy autoincrement dla `INTEGER PRIMARY KEY`. Problem: `id` w `UserDB` to już `str` (UUID), nie możemy zrobić `user_number` drugim primary key w SQLite/SQLModel bezpośrednio. Rozwiązaniem jest **osobna tabela-licznik** z `INTEGER PRIMARY KEY AUTOINCREMENT`, z której "pożyczamy" numer atomowo:

```python
# app/models.py — nowa tabela pomocnicza
class UserNumberSequenceDB(SQLModel, table=True):
    __tablename__ = "user_number_sequence"
    id: Optional[int] = Field(default=None, primary_key=True)  # AUTOINCREMENT w SQLite
    user_id: str = Field(foreign_key="users.id", unique=True)
```

```python
# app/auth/routes.py — w register(), zamiast MAX()+1:
session.add(user)
session.flush()  # user.id jest już dostępne, ale jeszcze nie skomitowane

seq_row = UserNumberSequenceDB(user_id=user.id)
session.add(seq_row)
session.flush()  # tu SQLite atomowo nadaje seq_row.id = N (AUTOINCREMENT)

user.user_number = seq_row.id
session.commit()
session.refresh(user)
```

**Dlaczego to jest atomowe:** `AUTOINCREMENT` w SQLite jest realizowany na poziomie silnika bazy z własnym blokowaniem `sqlite_sequence` — **dwa równoczesne INSERT-y do tej samej tabeli z AUTOINCREMENT nigdy nie dostaną tego samego ID**, niezależnie od poziomu izolacji transakcji. To jest dokładnie ten sam mechanizm co `SERIAL`/`IDENTITY` w PostgreSQL.

#### Rozwiązanie B — retry z exponential backoff (szybszy patch, mniej elegancki)

Jeśli nie chcesz dodawać nowej tabeli, opakuj `register()` w retry:

```python
import time

MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    max_number_row = session.exec(
        select(UserDB.user_number)
        .where(UserDB.user_number.is_not(None))
        .order_by(UserDB.user_number.desc())
    ).first()
    next_number = (max_number_row or 0) + 1
    user.user_number = next_number
    user.user_key = f"native:user:{next_number}"
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
        break
    except IntegrityError as exc:
        session.rollback()
        # Sprawdź czy konflikt to email czy user_number
        existing_email = session.exec(
            select(UserDB).where(UserDB.email == payload.email.lower().strip())
        ).first()
        if existing_email:
            raise HTTPException(409, detail="Konto z tym e-mailem już istnieje")
        if attempt == MAX_RETRIES - 1:
            raise HTTPException(500, detail="Nie udało się przydzielić numeru — spróbuj ponownie")
        time.sleep(0.05 * (attempt + 1))  # 50ms, 100ms, 150ms
        continue
```

**Rekomendacja:** Rozwiązanie A (sekwencja AUTOINCREMENT) — jest deterministyczne, bez retry-loop, i jest to **dokładnie ten wzorzec który stosuje PostgreSQL natywnie**, więc jeśli kiedyś migrujesz na Postgres, po prostu zamieniasz `UserNumberSequenceDB` na kolumnę `SERIAL` bezpośrednio w `users`.

#### Backfill numerów dla starych kont — analiza

Funkcja wykonująca się przy starcie (jednorazowy backfill, sekwencyjnie w jednej transakcji `with engine.connect() as conn`) jest **poprawna logicznie** dla scenariusza startowego. Ponieważ wykonuje się **synchronicznie przy starcie aplikacji, przed przyjęciem pierwszego requestu**, nie ma tu race condition — tylko jeden proces ma dostęp w tym momencie.

**Jedyne ryzyko:** jeśli używasz Render z **więcej niż jednym workerem/instancją** (`--workers 2` lub autoscaling), funkcja tworząca tabele (a więc i backfill) wykona się **w każdym workerze niezależnie przy starcie**. Pierwszy worker przydzieli numery 1-10 starym kontom, drugi worker — startujący milisekundy później — zobaczy że nie ma już wierszy bez numeru (bo worker 1 skomitował) i nic nie zrobi. To jest bezpieczne *o ile* worker 1 zdąży skomitować przed tym jak worker 2 zacznie czytać. W praktyce przy Render startCommand `uvicorn main:app --host 0.0.0.0 --port $PORT` (bez `--workers`), masz **jeden proces** — brak problemu. Jeśli kiedykolwiek dodasz `--workers N`, przenieś backfill do osobnego skryptu startowego (`buildCommand`, nie `startCommand`), wykonywanego raz przed startem workerów.

---

### 2.2 Mapa danych — co aplikacja zbiera

Na podstawie `app/models.py` (4 tabele):

#### Tabela `users` (`UserDB`)
| Kategoria | Pola |
|---|---|
| **Identyfikacja** | `id` (UUID), `user_key`, `identity_id`, `email`, `nickname`, `user_number`, `display_name` (property, nie kolumna) |
| **Dane fizyczne** | `name`, `age`, `height`, `weight`, `start_weight`, `target_weight`, `gender` |
| **Cele i preferencje** | `goal`, `frequency`, `diet`, `allergies`, `meals_per_day`, `notes`, `injuries` |
| **Konto i role** | `plan` (free/pro), `role`, `hashed_password`, `is_active` |
| **Makra** | `calories_target`, `protein_target` |
| **Gamifikacja** | `total_xp`, `streak_days`, `last_weight_change` |
| **Listy JSON** | `sports_json`, `training_focus_json`, `improvement_areas_json`, `preferred_foods_json`, `avoid_foods_json`, `available_equipment_json`, `avoid_exercises_json`, `reminders_json`, `weekly_plan_json`, `substitutes_history_json` |
| **Sport** | `sport_focus`, `sport_specialization`, `sport_training_days_json` |
| **Meta** | `created_at`, `updated_at`, `linked_discord_id` |

#### Tabela `daily_logs` (`DailyLogDB`)
| Kategoria | Pola |
|---|---|
| **Dzień** | `log_date`, `logged_at`, `user_id` (FK) |
| **Dieta** | `food`, `meals_json`, `custom_meals_json`, `meals_eaten` |
| **Trening** | `workout`, `workouts_json`, `workouts_done` |
| **Sen** | `sleep_hours`, `sleep_quality`, `sleep_start`, `sleep_end` |
| **Samopoczucie** | `mood`, `mood_score`, `energy_level`, `stress_level`, `fatigue_score`, `rpe`, `notes` |
| **Ciało** | `weight`, `water_liters` |

#### Tabela `exercise_results` (`ExerciseResultDB`)
`exercise_name`, `session_date`, `sets`, `reps`, `weight_kg`, `rpe` (1-10), `notes`, `logged_at` — pełna historia progresji siłowej.

#### Tabela `drill_results` (`DrillResultDB`)
`drill_name`, `drill_category`, `drill_sport`, `target_pct`, `session_date`, `success_count`/`total_attempts` (rzuty), `time_seconds`/`distance_meters` (bieg/sprint), `duration_seconds`, `weight_kg`, `rpe`, `notes` — uniwersalny model do drilli rzutowych, czasowych i siłowych.

---

### 2.3 Poradnik — przeglądanie i edycja bazy SQLite

#### A. Lokalnie (Windows, DB Browser for SQLite)

1. Pobierz **DB Browser for SQLite** (https://sqlitebrowser.org/) — darmowy, open-source.
2. Otwórz plik `C:\Users\adamz\OneDrive\Desktop\Projects\Training_coach\fitai.db`.
3. Zakładka **"Browse Data"** → wybierz tabelę z dropdown (`users`, `daily_logs`, `exercise_results`, `drill_results`).
4. Możesz edytować komórki bezpośrednio (dwuklik), klikać **"Write Changes"** żeby zapisać.
5. Zakładka **"Execute SQL"** do zapytań ad-hoc, np.:
   ```sql
   SELECT user_number, email, display_name, total_xp, streak_days
   FROM users ORDER BY user_number;
   ```

   ⚠️ **Zamknij DB Browser przed uruchomieniem serwera** — SQLite z otwartym połączeniem zapisującym z dwóch programów może powodować "database is locked" (patrz Sekcja 1.1).

#### B. Lokalnie — alternatywa wiersza poleceń (zawsze działa)

```bash
cd C:\Users\adamz\OneDrive\Desktop\Projects\Training_coach
sqlite3 fitai.db
```
```sql
.headers on
.mode column
SELECT user_number, display_name, email, plan, total_xp FROM users;
.quit
```

#### C. Na serwerze Render — endpoint diagnostyczny `/api/admin/db-snapshot`

Render.com **nie daje SSH/shell dostępu na darmowym planie**, więc DB Browser / DBeaver nie mogą się połączyć zdalnie do plikowej bazy SQLite. Najlepsze rozwiązanie: dedykowany endpoint chroniony rolą `admin`.

**Krok 1 — dodaj rolę admina do siebie** (jednorazowo, lokalnie przed deployem):
```sql
UPDATE users SET role = 'admin' WHERE email = 'twoj@email.pl';
```

**Krok 2 — dodaj endpoint w `app/fitness/routes.py` (lub nowy `app/admin/routes.py`):**

```python
from fastapi.responses import FileResponse
import tempfile
import sqlite3

@router.get("/admin/db-snapshot")
def db_snapshot(user: UserDB = Depends(get_current_user)):
    """
    Eksportuje aktualny snapshot bazy SQLite do pobrania.
    Wymaga roli 'admin'. Tworzy kopię (nie blokuje żywej bazy).
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Wymagana rola administratora")

    if not DATABASE_URL.startswith("sqlite"):
        raise HTTPException(status_code=400, detail="Endpoint dostępny tylko dla SQLite")

    db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite:////", "/")
    tmp_path = tempfile.mktemp(suffix=".db")

    # SQLite backup API — bezpieczna kopia "na gorąco" (nie blokuje zapisów)
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(tmp_path)
    src.backup(dst)
    src.close()
    dst.close()

    return FileResponse(
        tmp_path,
        media_type="application/octet-stream",
        filename=f"fitai_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
    )
```

**Krok 3 — pobierz i otwórz lokalnie:**
```bash
curl -H "Authorization: Bearer <TWÓJ_TOKEN_ADMIN>" \
     https://fitai-backend-l918.onrender.com/app/admin/db-snapshot \
     -o snapshot.db
```
Otwórz `snapshot.db` w DB Browser jak w punkcie A.

**Uwaga bezpieczeństwa:** `src.backup(dst)` używa SQLite Online Backup API — **nie blokuje** trwających zapisów (różnica vs. `shutil.copy()` który mógłby skopiować plik w trakcie transakcji i dać uszkodzoną kopię). Endpoint zwraca dane **read-only** (snapshot) — edycja musi się odbyć lokalnie i (jeśli chcesz wprowadzić zmiany z powrotem) przez osobny endpoint `POST /admin/db-restore` z dodatkowym potwierdzeniem, którego **nie rekomenduję** budować — zbyt ryzykowne dla danych produkcyjnych. Lepiej: edycje pojedynczych rekordów przez dedykowane endpointy admina (np. `PUT /admin/users/{id}`).

---

## Sekcja 3 — Autentykacja i zapamiętywanie urządzeń

### 3.1 🔴 KRYTYCZNE — `JWT_SECRET_KEY` nadal generowany losowo

W obecnej wersji `app/config.py`:

```python
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
```

**To jest dokładnie ten sam problem zgłaszany we wcześniejszej fazie projektu i NIE zostało naprawione w bieżącym kodzie.** Jeśli zmienna środowiskowa `JWT_SECRET_KEY` nie jest ustawiona na Render (sprawdź dashboard → Environment), to:

- Przy każdym restarcie/redeployu serwer generuje **nowy losowy klucz**
- Wszystkie wydane tokeny JWT są podpisane starym kluczem
- `decode_token()` w `jwt_utils.py` rzuci `InvalidTokenError` dla każdego istniejącego tokenu
- **Wszyscy użytkownicy zostają wylogowani** przy każdym deployu

To bezpośrednio uderza w wymaganie "Zapamiętaj urządzenie" z Sekcji 3.2 — nie ma sensu budować długoterminowych tokenów, jeśli klucz podpisujący zmienia się przy każdym `git push`.

**Napraw to TERAZ** (priorytet absolutny, przed jakąkolwiek inną zmianą):

```python
# app/config.py
_jwt_secret = os.getenv("JWT_SECRET_KEY", "")
if not _jwt_secret:
    if os.getenv("ENV", "development") == "production":
        import sys
        print("KRYTYCZNY BŁĄD: JWT_SECRET_KEY nie jest ustawiony w produkcji!", file=sys.stderr)
        sys.exit(1)
    else:
        _jwt_secret = secrets.token_hex(32)
        print("OSTRZEŻENIE: JWT_SECRET_KEY nie ustawiony — losowy klucz (tylko dev).")
JWT_SECRET_KEY: str = _jwt_secret
```

**I koniecznie ustaw na Render:**
1. Wygeneruj raz lokalnie: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Render Dashboard → fitai-backend-l918 → Environment → dodaj `JWT_SECRET_KEY` = (wygenerowana wartość)
3. Sprawdź `render.yaml` — masz już `- key: JWT_SECRET_KEY` z `sync: false`, więc Render **wymaga** ręcznego ustawienia w dashboardzie (sync: false = nie synchronizuj z repo, ustaw manualnie). **Zweryfikuj że to pole faktycznie ma wartość w dashboardzie, nie tylko deklarację w YAML.**

---

### 3.2 Access Token vs Refresh Token vs HttpOnly Cookies

**Obecny stan (`jwt_utils.py` + `auth/routes.py`):**
- Jeden token JWT, `exp` = `JWT_EXPIRE_MINUTES` = **10080 minut = 7 dni** (domyślnie)
- Endpoint `POST /auth/refresh` — przyjmuje (wciąż ważny) token, wydaje nowy z przesuniętym `exp`
- Token trzymany w `localStorage['fitai_token']`

To jest **"sliding session"** — pragmatyczne rozwiązanie dla SPA bez backendu sesji, i **dla MVP jest w porządku**. Ale ma realne ograniczenia, które warto zrozumieć przed komercjalizacją:

| Aspekt | Access Token (obecny, 7 dni, localStorage) | Access + Refresh Token (rekomendowane) | HttpOnly Cookie |
|---|---|---|---|
| **Czas życia** | Długi (7 dni) — wygodne, ale ryzykowne | Access: 30 min, Refresh: 30-90 dni | Refresh w cookie, Access w pamięci |
| **Podatność na XSS** | 🔴 Wysoka — JS atakującego może czytać `localStorage` i wykradnąć token na 7 dni | 🟠 Średnia — wykradziony access token żyje tylko 30 min | 🟢 Niska — `HttpOnly` = JS nie ma dostępu |
| **Unieważnienie sesji** | Niemożliwe bez blacklisty (token żyje do `exp`) | Refresh token można usunąć z bazy → wyloguj zdalnie | Tak samo jak refresh |
| **"Zapamiętaj urządzenie"** | De facto już działa (7 dni) | Refresh token 30-90 dni = realne "remember me" | Najlepsze UX, ale wymaga CORS z `credentials: include` |
| **Złożoność implementacji** | 🟢 Bardzo niska (już zrobione) | 🟠 Średnia | 🔴 Wyższa (CORS, SameSite, CSRF token) |

**Rekomendacja dla tej skali (małe/średnie SaaS, frontend na GitHub Pages — inna domena niż backend na Render):**

Nie wdrażaj HttpOnly cookies — **cross-domain cookies między `github.io` i `onrender.com` wymagają `SameSite=None; Secure`**, co działa, ale dodaje złożoności CORS i jest fragile na niektórych przeglądarkach mobilnych (Safari ITP blokuje cross-site cookies agresywnie). To jest realne ryzyko że "Zapamiętaj urządzenie" **nie zadziała na iPhone** mimo poprawnej implementacji.

**Zamiast tego — dwupoziomowy system tokenów w localStorage, oba JWT, różne `exp`:**

```python
# app/auth/jwt_utils.py — dodaj drugą funkcję

def create_refresh_token(user_id: str) -> str:
    """Token długotrwały — tylko do wymiany na nowy access token."""
    exp = datetime.utcnow() + timedelta(days=60)  # "zapamiętaj urządzenie" = 60 dni
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": exp,
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Token krótkotrwały — używany do każdego requestu API."""
    exp = datetime.utcnow() + timedelta(minutes=30)  # ZMIANA: 30 min, nie 7 dni
    payload = {
        "sub": str(user_id), "email": email, "role": role, "type": "access",
        "exp": exp, "iat": datetime.utcnow(), "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
```

```python
# app/auth/routes.py — register() i login() zwracają OBA tokeny

token = create_access_token(user.id, user.email, user.role)
refresh = create_refresh_token(user.id)
return TokenResponse(
    access_token=token,
    refresh_token=refresh,   # NOWE pole w schemas.TokenResponse
    user_id=user.id,
    user_number=user.user_number,
    display_name=user.display_name,
    name=user.name, role=user.role, plan=user.plan,
)

# NOWY endpoint — wymiana refresh → nowy access (bez ponownego logowania)
@router.post("/refresh-access")
def refresh_access_token(payload: RefreshTokenRequest):
    try:
        decoded = jwt.decode(payload.refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Sesja wygasła — zaloguj się ponownie")
    except jwt.InvalidTokenError:
        raise HTTPException(401, detail="Nieprawidłowy token")
    if decoded.get("type") != "refresh":
        raise HTTPException(401, detail="Nieprawidłowy typ tokenu")

    with Session(engine) as session:
        user = session.get(UserDB, decoded["sub"])
        if not user or not user.is_active:
            raise HTTPException(401, detail="Konto nieaktywne")
        new_access = create_access_token(user.id, user.email, user.role)
        return {"access_token": new_access, "expires_in": 1800}
```

**Frontend (`index.html`)** — automatyczne odświeżanie w tle:

```js
// Wywołuj przed każdym chronionym fetch, lub w interceptorze
async function ensureFreshToken() {
  const access = localStorage.getItem('fitai_token');
  const refresh = localStorage.getItem('fitai_refresh_token');
  if (!access || !refresh) return access;

  // Sprawdź exp tokenu access (dekoduj payload bez weryfikacji podpisu)
  try {
    const payload = JSON.parse(atob(access.split('.')[1]));
    const expiresInMs = payload.exp * 1000 - Date.now();
    if (expiresInMs > 5 * 60 * 1000) return access; // jeszcze >5 min — OK

    // Odśwież
    const res = await fetch(window.API_BASE + '/auth/refresh-access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh })
    });
    if (!res.ok) {
      // Refresh token wygasł — wyloguj
      localStorage.removeItem('fitai_token');
      localStorage.removeItem('fitai_refresh_token');
      openAuthModal('login');
      return null;
    }
    const data = await res.json();
    localStorage.setItem('fitai_token', data.access_token);
    return data.access_token;
  } catch (e) {
    return access; // fallback — użyj starego, niech serwer zwróci 401 jeśli zły
  }
}
```

**Efekt dla użytkownika:** loguje się raz, refresh token (60 dni) żyje w `localStorage`, access token (30 min) odświeża się automatycznie w tle przy każdej akcji — użytkownik **nigdy nie widzi ekranu logowania**, dopóki nie minie 60 dni nieaktywności albo nie wyczyści danych przeglądarki. To jest realne "Zapamiętaj urządzenie" bez komplikacji cookies cross-domain.

**Migracja:** dodaj `refresh_token: Optional[str] = None` do `TokenResponse` w `schemas.py`, dodaj `RefreshTokenRequest(BaseModel): refresh_token: str`. Stare tokeny (7-dniowe, bez `"type"`) będą nadal działać dla `decode_token` w `get_current_user` o ile nie dodasz tam walidacji `type == "access"` — dla płynnej migracji **nie wymuszaj** sprawdzania `type` w `get_current_user`, tylko w nowym `/auth/refresh-access`.

---

### 3.3 Powiązanie e-mail + hasło + `user_number`

Przepływ `register()` jest poprawny:
1. Sprawdzenie unikalności e-maila (`existing = session.exec(select(UserDB).where(UserDB.email == ...))`)
2. Hashowanie hasła (`hash_password()`)
3. Przydział `user_number` (z zastrzeżeniami z Sekcji 2.1)
4. Zapis `user_key = f"native:user:{next_number}"`, `nickname=None`
5. `display_name` jako `@property` zwraca `f"Użytkownik#{self.user_number:04d}"` — **prawidłowo obliczane dynamicznie, nie duplikowane w bazie**, co jest dobrą praktyką (single source of truth)

**To wszystko jest poprawnie powiązane.** Jedyna poprawka to Sekcja 2.1 (race condition na `user_number`).

---

## Sekcja 4 — Funkcjonalność zakładek i optymalizacja

### 4.1 `DayItemSwapRequest` — ulepszenia

Endpoint `POST /app/day/item/swap` działa, ale ma ograniczenie: **wymiana posiłku/ćwiczenia wymaga ręcznego podania `new_name`, `new_kcal`, `new_protein` przez użytkownika** (frontend prawdopodobnie pokazuje `prompt()` lub formularz). To jest słabe UX — użytkownik musi sam wymyślić wartości kcal/białka dla nowego posiłku.

**Propozycja — endpoint sugestii zamiany na bazie bazy posiłków:**

```python
# app/schemas.py
class DaySwapSuggestionRequest(BaseModel):
    item_id: str
    item_type: str  # "meal" | "workout"

# app/fitness/routes.py
@router.post("/day/item/swap-suggestions")
def get_swap_suggestions(
    payload: DaySwapSuggestionRequest,
    user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Zwraca 3 alternatywy o podobnej kaloryczności/typie do wymiany."""
    log = _ensure_day_log(session, user.id, date.today())
    _, item, _ = _find_day_item(log, payload.item_id, payload.item_type)
    if not item:
        raise HTTPException(404, "Element nie znaleziony")

    if payload.item_type == "meal":
        target_kcal = item.get("kcal", 0)
        meal_type = item.get("meal_type", "inne")
        candidates = find_meals_by_kcal_range(meal_type, target_kcal * 0.85, target_kcal * 1.15)
        return {"suggestions": candidates[:3]}
    else:
        avoid = set(user.get_list("avoid_exercises_json"))
        candidates = find_exercises_by_muscle_group(item.get("name"), exclude=avoid)
        return {"suggestions": candidates[:3]}
```

Frontend renderuje 3 kafelki z podglądem ("🥗 Sałatka z kurczakiem — 410 kcal, 38g białka") i jednym kliknięciem wywołuje istniejący `POST /app/day/item/swap` z wybranymi wartościami — **eliminuje ręczne wpisywanie liczb**.

### 4.2 Logowanie drillów sportowych — szybsze wprowadzanie

`POST /app/drill-result` jest kompletny backendowo. UX-owo, dla sportów z seriami (np. "Rzuty wolne — seria 10" × 5 serii), użytkownik musi wywołać endpoint 5 razy. Propozycja — **batch logging**:

```python
class DrillResultBatchRequest(BaseModel):
    drill_name: str
    drill_category: Optional[str] = None
    drill_sport: Optional[str] = None
    target_pct: Optional[int] = None
    session_date: Optional[str] = None
    series: list[dict]  # [{"success_count": 8, "total_attempts": 10}, ...]
    rpe: int

@router.post("/drill-result/batch")
def log_drill_result_batch(req: DrillResultBatchRequest, user=Depends(get_current_user), session=Depends(get_session)):
    total_success = sum(s["success_count"] for s in req.series)
    total_attempts = sum(s["total_attempts"] for s in req.series)
    # Zapisz jeden agregowany DrillResultDB + opcjonalnie JSON z rozbiciem na serie w `notes`
    ...
```

Frontend: zamiast 5 wywołań API, jeden formularz z 5 wierszami "Seria 1: [8]/[10]", "Seria 2: [7]/[10]"... i jeden przycisk "Zapisz wszystkie serie".

### 4.3 Parametry życiowe (waga, sen, RPE) — jednorazowy zapis ✅

To zostało już zaimplementowane jako `saveDayData()` / `POST /app/checkin` z polami `sleep_hours`, `sleep_quality`, `sleep_start`, `sleep_end`, `energy_level`, `stress_level`, `fatigue_score`, `mood_score`, `rpe`, `weight` — **wszystkie w jednym requeście**. To jest prawidłowa architektura, nie wymaga zmian.

### 4.4 Redundancja JS i offline sync — Service Worker już bardzo dobry

`sw.js` — **to jest implementacja na poziomie produkcyjnym**, z:
- Network-First + 4s timeout dla API (`networkFirstJSON`)
- Cache-First + SWR dla CDN
- Background Sync (`syncPendingLogs` → `/app/log/daily`)
- Force-update flow z `postMessage`

**Jedyna niezgodność:** `syncPendingLogs()` wysyła do `/app/log/daily`, ale w `app/fitness/routes.py` **nie istnieje endpoint `/app/log/daily`** — istnieje `/app/checkin` jako odpowiednik. To oznacza że background sync **nigdy się nie powiedzie** (404), dane z trybu offline nie zostaną zsynchronizowane.

**Fix — zmień w `sw.js`, użyj `req.url` z oryginalnego requestu** (nie hardcodowanej ścieżki):

```js
async function syncPendingLogs() {
  let pendingCache;
  try { pendingCache = await caches.open('fitai-pending-logs'); } catch { return; }
  const keys = await pendingCache.keys();
  let synced = 0, failed = 0;
  for (const req of keys) {
    const resp = await pendingCache.match(req);
    if (!resp) continue;
    try {
      const body = await resp.json();
      const result = await fetch(req.url, {  // ← użyj URL z oryginalnego requestu
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (result.ok) { await pendingCache.delete(req); synced++; }
      else failed++;
    } catch { failed++; }
  }
  // ...
}
```

A przy zapisie offline (w `index.html`, gdy `fetch()` się nie powiedzie), zapisz pełny URL do `pendingCache`:
```js
const pendingCache = await caches.open('fitai-pending-logs');
await pendingCache.put(
  new Request(window.API_BASE + '/app/checkin', { method: 'POST' }),
  new Response(JSON.stringify(checkinPayload))
);
await navigator.serviceWorker.ready.then(sw => sw.sync.register('fitai-sync-logs'));
```

---

## Sekcja 5 — Rewolucja wizualna (UI/UX) — od cyberpunk do Premium SaaS

### 5.1 Ocena obecnego stanu

Styl (Plus Jakarta Sans + Syne, gradienty cyan/violet, glassmorphism) jest **konsekwentny i ma charakter**, ale obecnie wygląda jak *dobry projekt deweloperski*, nie *produkt komercyjny premium*. Konkretne problemy:

1. **Puste stany (Empty States) są tekstowe i nieatrakcyjne** — "Brak planu diety na dziś — kliknij + Dodaj" to zwykły szary tekst. Premium SaaS używa **ilustracji + jasnego call-to-action** w pustych stanach.
2. **`cdn.tailwindcss.com` w produkcji** — to jest **deweloperski CDN Tailwind który kompiluje CSS w runtime w przeglądarce** (~350KB JS + recompilacja klas przy każdej zmianie DOM). Dla produktu komercyjnego to oznacza: wolniejszy initial paint, ostrzeżenie w konsoli przeglądarki ("cdn.tailwindcss.com should not be used in production"), i brak tree-shaking (cały Tailwind ładowany, nie tylko użyte klasy).
3. **Stary mechanizm wielu profili na koncie** (dropdown "Adam / Ala / + Dodaj profil") — jeśli nadal istnieje gdzieś w `index.html`, **musi zostać usunięty przed launchem** — w modelu "jeden `user_number` = jedno konto" multi-profile nie ma sensu i wprowadza w błąd.

### 5.2 Konkretna paleta i typografia premium

**Obecna paleta** (`--cyan:#00e5ff`, `--violet:#7c3aed`, `--bg:#0a0b10`) jest dobra bazowo, ale potrzebuje **hierarchii** — premium dark UI (Linear, Vercel, Raycast) używa 5-7 odcieni szarości/granatu, nie tylko czarnego tła + jasnych akcentów:

```css
:root {
  /* Tła — hierarchia głębi */
  --bg-base:      #0a0b10;   /* tło strony */
  --bg-surface:   #12141c;   /* karty (1 poziom nad bazą) */
  --bg-surface-2: #1a1d29;   /* karty zagnieżdżone, hover */
  --bg-overlay:   #20232f;   /* modale, dropdowny */

  /* Granice — subtelne, nie białe */
  --border-subtle: rgba(255,255,255,0.06);
  --border-default: rgba(255,255,255,0.10);
  --border-strong: rgba(255,255,255,0.16);

  /* Akcenty — zachowane, ale z wariantami */
  --cyan:        #00e5ff;
  --cyan-dim:    rgba(0,229,255,0.12);   /* tła badge'y */
  --cyan-border: rgba(0,229,255,0.30);
  --violet:      #7c3aed;
  --violet-dim:  rgba(124,58,237,0.12);

  /* Tekst — hierarchia, nie tylko białe/szare */
  --text-primary:   #f3f4f6;   /* nagłówki, wartości */
  --text-secondary: #9ca3af;   /* labelki, opisy */
  --text-tertiary:  #4b5563;   /* placeholder, disabled */

  /* Sukces/ostrzeżenie/błąd — stałe w całej appce */
  --success: #22c55e;
  --warning: #f59e0b;
  --danger:  #ef4444;
}
```

**Typografia** — `Syne` (nagłówki, 700-800) + `Plus Jakarta Sans` (treść, 400-600) to dobry wybór, ale ustal **skalę**:

```css
.text-display  { font: 800 32px/1.2 Syne, sans-serif; letter-spacing: -0.02em; }  /* "Witaj, Adam!" */
.text-h1       { font: 700 24px/1.3 Syne, sans-serif; letter-spacing: -0.01em; }  /* "Mój Dzień" */
.text-h2       { font: 700 18px/1.4 Syne, sans-serif; }                           /* nagłówki kart */
.text-body     { font: 500 14px/1.5 'Plus Jakarta Sans', sans-serif; }
.text-label    { font: 600 11px/1.4 'Plus Jakarta Sans'; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-secondary); }
.text-value-lg { font: 800 28px/1 'Plus Jakarta Sans'; }                          /* "2972 kcal" */
.text-mono     { font: 500 13px/1.4 'JetBrains Mono', monospace; }                /* Użytkownik#0047 */
```

### 5.3 Empty States — konkretne wzorce dla FitAI

Zamiast:
```html
<div class="text-center py-6 text-gray-500 text-sm italic">
  Brak planu diety na dziś — kliknij "+ Dodaj" aby dodać posiłek.
</div>
```

Premium wersja — ilustracja inline + hierarchia (nagłówek, opis, CTA):

```html
<div style="text-align:center;padding:32px 16px;">
  <div style="width:64px;height:64px;margin:0 auto 16px;border-radius:16px;
              background:var(--cyan-dim);display:flex;align-items:center;
              justify-content:center;font-size:28px;">🍽️</div>
  <h3 style="font:700 15px Syne;color:var(--text-primary);margin-bottom:4px;">
    Brak zaplanowanych posiłków
  </h3>
  <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;max-width:280px;
            margin-left:auto;margin-right:auto;line-height:1.5;">
    Dodaj swój pierwszy posiłek na dziś, albo wygeneruj plan AI dopasowany do Twoich celów.
  </p>
  <div style="display:flex;gap:8px;justify-content:center;">
    <button onclick="openAddMealModal()" style="padding:8px 16px;border-radius:10px;
            background:var(--cyan-dim);border:1px solid var(--cyan-border);
            color:var(--cyan);font-size:13px;font-weight:600;cursor:pointer;">
      + Dodaj posiłek
    </button>
    <button onclick="goToTab('dieta')" style="padding:8px 16px;border-radius:10px;
            background:transparent;border:1px solid var(--border-default);
            color:var(--text-secondary);font-size:13px;font-weight:600;cursor:pointer;">
      Generuj plan AI
    </button>
  </div>
</div>
```

### 5.4 Skeleton loading (shimmer) — dla wszystkich kart danych

Premium SaaS **nigdy nie pokazuje "0 kcal" lub pustego miejsca podczas ładowania** — pokazuje shimmer placeholder. Dodaj uniwersalną klasę:

```css
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}
.skeleton {
  background: linear-gradient(90deg,
    var(--bg-surface-2) 25%, var(--bg-overlay) 50%, var(--bg-surface-2) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}
.skeleton-text   { height: 14px; width: 60%; }
.skeleton-value  { height: 28px; width: 80px; }
.skeleton-card   { height: 80px; width: 100%; }
```

```js
function showLoadingState(containerId) {
  const c = document.getElementById(containerId);
  if (!c) return;
  c.innerHTML = Array(3).fill(0).map(() => `
    <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;">
      <div class="skeleton" style="width:20px;height:20px;border-radius:5px;"></div>
      <div style="flex:1;">
        <div class="skeleton skeleton-text" style="margin-bottom:6px;"></div>
        <div class="skeleton skeleton-text" style="width:40%;height:10px;"></div>
      </div>
    </div>
  `).join('');
}
```

Wywołuj `showLoadingState('day-meals-list')` na początku `loadTodayData()`, **przed** `fetch()`.

### 5.5 Hero Section — landing page

Obecny hero (tytuł "Trenuj inteligentnie. Żyj lepiej." + dashboard preview po prawej) to dobry układ. Konkretne ulepszenia premium:

1. **Dashboard preview powinien być "żywy"** — animowany licznik kalorii który odlicza od 0 do 2200 przy scrollu w viewport (Intersection Observer + `requestAnimationFrame`), zamiast statycznego "87%".
2. **Dodaj social proof pod CTA** — nie tylko "✅ Bezpłatny start · ✅ Brak karty · ✅ Offline PWA", ale też np. "🔥 247 aktywnych sportowców" (prawdziwa liczba z `SELECT COUNT(*) FROM users WHERE is_active=1` — wystaw publiczny endpoint `GET /app/stats/public` zwracający tylko agregaty, bez danych osobowych).
3. **Gradient tła hero** — dodaj subtelną animację (`background-position` przesuwane przez `@keyframes` w 30s loop) — daje wrażenie "żywego" produktu bez przesady.

```css
.hero-bg {
  background:
    radial-gradient(circle at 20% 30%, rgba(0,229,255,0.08), transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(124,58,237,0.08), transparent 50%),
    var(--bg-base);
  background-size: 200% 200%;
  animation: heroDrift 30s ease-in-out infinite alternate;
}
@keyframes heroDrift {
  0%   { background-position: 0% 0%; }
  100% { background-position: 100% 100%; }
}
```

### 5.6 Dynamiczny dashboard dla sportowców — propozycja architektury

Dla zakładki "Sport" (drille) — zamiast listy, **karta sportu jako hero element**:

```
┌─────────────────────────────────────────────────────┐
│  🏀 Koszykówka                          Tydzień 12   │
│                                                       │
│  Skuteczność rzutów wolnych        Trend: ↗ +8%     │
│  ████████████████████░░░░  78%  (cel: 80%)          │
│                                                       │
│  [Mini-wykres 7 dni — sparkline]                     │
│                                                       │
│  Ostatnie sesje:  Pon ✓  Wt ─  Śr ✓  Czw ✓  Pt ─    │
└─────────────────────────────────────────────────────┘
```

Dane do tego już istnieją w `GET /app/weekly-analysis`. Brakuje tylko renderowania sparkline — można zrobić **bez Chart.js**, czystym SVG (lżejsze, brak zależności):

```js
function renderSparkline(values, width = 120, height = 32) {
  const max = Math.max(...values, 1);
  const points = values.map((v, i) =>
    `${(i / (values.length - 1)) * width},${height - (v / max) * height}`
  ).join(' ');
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    <polyline points="${points}" fill="none" stroke="var(--cyan)" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
}
```

---

## Sekcja 6 — Roadmapa produkcyjna (Milestones)

### Milestone 0 — Blokery bezpieczeństwa (1 dzień, ZRÓB NAJPIERW)
| # | Zadanie | Plik | Czas |
|---|---|---|---|
| 0.1 | Napraw `JWT_SECRET_KEY` — usuń losowy fallback w produkcji, ustaw zmienną na Render | `app/config.py` + Render Dashboard | 30 min |
| 0.2 | Włącz WAL mode dla SQLite (`PRAGMA journal_mode=WAL` + `busy_timeout`) | `app/database.py` | 15 min |
| 0.3 | Zweryfikuj że stary multi-profile dropdown ("Adam/Ala/+Dodaj profil") jest usunięty z `index.html` | `index.html` | 1h |

### Milestone 1 — Integralność danych user_number (1-2 dni)
| # | Zadanie | Plik | Czas |
|---|---|---|---|
| 1.1 | Dodaj `UserNumberSequenceDB` z `AUTOINCREMENT`, zmień `register()` na `session.flush()` + sekwencja | `app/models.py`, `app/auth/routes.py` | 1h |
| 1.2 | Napraw błędny komunikat 409 przy konflikcie `user_number` (rozróżnij email vs numer) | `app/auth/routes.py` | 30 min |
| 1.3 | Dodaj endpoint `/api/admin/db-snapshot` + ustaw `role='admin'` dla siebie | `app/fitness/routes.py` | 1h |

### Milestone 2 — Sesje i "Zapamiętaj urządzenie" (1 dzień)
| # | Zadanie | Plik | Czas |
|---|---|---|---|
| 2.1 | Dodaj `create_refresh_token()`, zmień access token na 30 min | `app/auth/jwt_utils.py` | 30 min |
| 2.2 | Dodaj `refresh_token` do `TokenResponse`, endpoint `/auth/refresh-access` | `app/schemas.py`, `app/auth/routes.py` | 1h |
| 2.3 | Frontend: `ensureFreshToken()` + auto-refresh przed każdym chronionym fetch | `index.html` | 2h |

### Milestone 3 — Naprawy funkcjonalne (1-2 dni)
| # | Zadanie | Plik | Czas |
|---|---|---|---|
| 3.1 | Napraw `syncPendingLogs()` w SW — użyj `req.url` zamiast hardcoded `/app/log/daily` | `sw.js` | 30 min |
| 3.2 | Audyt `index.html` — usuń duplikaty `addEventListener`/`setInterval`, dodaj `chart.destroy()` przed re-render | `index.html` | 2-3h |
| 3.3 | Owijaj parsowanie JSON z LLM funkcją `extract_json_from_llm()` | `app/ai/*.py` | 1-2h |
| 3.4 | (opcjonalnie) `POST /app/day/item/swap-suggestions` — sugestie zamiany na bazie kcal/grupy mięśniowej | `app/fitness/routes.py` | 2-3h |

### Milestone 4 — Wizualny rebrand Premium (3-5 dni)
| # | Zadanie | Plik | Czas |
|---|---|---|---|
| 4.1 | Zbuduj statyczny Tailwind CSS (usuń `cdn.tailwindcss.com`) — `npx tailwindcss -o dist/tailwind.min.css --minify` | build pipeline | 2h |
| 4.2 | Wprowadź pełną paletę CSS variables (Sekcja 5.2) — zastąp hardcoded kolory | `index.html` (style global) | 3-4h |
| 4.3 | Zaimplementuj skeleton loaders dla wszystkich list (Mój Dzień, Postępy, Sport) | `index.html` | 3-4h |
| 4.4 | Zaprojektuj i wdróż nowe Empty States (ilustracje SVG + CTA) | `index.html` | 4-6h |
| 4.5 | Sparkline dla statystyk sportowych (czyste SVG) | `index.html` | 2-3h |
| 4.6 | Animowany hero (licznik, gradient drift), social proof z `/app/stats/public` | `index.html` + nowy endpoint | 3-4h |

### Milestone 5 — Pre-launch QA (1 dzień)
| # | Zadanie | Czas |
|---|---|---|
| 5.1 | Test end-to-end: rejestracja → 30 min nieaktywności → auto-refresh tokenu działa | 1h |
| 5.2 | Test współbieżności: 2 zakładki tego samego konta zapisują check-in jednocześnie — brak "database is locked" | 30 min |
| 5.3 | Test offline: wyłącz sieć w trakcie wypełniania "Mój Dzień", włącz ponownie — sync logów działa | 1h |
| 5.4 | Test mobile Safari — sprawdź że tokeny w localStorage przetrwają zamknięcie karty (nie tylko zakładki) | 30 min |
| 5.5 | Lighthouse audit po usunięciu `cdn.tailwindcss.com` — porównaj wynik Performance przed/po | 30 min |

**Łączny szacowany czas: ~8-12 dni roboczych** (przy pracy jednoosobowej, z testowaniem).

---

## Podsumowanie priorytetów

1. 🔴 **`JWT_SECRET_KEY`** — to jest pojedyncza linia kodu, która jeśli źle skonfigurowana, wylogowuje wszystkich użytkowników przy każdym deployu. Sprawdź to PRZED czymkolwiek innym.
2. 🔴 **`user_number` race condition** — niska szansa wystąpienia, ale gdy się zdarzy, daje **fałszywy komunikat "email zajęty"** dla poprawnego e-maila — to jest błąd który zniechęci realnego klienta przy próbie rejestracji.
3. 🟠 **WAL mode** — jedna zmiana, ogromna redukcja ryzyka "database is locked" pod obciążeniem.
4. 🟠 **`syncPendingLogs` 404** — offline sync obecnie nie działa, mimo że cała infrastruktura SW jest gotowa.
5. 🟡 **Wizualny rebrand** — najbardziej czasochłonne, ale obecny design jest już blisko premium; potrzebuje hierarchii kolorów, skeletonów i lepszych empty states, nie przebudowy od zera.
