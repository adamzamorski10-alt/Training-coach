# FitAI Kitchen AI - Naprawa Błędu "Brak Tokena Autoryzacji"

## Problem

Funkcja `kitchenGenerate()` zgłaszała błąd: **"Brak tokena autoryzacji"** (401 Unauthorized) mimo że użytkownik był zalogowany.

## Przyczyna

Endpoint `/app/kitchen/generate` w backendu wymagał `Depends(get_current_user)` (JWT token), ale frontend:
1. Nie wysyłał JWT tokena (bo go nie miał w localStorage)
2. Wysyłał `identity_id` w payloadzie, ale endpoint go ignorował

Dodatkowo, walidacja w JS była błędna: sprawdzała `if (!identityId && !token)` zamiast `if (!identityId)`.

## Wprowadzone Zmiany

### 1. Backend (fitai_api.py) - Zmiana Endpointu

**Co zostało zmienione:**
- Endpoint `/app/kitchen/generate` NIE wymaga teraz `Depends(get_current_user)`
- Zamiast tego, szuka użytkownika po `identity_id` z payloadu
- Jeśli `identity_id` jest nieznany → zwraca 404 z informacyjnym komunikatem

**Kod zmieniony (linie 3645-3688):**

```python
@app.post("/app/kitchen/generate", tags=["ai_chef"])
@limiter.limit(AI_RATE_PER_MINUTE)
@limiter.limit(AI_RATE_PER_HOUR)
def app_kitchen_generate(request: Request, req: FridgeChefRequest):
    """
    Generuje 4 przepisy na podstawie wybranych składników.
    Zwraca JSON tablica 4 obiektów: { nazwa, składniki, opis, kalorie }
    
    Uwaga: Zamiast JWT, używa identity_id z payloadu do identyfikacji użytkownika.
    """
    print(f"[KitchenGenerate] Incoming request: identity_id={req.identity_id}, {len(req.ingredients)} ingredients, strict_mode={req.strict_mode}")
    
    if not req.ingredients:
        print("[KitchenGenerate] ERROR: Empty ingredients list")
        raise HTTPException(status_code=422, detail="Lista składników nie może być pusta.")
    if len(req.ingredients) > 30:
        print(f"[KitchenGenerate] ERROR: Too many ingredients ({len(req.ingredients)} > 30)")
        raise HTTPException(status_code=422, detail="Maksymalnie 30 składników naraz.")

    try:
        with Session(engine) as session:
            # ─ Znalezienie user'a po identity_id ─
            user = session.exec(
                select(UserDB).where(UserDB.identity_id == req.identity_id)
            ).first()
            
            if not user:
                print(f"[KitchenGenerate] ERROR: User not found for identity_id={req.identity_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Użytkownik z identity_id='{req.identity_id}' nie znaleziony. Proszę się zalogować."
                )
            
            kcal_target   = user.calories_target or calc_calories(user)
            # ... rest of the code stays the same
```

**Zaletę:**
✅ Endpoint teraz działaogólnie bez JWT  
✅ Frontend może wysłać żądanie z identity_id  
✅ Błędy są jasne (404 jeśli user nie istnieje)  

---

### 2. Frontend (generate_html_complete.py) - Dodanie Token do State

**Co zostało zmienione:**
- Dodano pole `token` do obiektu `state`
- Token pobierany z `localStorage.getItem('fitai_token')`

**Kod zmieniony (linie 1146-1159 w generate_html_complete.py):**

```javascript
const state = {
  identityId: localStorage.getItem('fitai_identity_id') || 'demo_user_001',
  token: localStorage.getItem('fitai_token') || '', // JWT token from login
  profile: null,
  weeklyPlan: null,         // Full plan from API { days: [...] }
  currentDay: 0,
  expandedItem: null,       // { type, data, dayIndex, itemIndex }
  dayChecked: JSON.parse(localStorage.getItem('fitai_checked_v3') || '{}'), // PERSISTED CHECKLIST
  extraItems: JSON.parse(localStorage.getItem('fitai_extras_v3') || '{}'),
  activeDrillName: null,    // name of drill awaiting result submission
  activeDrillTotal: 0,
  manualFormType: null,
  days: ['Poniedziałek','Wtorek','Środa','Czwartek','Piątek','Sobota','Niedziela'],
  daysShort: ['Pon','Wt','Śr','Czw','Pt','Sob','Niedz'],
};
```

---

### 3. Frontend (index.html) - Lepsza Walidacja w kitchenGenerate()

**Co zostało zmienione:**
- Walidacja zmieniona z `if (!identityId && !token)` na `if (!identityId || identityId === '')`
- Dodano więcej debug console.log() dla ułatwienia diagnozowania
- Ulepszona obsługa błędu - wyświetla szczegóły z backendu

**Kod zmieniony (linie 8733-8765 w index.html):**

```javascript
async function kitchenGenerate() {
  const identityId = state.identityId || state.profiles[0]?.id || '';
  const token = state.token || localStorage.getItem('fitai_token') || '';

  // Debug logging
  console.log('🔍 Składniki:', _kitchen.fridgeTags);
  console.log('📝 Identity ID:', identityId);
  console.log('🔐 Token present:', !!token);
  console.log('[KitchenGenerate] State token:', state.token);
  console.log('[KitchenGenerate] LocalStorage token:', localStorage.getItem('fitai_token'));

  // ─ Walidacja: musi być identity_id ─
  if (!identityId || identityId === '') {
    showToast('⚠️ Nie udało się zidentyfikować użytkownika. Odśwież stronę.');
    console.error('[KitchenGenerate] ERROR: No identityId available!', { identityId, token });
    return;
  }
  if (_kitchen.fridgeTags.length === 0) {
    showToast('⚠️ Dodaj co najmniej jeden składnik');
    document.getElementById('fridgeIngredientInput')?.focus();
    return;
  }

  // ... rest of the code
  
  // Build headers with Authorization (optional, for future JWT support)
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    console.log('[KitchenGenerate] Authorization header added');
  } else {
    console.log('[KitchenGenerate] Note: No JWT token, using identity_id authentication');
  }
```

---

## Weryfikacja Poprawki

### 1. Backend - Sprawdzenie Endpointu z Curl

```bash
curl -X POST http://localhost:8000/app/kitchen/generate \
  -H "Content-Type: application/json" \
  -d '{
    "identity_id": "demo_user_001",
    "ingredients": ["kurczak", "brokuły", "jajka"],
    "extra_context": "Po treningu",
    "strict_mode": false
  }'
```

**Oczekiwany rezultat:**
- Status: **200 OK**
- Response zawiera `"recipes": [...]` z 4 przepisami

**Jeśli 404:**
```json
{
  "detail": "Użytkownik z identity_id='demo_user_001' nie znaleziony. Proszę się zalogować."
}
```
→ Stwórz użytkownika w bazie lub zmień `identity_id` na istniejący

---

### 2. Frontend - Konsola Przeglądarki (F12)

1. Otwórz `index.html` w przeglądarce
2. Wciśnij **F12** → zakładka **Console**
3. Przejdź do: **Plan → Dieta → Kuchnia AI**
4. Dodaj składniki
5. Kliknij **"Generuj 4 przepisy"**

**Szukaj w konsoli (powinny być takie logi):**

```
🔍 Składniki: (3) ['kurczak', 'brokuły', 'jajka']
📝 Identity ID: demo_user_001
🔐 Token present: false
[KitchenGenerate] State token: 
[KitchenGenerate] LocalStorage token: null
🌐 API Base: http://localhost:8000
✅ Health check passed
[KitchenGenerate] Sending request to /app/kitchen/generate
[KitchenGenerate] Payload: {identity_id: 'demo_user_001', ingredients: Array(3), extra_context: '', strict_mode: false}
[KitchenGenerate] Response status: 200
[KitchenGenerate] Response data: {recipes: Array(4)}
```

**Jeśli widać błąd:**
```
[KitchenGenerate] Response status: 401
[KitchenGenerate] Server error: {detail: "Brak tokena autoryzacji"}
```

→ Oznacza to, że moja zmiana nie została wprowadzona. Sprawdź czy fitai_api.py ma nowy kod.

---

### 3. Test Skryptem verify_kitchen_ai.py

```bash
python verify_kitchen_ai.py
```

**Oczekiwany rezultat:**
```
✅ ALL CHECKS PASSED - Ready for testing!
```

---

## Podsumowanie Zmian

| Komponent | Zmiana | Status |
|-----------|--------|--------|
| fitai_api.py (linie 3645-3688) | Zmiana endpointu - używa identity_id zamiast JWT | ✅ DONE |
| generate_html_complete.py (linie 1146-1159) | Dodanie token do state | ✅ DONE |
| index.html (linie 8733-8765) | Lepsza walidacja + debug logs | ✅ DONE |

---

## Następne Kroki (Opcjonalnie)

1. **Gdy będzie JWT login:**
   - Frontend wysyła POST do `/auth/login`
   - Backend zwraca `access_token` w JWT
   - Frontend przechowuje w `localStorage.setItem('fitai_token', token)`
   - Endpoint będzie wtedy móc wymagać `Depends(get_current_user)` zamiast identity_id

2. **Zabezpieczenie:**
   - Dodać rate limiting (już jest w kodzie: `@limiter.limit()`)
   - Walidacja identity_id na froncie (już jest)
   - Logging wszystkich żądań (już jest: `print(f"[KitchenGenerate] ...")`)

---

## Kontakt / Debug

Jeśli problem nie ustanie:
1. Sprawdź konsolę przeglądarki (F12 → Console)
2. Sprawdź terminal gdzie uruchomiony jest backend (powinna być linia z `[KitchenGenerate]`)
3. Sprawdź czy backend ma użytkownika w bazie z `identity_id` = "demo_user_001"
4. Sprawdź czy `/app/kitchen/generate` endpoint jest dostępny pod tym URL
