# 🍳 KUCHNIA AI - QUICK START GUIDE

## ⚡ Szybki Start (5 minut)

### 1. Uruchom Backend
```bash
cd "c:\Users\adamz\OneDrive\Desktop\Projects\Training coach"
uvicorn fitai_api:app --reload --port 8000
```

### 2. Otwórz App
Otwórz w przeglądarce:
- `http://localhost:5500/index.html` (jeśli masz Live Server)
- Lub kliknij F5 na otwartym index.html

### 3. Zaloguj Się
Zaloguj na swoje konto

### 4. Przejdź do Kuchni AI
```
Menu → Plan → Dieta → Kuchnia AI
```

### 5. Dodaj Składniki
```
Wpisz: Kurczak, Ryż, Brokuły, Czosnek
Wciśnij: Enter lub kliknij "Dodaj"
```

### 6. Generuj Przepisy
```
Kliknij: "🍳 Generuj 4 przepisy"
```

### 7. Obserwuj Result
- Przycisk zmieni tekst na "⏳ Generuję..."
- Pojawi się Toast: ✅ "Przepisy wygenerowane!"
- Poniżej pojawią się 4 przepisy

---

## 🔧 TECHNICZNE DETALE

### Backend Endpoint
```
POST /app/kitchen/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "identity_id": "uuid",
  "ingredients": ["Kurczak", "Ryż", "Brokuły"],
  "extra_context": "",
  "strict_mode": false
}
```

### Response
```json
{
  "recipes": [
    {
      "nazwa": "Kurczak z ryzem",
      "składniki": ["kurczak", "ryż"],
      "opis": "Szybka, pyszna potrawa...",
      "kalorie": 350,
      "białko": 35,
      "węglowodany": 40,
      "tłuszcze": 8
    }
  ]
}
```

### Console Logs (Frontend)
Aby zobaczyć debugowanie:
1. Wciśnij F12
2. Przejdź na kartę "Console"
3. Poszukaj logów zaczynających się od `[KitchenGenerate]`

```
🔍 Składniki: ['Kurczak', 'Ryż', 'Brokuły']
📝 Identity ID: uuid-123
🔐 Token present: true
✅ Health check passed
[KitchenGenerate] Response status: 200
[KitchenGenerate] SUCCESS ✓
```

### Console Logs (Backend)
W terminalu z uvicornem:
```
[KitchenGenerate] Incoming request: 3 ingredients
[KitchenGenerate] Parsed 4 recipes successfully ✓
```

---

## ❌ TROUBLESHOOTING

### Problem: "Serwer nie odpowiada"
**Rozwiązanie:**
1. Upewnij się, że backend jest uruchomiony
2. Sprawdź czy port 8000 jest dostępny
3. Odwiedź: `http://localhost:8000/health`

### Problem: "Zaloguj się"
**Rozwiązanie:**
1. Zaloguj się na swoje konto
2. Sprawdź czy token jest w `state.token`
3. Otwórz DevTools (F12) i sprawdź localStorage

### Problem: Przepisy się nie wyświetlają
**Rozwiązanie:**
1. Sprawdź console logi
2. Poszukaj błędu: `[KitchenGenerate] ERROR`
3. Sprawdź Network tab w DevTools

### Problem: "Zbyt mało składników"
**Rozwiązanie:**
1. Dodaj co najmniej 1 składnik
2. Jeśli masz strict_mode ON - dodaj więcej (min 4-5)

---

## 📋 LISTA ZMIAN

✅ Dodany endpoint `/app/kitchen/generate` w backend'u  
✅ Nowa funkcja `kitchenGenerate()` w frontend'u  
✅ Przycisk "Generuj" wywołuje nową funkcję  
✅ Authorization header jest wysyłany  
✅ Console logging na każdym kroku  
✅ JSON parsing z obsługą markdown  
✅ Error handling z polskimi komunikatami  
✅ Toast notifications  
✅ AbortController timeout (10s)  
✅ Health check ping  
✅ Rendering 4 przepisów z makroskładnikami  

---

## 🧪 TEST VERIFICATION

Aby sprawdzić czy wszystko jest gotowe:
```bash
python verify_kitchen_ai.py
```

Oczekiwany output:
```
✅ ALL CHECKS PASSED - Ready for testing!
```

---

## 📞 SUPPORT

Jeśli masz problemy:
1. Sprawdź console logi (`F12` → Console)
2. Sprawdź Network tab (`F12` → Network)
3. Sprawdź backend logi w terminalu
4. Przeczytaj `TEST_KITCHEN_AI.md` dla szczegółów

---

**Wersja:** 1.0  
**Data:** 5 maja 2026  
**Status:** ✅ TESTOWANIE
