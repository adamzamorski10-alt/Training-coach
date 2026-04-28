# FitAI SaaS Platform v2.0 - Dokumentacja

## 🎯 Przegląd Systemu

FitAI to nowoczesna platforma SaaS (Software as a Service) do zarządzania treningiem i dietą z zaawansowaną obsługą wielu użytkowników, systemem AI do zamiany posiłków/ćwiczeń oraz offline wsparciu (PWA).

### Kluczowe Cechy
✅ **5 głównych zakładek**: Home, My Day, Plan, Profile, Contact  
✅ **Modern Tech Noir design**: Glassmorphism, neonowe kolory (#00E5FF, #7C3AED)  
✅ **Zaawansowane animacje**: Slide-up, Spring effect, Pulse glow  
✅ **Multi-user**: Przełączanie pomiędzy użytkownikami z dropdown  
✅ **Persistent Substitutes DB**: Zapamiętane zamiany AI  
✅ **PWA Ready**: Offline support, push notifications, background sync  
✅ **Responsywny**: Mobile-first design  

---

## 📁 Struktura Plików

```
Training coach/
├── index.html                    # Wygenerowany główny dashboard
├── generate_html_complete.py     # Generator (v2.0 - SaaS Edition)
├── sw.js                         # Service Worker dla PWA
├── fitai_users.json              # Baza użytkowników
├── fitai_substitutes.json        # Zamiany posiłków/ćwiczeń (NEW)
├── fitai_api.py                  # API backend
├── fitai_discord_bot.py          # Discord integracja
├── fitai_utils.py                # Funkcje pomocnicze
└── netlify/functions/            # Serverless functions
    ├── create-checkout-session.js
    ├── process-reminders.js
    └── stripe-webhook.js
```

---

## 🎨 Design & UI/UX

### Kolorystyka
- **Neon Cyan**: `#00e5ff` (Primary accent)
- **Neon Purple**: `#7c3aed` (Secondary accent)
- **Deep Black**: `#0a0b10` (Background)
- **Card Background**: `rgba(255, 255, 255, 0.03)` (Glassmorphism)

### Typografia
- **Headings**: Syne (600, 700, 800)
- **Body**: Plus Jakarta Sans (300, 400, 500, 600, 700)

### Animacje
| Animacja | Cel | Duration |
|----------|-----|----------|
| `slideUpFade` | Przejścia między zakładkami | 0.4s |
| `springBounce` | Dzień w karuzeli | 0.6s cubic-bezier |
| `pulseNeon` | Przycisk PANEL | 2s infinite |

---

## 📊 Architektura Aplikacji

### State Management (JavaScript)
```javascript
const state = {
  currentUser: null,          // ID aktualnego użytkownika
  users: {},                  // Mapa użytkowników
  substitutes: {},            // Zapamiętane zamiany AI
  currentDay: 0,              // Indeks dnia (0-6)
  expandedItem: null,         // Aktualnie rozwinięty element
  manualFormType: null,       // Typ formularza (diet/training)
  days: ['Pon', 'Wt', 'Śr', ...] // Dni tygodnia
};
```

### Multi-User System
Każdy użytkownik ma własny obiekt w `fitai_users.json`:
```json
{
  "user123": {
    "name": "Marek",
    "age": 28,
    "height": 182,
    "weight": 84.5,
    "goals": ["strength", "cardio"],
    "equipment": ["dumbbells", "barbell"],
    "dietPlan": { "Pon": [...] },
    "trainingPlan": { "Pon": [...] }
  }
}
```

### Persistent Substitutes
Baza dostępnych zamienników w `fitai_substitutes.json`:
```json
{
  "substitutes": {
    "meals": {
      "kurczak": [
        { "name": "Indyk", "protein": 30, ... }
      ]
    },
    "exercises": {
      "wyciskanie_sztangi": [...]
    }
  }
}
```

---

## 🔑 Główne Funkcjonalności

### 1. **Home (Dashboard)**
- **KPI Cards**: Spójność (%), Kalorie (dzisiaj), Waga, Status planu
- **Consistency Chart**: Wykres słupkowy spójności 7 dni
- **Next Steps**: Sugerowane akcje (dodaj posiłek, zrób trening)
- **Recent Activity**: Historia ostatnich działań z ikonami i kalorią

### 2. **Mój Dzień (Daily Log)**
- **Dwa kontenery**: Dieta i Trening
- **Przyciski**:
  - 📌 Z Planu: Pobiera z planu użytkownika
  - ✏️ Inny: Manualny wpis z makroskładnikami
- **Neonowe Alerty**: Pojawiają się przy braku makroskładników
- **Smart Calc**: Suma makroskładników w real-time

### 3. **Plan (Meal & Training Schedule)**
- **Dzień Carousel**: Przyciski dni z animacją spring
- **Strzałki Nawigacji**: Przewijanie pomiędzy dniami
- **Expand Modal**: Kliknij posiłek/ćwiczenie → szczegóły + recepta
- **Zamień na inne**: System AI zaproponuje alternatywy z bazy

### 4. **Profil (4 podtabki)**
| Tabela | Zawartość |
|--------|-----------|
| **Dane** | Imię, wiek, wzrost, waga, cel, płeć, alergie |
| **Cele** | Checkboxy: Siłownia, Kardio, Mobilność, Masa |
| **Preferencje** | Sprzęt (hantle, sztanga...), Wykluczone potrawy |
| **Płatności** | Statyczne "w przygotowaniu" |

### 5. **Kontakt**
- **Discord Tile**: Przycisk + opcja kopiowania (z3tol)
- **Email Tile**: Mailto + opcja kopiowania (adam.zamorski.10@gmail.com)
- **FAQ**: Sekcja z pytaniami i odpowiedziami

---

## 🔄 User Flows

### Flow: Dodanie Posiłku
1. Użytkownik klika "📌 Z Planu" lub "✏️ Inny"
2. Jeśli Z Planu → system pobiera zaplanowany posiłek
3. Jeśli Inny → pokazuje się formularz (nazwa, makroskładniki)
4. Formularz dodaje element do dziennika
5. System oblicza sumy i sprawdza alerty

### Flow: Zamiana Posiłku
1. W zakładce "Plan" użytkownik klika na posiłek
2. Otwiera się modal z szczegółami i przepisem
3. Klika "Zamień na inne"
4. System szuka alternatyw z `fitai_substitutes.json`
5. Proponuje podobne posiłki (zapamiętane zamiany)
6. Użytkownik wybiera → zapis w bazie

### Flow: Przełączanie Użytkownika
1. Klik na ikonę użytkownika w navbar
2. Dropdown pokazuje listę użytkowników
3. Wybranie użytkownika → załadowanie jego danych
4. Wszystkie widoki aktualizują się (KPI, plan, profile)

---

## 🌐 PWA Features

### Service Worker (`sw.js`)
- **Install**: Cachowanie app shell (index.html)
- **Activate**: Czyszczenie starych cache'y
- **Fetch**: Network-first strategy (online) + cache fallback (offline)
- **Push**: Obsługa push notifications
- **Background Sync**: Synchronizacja z serwerem gdy connection wrócił

### Offline Support
```javascript
// Network first, fallback to cache
fetch(request)
  .then(response => { ... cache it ... })
  .catch(() => {
    // Go to cache
    return caches.match(request)
      .catch(() => return offlinePage);
  });
```

### Push Notifications
```json
{
  "title": "Brakuje Ci białka!",
  "body": "Dodaj jeszcze 30g aby osiągnąć cel",
  "tag": "macro-alert",
  "actions": [
    { "action": "open", "title": "Dodaj" }
  ]
}
```

---

## 🔌 API Integration Points

### Endpoints to Implement
```
GET  /api/users              # Lista użytkowników
GET  /api/users/:id          # Dane użytkownika
POST /api/users/:id          # Update profilu
GET  /api/plans/:id/meal     # Plan posiłków
GET  /api/plans/:id/training # Plan treningowy
POST /api/logs               # Zaloguj działanie
GET  /api/substitutes        # Zamiany (cache locally)
POST /api/sync               # Background sync
```

---

## 📱 Responsive Breakpoints

- **Mobile**: < 768px
  - Sidebar: Ukryty, mobile menu toggle
  - Layout: Single column
  - Grid: 2x2 KPI cards

- **Tablet**: 768px - 1024px
  - Sidebar: Visible
  - Layout: Sidebar + Main
  - Grid: Responsive adjustments

- **Desktop**: > 1024px
  - Sidebar: Full width (w-64)
  - Layout: Optimal spacing
  - Grid: Full multi-column layout

---

## 🚀 Deployment

### Netlify
```bash
# Build
npm run build

# Deploy
netlify deploy --prod
```

### Environment Variables
```env
VITE_API_URL=https://api.fitai.com
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_KEY=xxx
```

---

## 📈 Metrics & Analytics

### KPIs Tracked
- Consistency score (%)
- Calories consumed vs target
- Weight trend
- Workout completion rate
- Macro adherence

### Events to Log
- User login/logout
- Meal/exercise logged
- Substitutions made
- Profile updates
- PWA install

---

## 🔒 Security Notes

1. **User Isolation**: Każdy user ma separate record
2. **LocalStorage**: Dane tymczasowe (nie sensitive data)
3. **HTTPS**: Wymagane do Service Worker
4. **CORS**: API CORS policy dla domains
5. **Input Validation**: Sanitize user inputs

---

## 📝 Changelog v2.0

- ✅ Complete UI rewrite (Modern Tech Noir)
- ✅ 5 tabs + Profile subtabs
- ✅ Multi-user support
- ✅ Glassmorphism effects
- ✅ Advanced animations
- ✅ PWA Service Worker
- ✅ Substitutes database
- ✅ Neon alerts
- ✅ Responsive design
- ✅ Offline support

---

## 🎓 Jak Zacząć

1. **Otwórz `index.html` w przeglądarce**
   - Localhost lub Netlify

2. **Wybierz użytkownika** z dropdown (user123)

3. **Przejrzyj sekcje**:
   - Home: Dashboard z KPI
   - My Day: Logowanie posiłków/ćwiczeń
   - Plan: Zaplanowany plan
   - Profile: Personalizacja
   - Contact: Kontakt

4. **Test Offline**:
   - DevTools → Network → Offline
   - Aplikacja powinna działać z cache

---

## 🐛 Known Issues & TODOs

- [ ] Backend API integration
- [ ] Real data loading from fitai_users.json
- [ ] AI substitution engine
- [ ] Push notifications testing
- [ ] Analytics setup
- [ ] Stripe integration
- [ ] Email notifications
- [ ] Dark mode toggle (zaznaczony)

---

## 📞 Support

- Discord: z3tol
- Email: adam.zamorski.10@gmail.com
- GitHub Issues: [project-repo]

---

**FitAI v2.0 © 2026 - Premium Training & Nutrition Platform**
