#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate premium FitAI dashboard HTML"""

html = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FitAI — Premium Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <style>
    body {
      font-family: 'DM Sans', sans-serif;
      background: radial-gradient(circle at 85% -5%, rgba(0, 229, 255, 0.08), transparent 35%),
                  radial-gradient(circle at 10% 120%, rgba(124, 58, 237, 0.06), transparent 35%),
                  #0a0b0f;
      color: #f0f2f8;
    }
    .glass {
      background: rgba(15, 17, 23, 0.5);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(0, 229, 255, 0.15);
      transition: all 0.3s ease;
    }
    .glass:hover {
      background: rgba(15, 17, 23, 0.6);
      border-color: rgba(0, 229, 255, 0.3);
    }
    .neon-glow:hover {
      box-shadow: 0 0 24px rgba(0, 229, 255, 0.4);
      border-color: rgba(0, 229, 255, 0.6);
    }
    button, a, input, select, textarea {
      transition: all 0.2s ease;
    }
    ::-webkit-scrollbar {
      width: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #0f1117;
    }
    ::-webkit-scrollbar-thumb {
      background: rgba(0, 229, 255, 0.3);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: rgba(0, 229, 255, 0.6);
    }
  </style>
</head>
<body class="bg-slate-950 text-gray-100">
  <div class="flex h-screen bg-slate-950 overflow-hidden">
    <!-- Sidebar -->
    <aside class="hidden md:flex w-20 bg-slate-900 border-r border-cyan-400/10 flex-col items-center py-6 space-y-8">
      <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-cyan-400 to-violet-500 flex items-center justify-center font-bold text-slate-900 text-lg">F</div>
      <nav class="flex flex-col space-y-6">
        <button class="nav-icon opacity-70 hover:opacity-100 transition" data-tab="dashboard" title="Dashboard"><span class="text-2xl">📊</span></button>
        <button class="nav-icon opacity-70 hover:opacity-100 transition" data-tab="panel" title="Panel"><span class="text-2xl">⚙️</span></button>
        <button class="nav-icon opacity-70 hover:opacity-100 transition" data-tab="checkin" title="Check-in"><span class="text-2xl">✅</span></button>
        <button class="nav-icon opacity-70 hover:opacity-100 transition" data-tab="integrations" title="Integracje"><span class="text-2xl">🔗</span></button>
        <button class="nav-icon opacity-70 hover:opacity-100 transition" data-tab="billing" title="Płatności"><span class="text-2xl">💳</span></button>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="glass border-b border-cyan-400/10 px-6 py-4 md:py-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl md:text-3xl font-bold"><span class="text-cyan-400">FitAI</span> Dashboard</h1>
          <p id="status" class="text-gray-500 text-sm mt-1">Sprawdzam logowanie...</p>
        </div>
        <div class="flex items-center gap-4">
          <div id="version" class="text-xs text-gray-500 px-3 py-1 rounded-full bg-slate-900/50">v--</div>
          <div class="hidden md:flex gap-2">
            <button id="loginBtn" class="px-4 py-2 rounded-lg border border-cyan-400/30 text-cyan-400 hover:bg-cyan-400/10 text-sm font-medium">Zaloguj</button>
            <button id="signupBtn" class="px-4 py-2 rounded-lg border border-cyan-400/30 text-cyan-400 hover:bg-cyan-400/10 text-sm font-medium">Rejestracja</button>
            <button id="logoutBtn" class="hidden px-4 py-2 rounded-lg border border-cyan-400/30 text-cyan-400 hover:bg-cyan-400/10 text-sm font-medium">Wyloguj</button>
          </div>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto">
        <div class="p-4 md:p-8">
          <!-- Locked State -->
          <div id="appLocked">
            <div class="glass neon-glow rounded-2xl p-8 md:p-12 border border-cyan-400/20 max-w-2xl mx-auto text-center mt-12">
              <div class="text-6xl mb-6">🔒</div>
              <h2 class="text-3xl font-bold mb-3">Panel jest chroniony</h2>
              <p class="text-gray-500 text-lg">Zaloguj się przez Netlify Identity, aby uzyskać dostęp do pełnego dashboardu.</p>
              <div class="flex gap-4 justify-center mt-8">
                <button id="loginModal" class="px-6 py-3 rounded-lg bg-cyan-400 text-slate-900 font-semibold hover:brightness-110">Zaloguj się</button>
                <button id="signupModal" class="px-6 py-3 rounded-lg border border-cyan-400/50 text-cyan-400 hover:bg-cyan-400/10 font-semibold">Utwórz konto</button>
              </div>
            </div>
          </div>

          <!-- Unlocked State -->
          <div id="appUnlocked" class="hidden space-y-6">
            <!-- Dashboard Tab -->
            <section id="dashboard-tab" class="tab-content">
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
                <div class="glass neon-glow rounded-xl p-5 border border-cyan-400/10">
                  <p class="text-gray-500 text-xs uppercase tracking-wide font-semibold">Plan</p>
                  <p class="text-2xl font-bold text-cyan-400 mt-2" id="kpiPlan">free</p>
                </div>
                <div class="glass neon-glow rounded-xl p-5 border border-cyan-400/10">
                  <p class="text-gray-500 text-xs uppercase tracking-wide font-semibold">Rola</p>
                  <p class="text-2xl font-bold text-cyan-400 mt-2" id="kpiRole">free_user</p>
                </div>
                <div class="glass neon-glow rounded-xl p-5 border border-cyan-400/10">
                  <p class="text-gray-500 text-xs uppercase tracking-wide font-semibold">Streak</p>
                  <p class="text-2xl font-bold text-cyan-400 mt-2" id="kpiStreak">0</p>
                </div>
                <div class="glass neon-glow rounded-xl p-5 border border-cyan-400/10">
                  <p class="text-gray-500 text-xs uppercase tracking-wide font-semibold">Konsystencja</p>
                  <p class="text-2xl font-bold text-cyan-400 mt-2" id="kpiConsistency">0%</p>
                </div>
                <div class="glass neon-glow rounded-xl p-5 border border-cyan-400/10">
                  <p class="text-gray-500 text-xs uppercase tracking-wide font-semibold">Cele</p>
                  <p class="text-xl font-bold text-cyan-400 mt-2" id="kpiTargets">-</p>
                </div>
              </div>
              <div class="glass rounded-2xl p-8 border border-cyan-400/10">
                <h3 class="text-xl font-bold mb-6">Postęp Wagi</h3>
                <div class="h-80"><canvas id="weightChart"></canvas></div>
              </div>
            </section>

            <!-- Panel Tab -->
            <section id="panel-tab" class="tab-content hidden">
              <div class="glass rounded-2xl p-8 border border-cyan-400/10">
                <h3 class="text-2xl font-bold mb-6">Profil Użytkownika</h3>
                <form id="profileForm" class="space-y-6">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <label class="block">
                      <span class="text-sm font-semibold text-cyan-400 mb-2 block">Imię</span>
                      <input type="text" name="name" class="w-full px-4 py-3 rounded-lg glass border border-cyan-400/20 bg-slate-900/30" required>
                    </label>
                    <label class="block">
                      <span class="text-sm font-semibold text-cyan-400 mb-2 block">Wiek</span>
                      <input type="number" name="age" min="12" max="99" class="w-full px-4 py-3 rounded-lg glass border border-cyan-400/20 bg-slate-900/30" required>
                    </label>
                  </div>
                  <button type="submit" class="w-full px-6 py-3 rounded-lg bg-cyan-400 text-slate-900 font-bold hover:brightness-110">Zapisz Profil</button>
                </form>
              </div>
            </section>

            <!-- Check-in Tab -->
            <section id="checkin-tab" class="tab-content hidden">
              <div class="glass rounded-2xl p-8 border border-cyan-400/10 max-w-2xl">
                <h3 class="text-2xl font-bold mb-6">✅ Daily Check-in</h3>
                <form id="checkinForm" class="space-y-6">
                  <label class="block">
                    <span class="text-sm font-semibold text-cyan-400 mb-2 block">Dzisiejsze posiłki</span>
                    <textarea name="food" placeholder="np. owsianka, kurczak z ryżem" class="w-full px-4 py-3 rounded-lg glass border border-cyan-400/20 bg-slate-900/30 min-h-20"></textarea>
                  </label>
                  <label class="block">
                    <span class="text-sm font-semibold text-cyan-400 mb-2 block">Trening</span>
                    <textarea name="workout" placeholder="np. push day, 45 min" class="w-full px-4 py-3 rounded-lg glass border border-cyan-400/20 bg-slate-900/30 min-h-20"></textarea>
                  </label>
                  <button type="submit" class="w-full px-6 py-3 rounded-lg bg-cyan-400 text-slate-900 font-bold hover:brightness-110">Wyślij Check-in</button>
                </form>
              </div>
            </section>

            <!-- Integrations Tab -->
            <section id="integrations-tab" class="tab-content hidden">
              <div class="glass rounded-2xl p-8 border border-cyan-400/10">
                <h3 class="text-2xl font-bold mb-6">🔗 Integracje</h3>
                <form id="discordForm" class="space-y-4">
                  <input type="text" name="discord_id" placeholder="Discord User ID" class="w-full px-4 py-3 rounded-lg glass border border-cyan-400/20 bg-slate-900/30">
                  <button type="submit" class="w-full px-6 py-3 rounded-lg bg-cyan-400 text-slate-900 font-bold">Połącz Discord</button>
                </form>
              </div>
            </section>

            <!-- Billing Tab -->
            <section id="billing-tab" class="tab-content hidden">
              <div class="glass rounded-2xl p-8 border border-cyan-400/10 max-w-2xl">
                <h3 class="text-2xl font-bold mb-6">💳 Plan Płatności</h3>
                <p class="text-gray-500 mb-6">Aktualny plan: <strong class="text-cyan-400" id="planBadge">free</strong></p>
                <button id="buyProBtn" class="px-6 py-3 rounded-lg bg-cyan-400 text-slate-900 font-bold hover:brightness-110">Kup Pro (Stripe)</button>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script src="https://identity.netlify.com/v1/netlify-identity-widget.js"></script>
  <script>
    const state = { user: null };
    const appLocked = document.getElementById('appLocked');
    const appUnlocked = document.getElementById('appUnlocked');

    function showUnlocked(unlocked) {
      appLocked.classList.toggle('hidden', unlocked);
      appUnlocked.classList.toggle('hidden', !unlocked);
      document.getElementById('loginBtn').classList.toggle('hidden', unlocked);
      document.getElementById('signupBtn').classList.toggle('hidden', unlocked);
      document.getElementById('logoutBtn').classList.toggle('hidden', !unlocked);
    }

    // Setup tab navigation
    document.querySelectorAll('.nav-icon').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll('.nav-icon').forEach(b => b.classList.remove('opacity-100'));
        btn.classList.add('opacity-100');
        document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
        const tabEl = document.getElementById(`${tab}-tab`);
        if (tabEl) tabEl.classList.remove('hidden');
      });
    });

    // Auth handlers
    document.getElementById('loginBtn').addEventListener('click', () => window.netlifyIdentity?.open('login'));
    document.getElementById('signupBtn').addEventListener('click', () => window.netlifyIdentity?.open('signup'));
    document.getElementById('logoutBtn').addEventListener('click', () => window.netlifyIdentity?.logout());
    document.getElementById('loginModal').addEventListener('click', () => window.netlifyIdentity?.open('login'));
    document.getElementById('signupModal').addEventListener('click', () => window.netlifyIdentity?.open('signup'));

    if (window.netlifyIdentity) {
      window.netlifyIdentity.on('init', (user) => {
        state.user = user;
        showUnlocked(Boolean(user));
        document.getElementById('status').textContent = user ? `Zalogowano: ${user.email}` : 'Niezalogowany';
      });
      window.netlifyIdentity.on('login', (user) => {
        state.user = user;
        showUnlocked(true);
        window.netlifyIdentity.close();
        document.getElementById('status').textContent = `Zalogowano: ${user.email}`;
      });
      window.netlifyIdentity.on('logout', () => {
        state.user = null;
        showUnlocked(false);
        document.getElementById('status').textContent = 'Niezalogowany';
      });
      window.netlifyIdentity.init();
    }
  </script>
</body>
</html>"""

with open(r"c:\\Users\\adamz\\OneDrive\\Desktop\\Projects\\Training coach\\app\\index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Panel dashboard successfully created with Premium SaaS design!")
print("📊 Features: Dark mode, Glassmorphism, Tailwind CSS, Responsive, Neon effects")
