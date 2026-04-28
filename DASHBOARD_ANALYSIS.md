# FitAI Dashboard - Complete Feature Analysis

## MAIN NAVIGATION TABS (Sidebar)

| Tab | Icon (Original) | ID | Description |
|-----|------------|----|----|
| **Dashboard** | 📊 | `dashboard-tab` | Main analytics and KPI view |
| **Panel** | ⚙️ | `panel-tab` | User profile settings |
| **Check-in** | ✅ | `checkin-tab` | Daily food & workout logging |
| **Integrations** | 🔗 | `integrations-tab` | Discord and external service connections |
| **Billing** | 💳 | `billing-tab` | Payment plans and subscription management |

---

## 1. DASHBOARD TAB (`dashboard-tab`)

### KPI Cards (5 Metrics)
1. **Plan** (`id="kpiPlan"`)
   - Display: Subscription tier (e.g., "free", "pro")
   - Field: User's current plan

2. **Rola** (Role) (`id="kpiRole"`)
   - Display: User role (e.g., "user", "admin")
   - Field: User's system role

3. **Streak** (`id="kpiStreak"`)
   - Display: Numeric value (0 or higher)
   - Field: Days of consecutive check-ins

4. **Spójność** (Consistency) (`id="kpiConsistency"`)
   - Display: Percentage value (e.g., "0%")
   - Field: Check-in completion rate

5. **Cele** (Goals) (`id="kpiTargets"`)
   - Display: Numeric value (0 or higher)
   - Field: Number of active fitness goals

### Weight Tracking Chart
- **Chart Type**: Line chart using Chart.js
- **Element ID**: `weightChart`
- **Data**: 
  - X-axis: `data.dates` from `/weight-history` API
  - Y-axis: `data.weights` (in kg)
- **Features**:
  - Blue/cyan colored line (`#00e5ff`)
  - Semi-transparent fill beneath the line
  - Point markers at each data point
  - Grid background
  - Loading spinner while fetching data
- **Data Source**: Fetches from `/weight-history` API endpoint

### Loading State
- **Element ID**: `chartLoading`
- Display: Gear emoji spinner (⚙️) while chart data is loading

---

## 2. PANEL TAB (User Profile) (`panel-tab`)

### Section Title
- "Profil Użytkownika" (User Profile)

### Onboarding Form (`id="onboardingForm"`)
**Fields:**
1. **Imię** (Name)
   - Type: Text input
   - Name attribute: `name`
   - Required: Yes
   - Placeholder: (none specified)

2. **Wiek** (Age)
   - Type: Number input
   - Name attribute: `age`
   - Min value: 12
   - Max value: 99
   - Required: Yes

**Submit Button**: "Zapisz Profil" (Save Profile)
- Posts to `/profile` API endpoint
- Success message: "✅ Profil zapisany!" in cyan
- Error message: "❌ Błąd: [error message]" in red

**Status Message Container**: `id="profileStatus"`
- Initial text: "Uzupełnij swoje dane." (Complete your data)
- Shows feedback on form submission

---

## 3. CHECK-IN TAB (`checkin-tab`)

### Section Title
- "✅ Daily Check-in"

### Check-in Form (`id="checkinForm"`)
**Fields:**

1. **Dzisiejsze posiłki** (Today's Meals)
   - Type: Textarea
   - Name attribute: `food`
   - Placeholder: "np. owsianka, kurczak z ryżem" (e.g., oatmeal, chicken with rice)
   - Min height: 6 lines

2. **Trening** (Workout)
   - Type: Textarea
   - Name attribute: `workout`
   - Placeholder: "np. push day, 45 minut" (e.g., push day, 45 minutes)
   - Min height: 6 lines

**Submit Button**: "Wyślij Check-in" (Send Check-in)
- Posts to `/checkin` API endpoint
- Form clears after successful submission
- Success message: "✅ Check-in wysłany!" (Check-in sent!)
- Error message: "❌ Błąd: [error message]"

**Status Message Container**: `id="checkinStatus"`
- Initial text: "Brak dzisiejszego check-in'u." (No today's check-in)

---

## 4. INTEGRATIONS TAB (`integrations-tab`)

### Section Title
- "🔗 Integracje" (Integrations)

### Discord Integration Form (`id="discordForm"`)
**Fields:**

1. **Discord User ID**
   - Type: Text input
   - Name attribute: `discord_id`
   - Placeholder: "Discord User ID"

**Submit Button**: "Połącz Discord" (Connect Discord)
- Posts to `/integrations/discord` API endpoint
- Form clears after successful submission
- Success message: "✅ Discord połączony!" (Discord connected!)
- Error message: "❌ Błąd: [error message]"

**Status Message Container**: `id="integrationStatus"`
- Initial text: "Brak aktywnych integracji." (No active integrations)

### Note
- Currently only Discord integration is shown
- Extensible for additional integrations

---

## 5. BILLING TAB (`billing-tab`)

### Section Title
- "💳 Plan Płatności" (Payment Plan)

### Plan Information Display
- **Element ID**: `planBadge`
- Shows current subscription tier (e.g., "free")
- Initial value pulled from profile data

### Upgrade Button
- **Button ID**: `buyProBtn`
- Text: "Kup Pro (Stripe)" (Buy Pro - Stripe)
- Action: 
  - POST to `/stripe/checkout` API endpoint
  - Receives `session.url` for Stripe checkout
  - Redirects user to Stripe payment page
  - Error alert: "❌ Błąd płatności: [error message]" (Payment error)

**Status Message Container**: `id="billingStatus"`
- Initial text: "Jesteś na planie free." (You are on the free plan)

---

## 6. HEADER & AUTHENTICATION

### Header Section
- **App Title**: "FitAI Dashboard"
- **Status Display**: `id="status"` 
  - Shows: "Sprawdzam logowanie..." (Checking login...) initially
  - When logged in: "Zalogowano: [email]" (Logged in: [email])
  - When logged out: "Niezalogowany" (Not logged in)

- **Version Display**: `id="version"`
  - Shows: "v--" initially
  - Updates to: "v[api_version]" from `/version` API endpoint

### Authentication Buttons (Header)
1. **Zaloguj** (Login) - `id="loginBtn"`
   - Shows when not logged in
   - Uses Netlify Identity widget

2. **Rejestracja** (Sign up) - `id="signupBtn"`
   - Shows when not logged in
   - Uses Netlify Identity widget

3. **Wyloguj** (Logout) - `id="logoutBtn"`
   - Hidden until user logs in
   - Logs out via Netlify Identity

### Locked State Screen
**Displayed when:**
- User is not logged in

**Elements:**
- Large lock emoji (🔒)
- Heading: "Panel chroniony" (Protected panel)
- Message: "Zaloguj się aby uzyskać dostęp do pełnego dashboardu." (Log in to access the full dashboard)
- **Zaloguj** button - `id="loginModal"`
- **Rejestracja** button - `id="signupModal"`

---

## 7. USER INFORMATION FIELDS

### Stored User Data (from Profile)
1. **Email** - From Netlify Identity
2. **Name** (`profile.name`) - Text, from profile form
3. **Age** (`profile.age`) - Number, from profile form
4. **Plan** (`profile.plan`) - String, subscription tier
5. **Discord ID** - Optional, from integration form

### Data Displayed
1. Plan type
2. User role
3. Consistency percentage
4. Streak counter
5. Active goals count

---

## 8. WORKOUT FEATURES

### Data Collection
- **Workout Logging**: Daily workout description in check-in form
- **Placeholder Example**: "push day, 45 minut" (push day, 45 minutes)
- **Format**: Free-form text description

### Data Display
- Displayed as part of check-in functionality
- No dedicated workout visualization/calendar shown in original

---

## 9. DIET/NUTRITION FEATURES

### Data Collection
- **Meal Logging**: Daily meals in check-in form
- **Field Name**: "Dzisiejsze posiłki" (Today's Meals)
- **Placeholder Example**: "owsianka, kurczak z ryżem" (oatmeal, chicken with rice)
- **Format**: Free-form text description

### Data Display
- Displayed as part of check-in functionality
- No dedicated meal plan or nutrition tracking shown

---

## 10. GOALS & PREFERENCES

### Goals Tracking
- **Goal Counter** (`id="kpiTargets"`)
  - Displays number of active goals
  - Initial value: 0
  - Data source: Not explicitly shown where goals are created/managed

### Preferences
- **None explicitly shown in original dashboard**
- Could be extended in profile form

---

## 11. CHARTS & VISUALIZATIONS

### Weight Progress Chart
- **Chart Library**: Chart.js 4.4.3
- **Chart Type**: Line chart
- **Title**: "Postęp Wagi" (Weight Progress)
- **Data**:
  - Labels: Dates from API
  - Dataset: Weight values in kg
- **Styling**:
  - Line color: `#00e5ff` (cyan)
  - Background: `rgba(0, 229, 255, 0.1)` (semi-transparent cyan)
  - Point color: Cyan
  - Point size: 4px radius
  - Tension: 0.4 (smooth curve)
- **Grid**: Cyan with transparency
- **Legend labels**: Gray color
- **Responsive**: Yes
- **Loading state**: Shows gear emoji while fetching

---

## 12. API ENDPOINTS REFERENCED

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/profile` | GET | Fetch user profile data |
| `/profile` | POST | Update user profile (name, age) |
| `/checkin` | POST | Submit daily check-in (meals, workout) |
| `/integrations/discord` | POST | Connect Discord account |
| `/stripe/checkout` | POST | Create Stripe checkout session |
| `/weight-history` | GET | Fetch weight tracking data |
| `/version` | GET | Fetch API version info |

---

## 13. FORMS SUMMARY

| Form ID | Tab | Title | Fields | Submit Action |
|---------|-----|-------|--------|--------|
| `onboardingForm` | Panel | Profil Użytkownika | Name (text), Age (number) | POST `/profile` |
| `checkinForm` | Check-in | Daily Check-in | Food (textarea), Workout (textarea) | POST `/checkin` |
| `discordForm` | Integrations | Integracje | Discord ID (text) | POST `/integrations/discord` |

---

## 14. DESIGN ELEMENTS

### Color Scheme
- **Primary Color**: Cyan (`#00e5ff`)
- **Secondary Color**: Violet (`rgba(124, 58, 237, 0.06)`)
- **Background**: Dark slate (`#0a0b0f`, `#0f1117`, `#1e293b`)
- **Text**: Light gray/white (`#f0f2f8`)
- **Accent**: Glass-morphism with cyan borders

### UI Components
- **Glass cards**: Semi-transparent panels with blur effect
- **Neon glow**: Hover effect on cards
- **Buttons**: Cyan background with brightness hover effect
- **Inputs**: Dark glass styling with cyan borders
- **Status messages**: Colored text (cyan for success, red/orange for errors)

### Responsive Design
- **Desktop**: Full layout with sidebar visible
- **Mobile**: Collapsed sidebar (hidden), full-width content
- **Grid layouts**: Responsive 1-column (mobile) to 5-column (desktop)

---

## 15. STATE MANAGEMENT

### Application State Variables
```javascript
const state = {
  user: null,           // Netlify Identity user object
  profile: null,        // User profile data { name, age, plan, ... }
  chart: null          // Chart.js instance for weight chart
}
```

### Authentication State
- Managed via Netlify Identity widget
- Events: `init`, `login`, `logout`
- User data updated on these events

---

## 16. ADDITIONAL FEATURES

### Version Display
- Fetches API version from `/version` endpoint
- Displays in header as "v[version]"

### Error Handling
- API errors displayed in status messages
- User-friendly error messages
- Console logging for debugging

### Loading States
- Chart displays loading spinner while fetching data
- Form submissions provide feedback

### Responsive Design
- Mobile: Single column, collapsible sidebar
- Desktop: Multi-column grid layouts
- Smooth transitions on all interactive elements

---

## 17. MISSING/NOT IMPLEMENTED IN ORIGINAL

- **Workout plan scheduling**: No calendar or plan view
- **Meal planning**: No meal plan templates or suggestions
- **Goal setting UI**: Goals are counted but no form to create them
- **Progress analytics**: Only weight tracking, no other metrics
- **Achievement badges**: Mentioned streak but no visual representation
- **Social features**: No sharing or comparison
- **Advanced settings**: Minimal configuration options
- **Data export**: No download/export functionality

---

## Summary Statistics

- **Total Tabs**: 5
- **Total Forms**: 3
- **Total API Endpoints**: 7
- **Total KPI Cards**: 5
- **Total User Input Fields**: 6 (name, age, food, workout, discord_id, + implicit fields)
- **Charts**: 1 (weight progress)

