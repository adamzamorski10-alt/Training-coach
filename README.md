# FitAI — System Zarządzania Dietą i Treningiem

Kompletny system asystenta fitness oparty na Claude AI, dostępny przez:
- **Stronę internetową** (React/HTML dashboard)
- **Bota Discord** (slash komendy)
- **REST API** (FastAPI — integracja z innymi serwisami)

---

## Architektura

```
fitai/
├── fitai_discord_bot.py   # Bot Discord (discord.py)
├── fitai_api.py           # Backend REST API (FastAPI)
├── fitai_users.json       # Baza danych użytkowników (auto-tworzona)
├── .env                   # Klucze API (nie commituj!)
├── requirements.txt       # Zależności Python
└── README.md
```

Strona internetowa (dashboard) działa jako **standalone HTML/React artifact** — 
może być hostowana na dowolnym statycznym hostingu (Vercel, Netlify, GitHub Pages).

---

## Szybki start

### 1. Instalacja zależności

```bash
pip install discord.py anthropic fastapi uvicorn python-dotenv pydantic aiohttp filelock
```

Lub przez requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Plik `.env`

Utwórz plik `.env` w katalogu projektu:

```env
DISCORD_TOKEN=twoj_token_bota_discord
ANTHROPIC_API_KEY=twoj_klucz_anthropic
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Skąd wziąć klucze:**
- `DISCORD_TOKEN` → https://discord.com/developers/applications → Utwórz bota → Bot → Token
- `ANTHROPIC_API_KEY` → https://console.anthropic.com → API Keys

### 3. Uruchomienie backendu (API)

```bash
uvicorn fitai_api:app --reload --port 8000
```

API będzie dostępne pod `http://localhost:8000`  
Dokumentacja Swagger: `http://localhost:8000/docs`

### 4. Uruchomienie bota Discord

```bash
python fitai_discord_bot.py
```

### 5. Konfiguracja bota Discord

1. Wejdź na https://discord.com/developers/applications
2. Utwórz nową aplikację → Bot
3. Włącz **Message Content Intent** (Bot → Privileged Gateway Intents)
4. Skopiuj token do `.env`
5. Zaproś bota na serwer:  
   `https://discord.com/oauth2/authorize?client_id=TWOJE_CLIENT_ID&permissions=8&scope=bot+applications.commands`

---

## Komendy Discord

| Komenda | Opis |
|---------|------|
| `/fit setup` | Utwórz profil (interaktywny onboarding przez Discord) |
| `/fit profil` | Wyświetl swój profil |
| `/fit raport` | Złóż dzienny raport (co jadłeś, co ćwiczyłeś) |
| `/fit dieta` | Plan diety na dziś od AI |
| `/fit trening` | Plan treningowy na dziś od AI |
| `/fit postepy` | Tygodniowe podsumowanie AI |
| `/fit reset` | Usuń profil |
| `/fit pomoc` | Lista komend |

---

## API Endpointy

### Użytkownicy
```
POST /users/{user_id}           Utwórz/zaktualizuj profil
GET  /users/{user_id}           Pobierz profil
POST /users/{user_id}/logs      Dodaj dzienny raport
GET  /users/{user_id}/logs      Historia raportów
```

### AI
```
POST /ai/diet                   Plan diety (wymaga user_id)
POST /ai/workout                Plan treningowy (wymaga user_id)
POST /ai/analyze-log            Analiza dziennego raportu
POST /ai/weekly                 Tygodniowe podsumowanie
```

### Przykład użycia API

```bash
# Utwórz profil
curl -X POST http://localhost:8000/users/user123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marek",
    "age": 28,
    "height": 182,
    "weight": 85,
    "target_weight": 78,
    "gender": "mężczyzna",
    "goal": "Redukcja tkanki tłuszczowej",
    "frequency": "3-4 razy w tygodniu",
    "sports": ["siłownia", "bieganie"],
    "diet": "High-protein",
    "allergies": "",
    "meals_per_day": 4
  }'

# Pobierz plan diety
curl -X POST http://localhost:8000/ai/diet \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# Dodaj dzienny raport
curl -X POST http://localhost:8000/users/user123/logs \
  -H "Content-Type: application/json" \
  -d '{
    "food": "Owsianka, kurczak z ryżem, shake proteinowy",
    "workout": "Siłownia 45 min - Push Day",
    "mood": "Dobre samopoczucie, lekkie zmęczenie",
    "weight": 84.5
  }'
```

---

## Schemat bazy danych (JSON)

```json
{
  "user_id": {
    "name": "Marek",
    "age": 28,
    "height": 182,
    "weight": 85.0,
    "target_weight": 78.0,
    "start_weight": 88.0,
    "gender": "mężczyzna",
    "goal": "Redukcja tkanki tłuszczowej",
    "frequency": "3-4 razy w tygodniu",
    "sports": ["siłownia", "bieganie"],
    "diet": "High-protein",
    "allergies": "",
    "meals_per_day": 4,
    "notes": "",
    "calories_target": 2200,
    "protein_target": 187,
    "created_at": "2026-04-24T10:00:00",
    "updated_at": "2026-04-24T10:00:00",
    "logs": [
      {
        "date": "2026-04-24",
        "food": "Owsianka, kurczak z ryżem...",
        "workout": "Siłownia 45 min...",
        "mood": "Dobre samopoczucie",
        "weight": 84.5,
        "logged_at": "2026-04-24T20:30:00"
      }
    ]
  }
}
```

---

## Funkcje AI

System używa **Claude claude-sonnet-4-20250514** do:

1. **Rekomendacja dzienna** — krótka wskazówka na dany dzień
2. **Plan diety** — szczegółowy plan posiłków z gramaturą i kaloriami, dostosowany do profilu
3. **Plan treningowy** — plan sesji z ćwiczeniami, seriami i wskazówkami
4. **Analiza raportu** — ocena dnia + konkretny plan na jutro
5. **Podsumowanie tygodniowe** — analiza postępów i rekomendacje

Każde zapytanie AI uwzględnia:
- Pełny profil użytkownika (cel, parametry, preferencje)
- Historię ostatnich raportów
- Obliczone zapotrzebowanie kaloryczne (wzór Harris-Benedict + TDEE)
- Docelowe makroskładniki

---

## Hosting produkcyjny

### Backend (API)
- **Railway** / **Render** / **Heroku** — darmowy tier na start
- Ustaw zmienne środowiskowe (`DISCORD_TOKEN`, `ANTHROPIC_API_KEY`)
- Ustaw też `CORS_ORIGINS`, jeśli frontend działa z innego adresu niż localhost
- Dla produkcji zamień JSON na **PostgreSQL** lub **SQLite** (alembic + SQLModel)

### Bot Discord
- Uruchom na tym samym serwerze co API
- Lub osobno na **Railway** / **Fly.io**

### Frontend (strona)
- Wbudowany dashboard działa offline (localStorage)
- Dla synchronizacji z API: podmień `localStorage` na wywołania `fetch('/api/...')`
- Hostowanie: **Vercel** / **Netlify** / **GitHub Pages** (bezpłatnie)

---

## requirements.txt

```
discord.py>=2.3.0
anthropic>=0.25.0
fastapi>=0.110.0
uvicorn>=0.29.0
python-dotenv>=1.0.0
pydantic>=2.0.0
aiohttp>=3.9.0
```

---

## Rozbudowa

Możliwe kolejne kroki:
- [ ] Baza danych PostgreSQL zamiast JSON
- [ ] Autoryzacja JWT (logowanie przez Discord OAuth)
- [ ] Zdjęcia posiłków → analiza kalorii przez Claude Vision
- [ ] Integracja z Garmin / Apple Health (krokomierz, HRV)
- [ ] Powiadomienia push (web) i przypomnienia Discord
- [ ] Eksport danych do PDF / Excel
- [ ] Multi-language support (EN/PL/DE)
