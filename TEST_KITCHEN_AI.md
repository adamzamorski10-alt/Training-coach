# 🧪 TEST KITCHEN AI - Kuchnia AI

## 📋 Kompletny Plan Testowania

### Backend (fitai_api.py)

#### ✅ Co zostało dodane:

1. **Nowy endpoint POST `/app/kitchen/generate`**
   - Lokalizacja: linia 3631 w fitai_api.py
   - Wymaga: Authorization header z tokenem JWT
   - Wymaga: lista składników (ingredients: List[str])
   - Zwraca: JSON z tablica 4 przepisów

2. **Szczegółowe logowanie**
   - `[KitchenGenerate]` prefix dla wszystkich logów
   - Loguje: liczbę składników, cel użytkownika, dane z AI
   - Loguje: błędy parsowania JSON
   - Loguje: sukces wygenerowania przepisów

3. **JSON Format zwracany przez API**
   ```json
   {
     "recipes": [
       {
         "nazwa": "string",
         "składniki": ["string"],
         "opis": "string",
         "kalorie": number,
         "białko": number,
         "węglowodany": number,
         "tłuszcze": number
       }
     ]
   }
   ```

4. **Obsługa błędów**
   - HTTPException 422 - pusta lista składników
   - HTTPException 422 - więcej niż 30 składników
   - HTTPException 503 - błąd AI (Groq/Gemini)
   - HTTPException 502 - nieprawidłowy JSON z AI
   - HTTPException 500 - błąd nieoczekiwany

### Frontend (index.html)

#### ✅ Co zostało dodane:

1. **Nowa funkcja `kitchenGenerate()`**
   - Lokalizacja: linia 8724-8910 w index.html
   - Zastępuje starego `fridgeGenerate()` dla nowego endpointu
   - Console.log debugging na każdym kroku

2. **Szczegółowe console logowanie**
   ```javascript
   console.log('🔍 Składniki:', _kitchen.fridgeTags);
   console.log('📝 Identity ID:', identityId);
   console.log('🔐 Token present:', !!token);
   console.log('🌐 API Base:', _apiBase);
   console.log('✅ Health check passed');
   console.log('[KitchenGenerate] Authorization header added');
   console.log('[KitchenGenerate] Sending request to /app/kitchen/generate');
   console.log('[KitchenGenerate] Payload:', payload);
   console.log('[KitchenGenerate] Response status:', res.status);
   console.log('[KitchenGenerate] Response data:', data);
   ```

3. **Rendering przepisów**
   - Każdy przepis wyświetlony w osobnym kontenerze
   - Pokazuje: nazwę, składniki, opis, kalorie, makroskładniki
   - Kolorowe etykiety dla wartości odżywczych

4. **Obsługa błędów**
   - Toast notifications (pop-up)
   - Wyświetlanie HTTP status w interfejsie
   - Parsowanie szczegółowych komunikatów z serwera
   - AbortController timeout (10 sekund)
   - Obsługa networkowych błędów

#### ✅ Co zostało zmienione:

1. **Przycisk**
   - Linia 2161: zmieniono `onclick="fridgeGenerate()"` na `onclick="kitchenGenerate()"`
   - Teraz wywołuje nową funkcję zamiast starej

---

## 🚀 INSTRUKCJA TESTOWANIA

### Krok 1: Uruchom Backend

```bash
cd "c:\Users\adamz\OneDrive\Desktop\Projects\Training coach"
uvicorn fitai_api:app --reload --port 8000
```

Powinieneś zobaczyć:
```
[FitAI] ✅ Groq: klient zainicjalizowany (primary AI).
[FitAI] ✅ Gemini: klient zainicjalizowany (fallback AI).
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Krok 2: Otwórz index.html w przeglądarce

1. Otwórz `http://localhost:5500/index.html` (Live Server) lub
   `file:///c:/Users/adamz/OneDrive/Desktop/Projects/Training%20coach/index.html` (bezpośrednio)
2. Zaloguj się swoim kontem
3. Przejdź do: Plan → Dieta → Kuchnia AI

### Krok 3: Otwórz Developer Tools

Wciśnij: `F12` lub `Ctrl+Shift+I`

Przejdź na kartę "Console", aby widzieć logi

### Krok 4: Przetestuj Funkcjonalność

#### Test 1: Dodaj składniki

1. W polu "np. kurczak 200g, brokuły…" wpisz:
   ```
   Kurczak, Ryż, Brokuły, Czosnek, Cebula
   ```
2. Kliknij "Dodaj" lub wciśnij Enter
3. Powinieneś zobaczyć 5 tagów z możliwością usunięcia (×)

**W konsoli powinieneś zobaczyć:**
```
🔍 Składniki: ['Kurczak', 'Ryż', 'Brokuły', 'Czosnek', 'Cebula']
```

#### Test 2: Kliknij "Generuj 4 przepisy"

**W konsoli powinieneś zobaczyć:**

```
🔍 Składniki: (5) ['Kurczak', 'Ryż', 'Brokuły', 'Czosnek', 'Cebula']
📝 Identity ID: uuid-tego-użytkownika
🔐 Token present: true
🌐 API Base: http://localhost:8000
✅ Health check passed
[KitchenGenerate] Authorization header added
[KitchenGenerate] Sending request to /app/kitchen/generate
[KitchenGenerate] Payload: {identity_id: '...', ingredients: [...], extra_context: '', strict_mode: false}
[KitchenGenerate] Response status: 200
[KitchenGenerate] Response data: {recipes: [...]}
[KitchenGenerate] SUCCESS ✓
```

**Na stronie powinieneś zobaczyć:**
- Przycisk zmienia tekst na "⏳ Generuję..." (animacja)
- Toast notyfikacja: "✅ Przepisy wygenerowane!"
- 4 przepisy wyświetlone z:
  - 🍽️ Nazw (np. "Przepis 1: Kurczak smażony z ryżem")
  - Listy składników
  - Opisu przygotowania
  - Etykiet: kcal, białko, węglowodany, tłuszcze

#### Test 3: Brak składników

1. Wyczyść wszystkie tagi (kliknij × na każdym)
2. Kliknij "Generuj 4 przepisy"
3. Powinieneś zobaczyć Toast: "⚠️ Dodaj co najmniej jeden składnik"

**W konsoli:**
```
🔍 Składniki: []
```

#### Test 4: Serwer niedostępny

1. Zatrzymaj backend (`Ctrl+C` w terminalnie)
2. Kliknij "Generuj 4 przepisy"
3. Powinieneś zobaczyć Toast: "❌ Serwer nie odpowiada..."

**W konsoli:**
```
[KitchenGenerate] Health check failed
```

#### Test 5: Timeout (długi czas oczekiwania)

1. Uruchom backend
2. Dodaj składniki
3. Otwórz DevTools Network tab
4. Ustaw throttle na "Slow 3G" lub "GPRS"
5. Kliknij "Generuj"
6. Czekaj > 10 sekund
7. Powinieneś zobaczyć Toast: "⏱️ Przekroczono limit czasu (10 sekund)"

**W konsoli:**
```
[KitchenGenerate] Request timeout
```

#### Test 6: Brak logowania

1. Wyloguj się (clear localStorage)
2. Kliknij "Generuj"
3. Powinieneś zobaczyć Toast: "⚠️ Zaloguj się..."

**W konsoli:**
```
🔐 Token present: false
```

---

## 🔍 Backend Logi

Gdy klikniesz "Generuj", w terminalu (backend) powinieneś zobaczyć:

```
[KitchenGenerate] Incoming request: 5 ingredients, strict_mode=False
[KitchenGenerate] User: Tomasz, kcal_target: 2000, meal_kcal: 400
[KitchenGenerate] Ingredients: Kurczak, Ryż, Brokuły, Czosnek, Cebula
[KitchenGenerate] Avoid foods: brak
[KitchenGenerate] Calling ask_claude()...
[KitchenGenerate] Raw AI response (first 200 chars): [{"nazwa": "Kurczak smażony...
[KitchenGenerate] Parsed 4 recipes successfully ✓
[KitchenGenerate] Recipes validated successfully ✓
[KitchenGenerate] SUCCESS ✓
```

Jeśli jest błąd:
```
[KitchenGenerate] ERROR: Empty ingredients list
[KitchenGenerate] ERROR: Too many ingredients (31 > 30)
[KitchenGenerate] JSON Parse Error: Expecting value: line 1 column 1 (char 0)
[KitchenGenerate] Unexpected Error: ValueError: Response must be a list of recipes
```

---

## 🛠️ Debugging

### Jeśli nie widzisz logów w konsoli:

1. Otwórz Developer Tools (F12)
2. Przejdź na kartę "Console"
3. Upewnij się, że log level nie jest ustawiony na "Errors" czy "Warnings"
4. Filtr powinien być pusty (żaden filtr nie aktywny)

### Jeśli widzisz "Failed to fetch":

1. Sprawdź, czy backend jest uruchomiony (`http://localhost:8000/health`)
2. Sprawdź CORS headers w Network tab
3. Sprawdź, czy port 8000 jest dostępny

### Jeśli żaden przepis się nie wyświetla:

1. Sprawdź `[KitchenGenerate] Response data` w konsoli
2. Upewnij się, że struktura jest:
   ```json
   { "recipes": [ { "nazwa": "...", "składniki": [...], ... } ] }
   ```

---

## 📊 Oczekiwane Resultaty

### Sukces (200 OK):

**Frontend:**
- Toast: ✅ "Przepisy wygenerowane!"
- 4 przepisy wyświetlone
- Przycisk powraca do normalnego stanu

**Backend:**
```
[KitchenGenerate] SUCCESS ✓
```

---

## 🎯 Podsumowanie Zmian

| Komponent | Plik | Linia | Zmiana |
|-----------|------|-------|--------|
| Backend Endpoint | fitai_api.py | 3631 | Nowy POST `/app/kitchen/generate` |
| Backend Logging | fitai_api.py | 3631-3720 | Szczegółowe logi `[KitchenGenerate]` |
| Frontend Function | index.html | 8724 | Nowa `kitchenGenerate()` |
| Frontend Console Logs | index.html | 8724-8910 | Logi na każdym kroku |
| Button Handler | index.html | 2161 | `onclick="kitchenGenerate()"` |
| JSON Parsing | fitai_api.py | 3700-3720 | Obsługa markdown code blocks |
| Error Handling | fitai_api.py | 3715-3750 | HTTPException z polskimi komunikatami |
| Toast Display | index.html | 8820 | `showToast()` dla błędów i sukcesu |

---

## ✅ Checklist Testowania

- [ ] Backend się uruchamia bez błędów
- [ ] Frontend console ma logi `[KitchenGenerate]`
- [ ] Dodaję składniki - widzę je jako tagi
- [ ] Kliknę "Generuj" - widzę przycisk zmienia tekst
- [ ] Toast pojawia się "✅ Przepisy wygenerowane!"
- [ ] 4 przepisy wyświetlają się z wszystkimi danymi
- [ ] Test brak składników - Toast "⚠️ Dodaj..."
- [ ] Test timeout - Toast "⏱️ Przekroczono czas..."
- [ ] Backend logi pokazują `[KitchenGenerate] SUCCESS ✓`
- [ ] Brak błędów w DevTools Console

---

**Data: 2026-05-05**
**Wersja: 1.0**
**Status: ✅ Gotowy do testowania**
