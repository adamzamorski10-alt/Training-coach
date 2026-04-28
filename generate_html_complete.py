#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ulepszony generator dashboardu FitAI - Nowoczesny wygląd bez tabel"""

html_content = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FitAI — Premium Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --neon-cyan: #00e5ff;
      --deep-bg: #0a0b10;
      --card-bg: rgba(255, 255, 255, 0.03);
    }
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--deep-bg);
      background-image: 
        radial-gradient(circle at 0% 0%, rgba(0, 229, 255, 0.05) 0%, transparent 50%),
        radial-gradient(circle at 100% 100%, rgba(124, 58, 237, 0.05) 0%, transparent 50%);
      color: #e2e8f0;
      min-height: 100vh;
    }
    .glass-card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 24px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
      border-color: rgba(0, 229, 255, 0.3);
      box-shadow: 0 0 30px rgba(0, 229, 255, 0.05);
    }
    .nav-item {
      transition: all 0.2s ease;
      border-radius: 12px;
    }
    .nav-item.active {
      background: rgba(0, 229, 255, 0.1);
      color: var(--neon-cyan);
      border-left: 4px solid var(--neon-cyan);
    }
    .btn-neon {
      background: var(--neon-cyan);
      color: #000;
      font-weight: 700;
      box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
      transition: all 0.3s ease;
    }
    .btn-neon:hover {
      box-shadow: 0 0 25px rgba(0, 229, 255, 0.5);
      transform: translateY(-2px);
    }
    /* Ukrywanie scrollbara */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
  </style>
</head>
<body class="overflow-x-hidden">

  <aside class="fixed left-0 top-0 h-full w-64 glass-card rounded-none border-y-0 border-l-0 p-6 z-50 hidden md:block">
    <div class="mb-10 flex items-center gap-3">
      <div class="w-8 h-8 bg-[#00e5ff] rounded-lg rotate-12 flex items-center justify-center font-bold text-black italic">F</div>
      <h1 class="text-2xl font-bold tracking-tight text-white font-['Syne']">FitAI</h1>
    </div>
    
    <nav class="space-y-2">
      <a href="#" onclick="showTab('dashboard')" class="nav-item active flex items-center gap-3 p-3 text-sm font-medium">
        <span>📊</span> Dashboard
      </a>
      <a href="#" onclick="showTab('checkin')" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span>✅</span> Raport Dzienny
      </a>
      <a href="#" onclick="showTab('plan')" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span>💪</span> Plan Treningowy
      </a>
      <a href="#" onclick="showTab('profile')" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span>👤</span> Profil
      </a>
    </nav>
  </aside>

  <main class="md:ml-64 p-4 md:p-8">
    
    <header class="flex justify-between items-center mb-10">
      <div>
        <h2 class="text-3xl font-bold text-white mb-1">Cześć, Formo! 👋</h2>
        <p class="text-gray-400 text-sm">Twój dzisiejszy postęp jest widoczny poniżej.</p>
      </div>
      <div class="flex items-center gap-4">
        <span id="version" class="text-xs font-mono text-gray-600 bg-white/5 px-2 py-1 rounded">v1.2</span>
        <button id="logoutBtn" class="p-2 bg-white/5 hover:bg-red-500/20 rounded-full transition-colors">🚪</button>
      </div>
    </header>

    <section id="dashboard" class="tab-content space-y-8">
      
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
        <div class="glass-card p-6">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">🔥 Streak</p>
          <h3 id="kpiStreak" class="text-3xl font-bold text-white">0 dni</h3>
        </div>
        <div class="glass-card p-6">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">⚖️ Waga</p>
          <h3 id="kpiWeight" class="text-3xl font-bold text-white">-- kg</h3>
        </div>
        <div class="glass-card p-6 border-l-4 border-cyan-500">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">📈 Spójność</p>
          <h3 id="kpiConsistency" class="text-3xl font-bold text-[#00e5ff]">0%</h3>
        </div>
        <div class="glass-card p-6">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">⭐ Plan</p>
          <h3 id="kpiPlan" class="text-3xl font-bold text-white">Free</h3>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 glass-card p-6">
          <h4 class="text-lg font-bold text-white mb-6">Analiza Wagi</h4>
          <div class="h-64">
            <canvas id="weightChart"></canvas>
          </div>
        </div>

        <div class="lg:col-span-1 space-y-4">
          <h4 class="text-lg font-bold text-white mb-2">Ostatnia Aktywność</h4>
          <div id="historyCards" class="space-y-4 overflow-y-auto max-h-[500px] pr-2">
            <div class="glass-card p-4 text-center text-gray-500 text-sm italic">
              Brak logów do wyświetlenia
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="checkin" class="tab-content hidden glass-card p-8">
       <h3 class="text-2xl font-bold mb-6">Raport Dzienny</h3>
       <form id="checkInForm" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div>
               <label class="block text-sm font-medium text-gray-400 mb-2">Co dzisiaj jadłeś?</label>
               <textarea class="w-full bg-slate-900/80 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-[#00e5ff]" rows="3" placeholder="np. Owsianka, kurczak z ryżem..."></textarea>
             </div>
             <div>
               <label class="block text-sm font-medium text-gray-400 mb-2">Trening / Ruch</label>
               <textarea class="w-full bg-slate-900/80 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-[#00e5ff]" rows="3" placeholder="np. 45 min siłownia..."></textarea>
             </div>
          </div>
          <button type="submit" class="btn-neon px-8 py-3 rounded-xl w-full md:w-auto">Zapisz Raport</button>
       </form>
    </section>

  </main>

  <script>
    // Logika przełączania zakładek
    function showTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      
      document.getElementById(tabId).classList.remove('hidden');
      event.currentTarget.classList.add('active');
    }

    // Generator kart zamiast wierszy tabeli
    function renderHistory(logs) {
      const container = document.getElementById('historyCards');
      if (!logs || logs.length === 0) return;
      
      container.innerHTML = logs.map(log => `
        <div class="glass-card p-4 hover:border-cyan-500/50 cursor-pointer">
          <div class="flex justify-between items-start mb-2">
            <span class="text-xs font-bold text-cyan-400">${log.date}</span>
            <span class="text-xs bg-white/5 px-2 py-1 rounded">Mood: ${log.mood || 'ok'}</span>
          </div>
          <p class="text-sm text-white font-medium line-clamp-1">${log.workout || 'Brak treningu'}</p>
          <p class="text-xs text-gray-500 mt-1">${log.food || 'Brak info o jedzeniu'}</p>
          <div class="mt-3 flex items-center justify-between">
            <span class="text-xs text-gray-400">${log.weight} kg</span>
            <span class="text-[10px] text-gray-600">Kliknij by rozwinąć</span>
          </div>
        </div>
      `).join('');
    }

    // Przykład inicjalizacji wykresu z neonowym motywem
    function initChart() {
      const ctx = document.getElementById('weightChart').getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Niedz'],
          datasets: [{
            label: 'Waga (kg)',
            data: [85, 84.8, 84.5, 84.6, 84.2, 84, 83.8],
            borderColor: '#00e5ff',
            backgroundColor: 'rgba(0, 229, 255, 0.1)',
            fill: true,
            tension: 0.4,
            borderWidth: 3,
            pointRadius: 5,
            pointBackgroundColor: '#00e5ff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
            x: { grid: { display: false }, ticks: { color: '#64748b' } }
          }
        }
      });
    }

    // Start
    window.onload = () => {
      initChart();
      // Symulacja danych historycznych
      renderHistory([
        {date: '2026-04-24', workout: 'Siłownia: Klatka + Triceps', food: 'Owsianka, Ryż z kurczakiem', weight: 84.5, mood: '🔥'},
        {date: '2026-04-23', workout: 'Bieganie 5km', food: 'Sałatka, Ryba', weight: 84.8, mood: '😴'}
      ]);
    };
  </script>
</body>
</html>"""

# Zapisanie do pliku
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ Zaktualizowany panel (bez tabel) został wygenerowany jako index.html")