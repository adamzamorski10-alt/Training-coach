# FitAI SaaS Platform v2.0 - Quick Start Guide

## 🚀 Szybki Start

### 1. Otwórz Dashboard
```bash
# Otwórz plik w przeglądarce
open index.html
# lub na Windowsie
start index.html
```

### 2. Przełącz Użytkownika
- Kliknij ikonę 👤 w navbar (prawy górny róg)
- Wybierz użytkownika z dropdown (domyślnie: Marek)
- Dashboard zaktualizuje się automatycznie

### 3. Poznaj Zakładki

#### 🏠 Home (Dashboard)
- **Consistency**: Procent spójności z planem
- **Calories**: Spalone vs cel dzisiaj
- **Weight**: Aktualna waga
- **Chart**: 7-dniowy trend spójności
- **Next Step**: Sugerowane działanie

#### 📋 My Day (Mój Dzień)
1. Dodaj posiłek:
   - 📌 Z Planu: Zaplanowany posiłek
   - ✏️ Inny: Manualnie (nazwa, białko, węgle, tłuszcz)
2. Dodaj trening:
   - 📌 Z Planu: Zaplanowany trening
   - ✏️ Inny: Ćwiczenie bez planu
3. Monitoruj alerty 🚀 (brakujące makroskładniki)

#### 📅 Plan (Dieta & Trening)
1. Przejdź między dniami:
   - ← → strzałkami
   - lub przyciski dni w karuzeli
2. Kliknij posiłek/ćwiczenie → **Expand Modal**
3. Wyświetli się:
   - Szczegóły makroskładników
   - Przepis / Instrukcja techniki
   - Tagi sprzętowe
4. Kliki "Zamień na inne" → AI zaproponuje alternatywy

#### 👤 Profil (Personalizacja)
1. **Dane**: Imię, wiek, wzrost, waga, cel, płeć, alergie
2. **Cele**: Zaznacz zainteresowania (Siłownia, Kardio, Mobilność, Masa)
   - Wpłynie na Twój plan
3. **Preferencje**: Sprzęt dostępny + wykluczone potrawy
   - Jeśli odznaczysz hantlę, usuną się z planu
4. **Płatności**: Status Premium (w przygotowaniu)

#### 💬 Kontakt
- **Discord**: Dołącz do społeczności (z3tol) - kopia do schowka
- **Email**: Wyślij wiadomość (adam.zamorski.10@gmail.com)
- **FAQ**: Popularne pytania z odpowiedziami

---

## 🎨 Design Features

### Kolorystyka
```css
Primary: #00E5FF (Neon Cyan)  - Przyciski, akcenty
Secondary: #7C3AED (Purple)   - Gradienty
Background: #0a0b10           - Głębokie czarne
```

### Efekty
- **Glassmorphism**: Rozmyte tła, półprzezroczyste karty
- **Neon Glow**: Pulsujący przycisk PANEL
- **Animacje**: Płynne przejścia między zakładkami
- **Spring Effect**: Dzień carousel

---

## 📱 Offline Mode

Aplikacja automatycznie cachuje dane:
1. **Pierwsza wizyta**: Pobierze wszystkie pliki
2. **Offline**: Wszystko działa z cache
3. **Powrót online**: Synchronizuje dane

Aby testować:
1. DevTools (F12)
2. Network tab
3. Ustaw na "Offline"
4. Strona powinna działać normalnie ✅

---

## 🔧 Integracja z Backend

### API Endpoints (do zaimplementowania)
```
GET  /api/users              # Lista użytkowników
GET  /api/users/:id          # Dane użytkownika
POST /api/users/:id          # Update profilu
GET  /api/plans/:id/meal     # Plan posiłków
GET  /api/plans/:id/training # Plan treningowy
POST /api/logs               # Zaloguj działanie
```

### Jak Łączyć
1. W `initApp()` zamiast `loadUsersFromStorage()`:
```javascript
async function loadUsers() {
  const resp = await fetch('/api/users');
  state.users = await resp.json();
}
```

2. Przy zapisie danych:
```javascript
async function saveUserData(userId, data) {
  await fetch(`/api/users/${userId}`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}
```

---

## 📊 Struktura Danych

### Użytkownik
```json
{
  "user123": {
    "name": "Marek",
    "age": 28,
    "weight": 84.5,
    "caloriesTarget": 2463,
    "proteinTarget": 185,
    "goals": ["strength", "cardio"],
    "equipment": ["dumbbells", "barbell", "mat"],
    "dietPlan": {
      "Pon": [
        {
          "id": "1",
          "name": "Owsianka",
          "protein": 15,
          "carbs": 50,
          "fat": 5,
          "kcal": 300
        }
      ]
    }
  }
}
```

### Zamiany (Substitutes)
```json
{
  "substitutes": {
    "meals": {
      "kurczak": [
        { "name": "Indyk", "protein": 30, ... },
        { "name": "Tofu", "protein": 15, ... }
      ]
    },
    "exercises": {
      "wyciskanie_sztangi": [
        { "name": "Pompki", "difficulty": "easy" }
      ]
    }
  }
}
```

---

## 🐛 Troubleshooting

| Problem | Rozwiązanie |
|---------|------------|
| Brak użytkownika | Sprawdź `fitai_users.json`, dodaj nowego |
| Animacje nie działają | Sprawdź CSS w `<style>` |
| Offline nie działa | SW wymaga HTTPS/localhost, sprawdź DevTools |
| Formularz nie wysyła | Sprawdź event listener na `#manualEntryForm` |
| Wykresy nie rysują | Chart.js musi być załadowany z CDN |

---

## 📈 Następne Kroki

### Bez Priorytetu
1. [ ] Backend API integration
2. [ ] Real data z `fitai_users.json`
3. [ ] Email notifications
4. [ ] Push notifications testing
5. [ ] Analytics (Google Analytics)
6. [ ] Stripe payments integration
7. [ ] Discord webhook dla alertów
8. [ ] AI suggestion engine

### Opcjonalne
- Dark/Light mode toggle
- Export data (PDF, CSV)
- Social sharing (workout achievements)
- Leaderboard (gamification)
- Video tutorials (ćwiczenia)

---

## 🔐 Security Checklist

- [ ] HTTPS enabled
- [ ] CORS configured
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] Rate limiting na API
- [ ] User authentication
- [ ] Data encryption at rest

---

## 📝 Notes dla Deweloperów

### State Management
Wszystko w `state` obiekcie - możesz debugować w konsoli:
```javascript
console.log(state);
console.log(state.users[state.currentUser]);
```

### DOM Selectors
```javascript
// Znaleźć elementy
document.getElementById('dashboard')        // Po ID
document.querySelectorAll('.glass-card')    // Po klasie
document.querySelector('button.btn-neon')   // Po selektorze CSS
```

### Dodać Event Listener
```javascript
document.getElementById('myButton').addEventListener('click', () => {
  // Logika
});
```

### LocalStorage
```javascript
// Zapisać
localStorage.setItem('key', JSON.stringify(data));

// Odczytać
const data = JSON.parse(localStorage.getItem('key'));
```

---

## 📞 Support

- **Discord**: z3tol
- **Email**: adam.zamorski.10@gmail.com
- **Issues**: GitHub

---

**FitAI v2.0 © 2026** 
*Premium Platform do Treningu & Odżywiania*
