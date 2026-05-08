#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FitAI SaaS Platform - Premium Dashboard Generator
Nowoczesny system dla wielu użytkowników z Glassmorphism UI, animacjami i offline support
FitAI SaaS Platform v3.0 - Premium Dashboard Generator
Integracja z FastAPI backendem: sport drille, Carb Cycling, autoregulacja.
"""

html_content = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#0a0b10">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <title>FitAI — Premium SaaS Platform</title>
  
  <!-- Tailwind & Fonts -->

  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  
  <!-- Chart.js for KPI visualization -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  
  <!-- PWA Manifest -->
  <link rel="manifest" href="data:application/manifest+json,%7B%22name%22:%22FitAI%22,%22short_name%22:%22FitAI%22,%22start_url%22:%22/%22,%22display%22:%22standalone%22,%22background_color%22:%22%230a0b10%22,%22theme_color%22:%22%2300e5ff%22%7D">
  

  <style>
    * { box-sizing: border-box; }
    
    :root {
      --neon-cyan: #00e5ff;
      --neon-purple: #7c3aed;
      --deep-bg: #0a0b10;
      --card-bg: rgba(255, 255, 255, 0.03);
      --alert-red: #ff4444;
      --cyan:#00e5ff;--violet:#7c3aed;--bg:#0a0b10;
      --card:rgba(255,255,255,0.03);--border:rgba(255,255,255,0.08);
      --border-cyan:rgba(0,229,255,0.25);--text:#e2e8f0;--muted:#64748b;
    }
    
    html { scroll-behavior: smooth; }
    
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--deep-bg);
      background-image: 
        radial-gradient(circle at 0% 0%, rgba(0, 229, 255, 0.05) 0%, transparent 50%),
        radial-gradient(circle at 100% 100%, rgba(124, 58, 237, 0.05) 0%, transparent 50%);
      color: #e2e8f0;
      background: var(--bg);
      background-image: radial-gradient(circle at 0% 0%,rgba(0,229,255,0.05) 0%,transparent 50%),radial-gradient(circle at 100% 100%,rgba(124,58,237,0.05) 0%,transparent 50%);
      color: var(--text);
      min-height: 100vh;
    }
    .glass {background:var(--card);backdrop-filter:blur(12px);border:1px solid var(--border);border-radius:16px;transition:border-color 0.3s,box-shadow 0.3s;}
    .glass:hover {border-color:var(--border-cyan);box-shadow:0 0 30px rgba(0,229,255,0.05);}
    .progress-bar{height:6px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;}
    .progress-fill{height:100%;border-radius:3px;transition:width 0.8s cubic-bezier(0.4,0,0.2,1);}
    .check-circle{width:22px;height:22px;border-radius:50%;border:2px solid var(--border-cyan);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 0.2s;flex-shrink:0;}
    .check-circle.checked{background:var(--cyan);border-color:var(--cyan);}
    .check-circle.checked::after{content:'✓';color:#000;font-size:12px;font-weight:bold;}
    .progress-ring-circle{transition:stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1);transform:rotate(-90deg);transform-origin:50% 50%;}
    .nav-item.active{background:rgba(0,229,255,0.1);color:var(--cyan);border-left:3px solid var(--cyan);padding-left:calc(0.75rem - 3px);}
    
    /* === GLASSMORPHISM === */
    .glass-card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    /* Sport session card – neon orange accent */
    .sport-card {
      background: linear-gradient(135deg, rgba(255,107,53,0.08), rgba(124,58,237,0.08));
      border: 1px solid rgba(255,107,53,0.35);
    }
    
    .glass-card:hover {
      border-color: rgba(0, 229, 255, 0.3);
      box-shadow: 0 0 30px rgba(0, 229, 255, 0.05);
      transform: translateY(-1px);
    }
    
    .sport-card:hover { border-color: rgba(255,107,53,0.6); }
    .glass-sidebar {
      background: rgba(10, 11, 16, 0.7);
      background: rgba(10,11,16,0.7);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255,255,255,0.08);
    }
    
    /* === ANIMATIONS === */
    @keyframes slideUpFade {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
      from { opacity:0; transform:translateY(20px); }
      to   { opacity:1; transform:translateY(0); }
    }
    
    @keyframes fadeOutFast {
      from { opacity: 1; }
      to { opacity: 0; }
    }
    
    @keyframes fadeOutFast { from{opacity:1} to{opacity:0} }
    @keyframes springBounce {
      0%, 100% { transform: translateX(0); }
      25% { transform: translateX(-8px); }
      75% { transform: translateX(8px); }
      0%,100%{transform:translateX(0)} 25%{transform:translateX(-8px)} 75%{transform:translateX(8px)}
    }
    
    @keyframes pulseNeon {
      0%, 100% {
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.3),
                    inset 0 0 15px rgba(0, 229, 255, 0.1);
      }
      50% {
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.6),
                    inset 0 0 20px rgba(0, 229, 255, 0.2);
      }
      0%,100%{ box-shadow:0 0 15px rgba(0,229,255,.3),inset 0 0 15px rgba(0,229,255,.1); }
      50%    { box-shadow:0 0 30px rgba(0,229,255,.6),inset 0 0 20px rgba(0,229,255,.2); }
    }
    
    @keyframes slideRightToLeft {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    @keyframes pulseOrange {
      0%,100%{ box-shadow:0 0 15px rgba(255,107,53,.4); }
      50%    { box-shadow:0 0 30px rgba(255,107,53,.8); }
    }
    
    @keyframes slideLeftToRight {
      from { transform: translateX(-100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    
    .tab-content {
      animation: slideUpFade 0.4s ease-out;
    }
    
    .tab-content.exit {
      animation: fadeOutFast 0.2s ease-out;
    }
    
    .day-carousel-item {
      animation: springBounce 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    
    .tab-content { animation:slideUpFade 0.4s ease-out; }
    .day-carousel-item { animation:springBounce 0.6s cubic-bezier(0.34,1.56,0.64,1); }
    .btn-neon {
      background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
      color: #fff;
      font-weight: 600;
      box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
      transition: all 0.3s ease;
      border: none;
      cursor: pointer;
      background:linear-gradient(135deg,var(--cyan),var(--violet));
      color:#fff; font-weight:600;
      box-shadow:0 0 15px rgba(0,229,255,.3);
      transition:all .3s ease; border:none; cursor:pointer;
    }
    
    .btn-neon:hover {
      box-shadow: 0 0 25px rgba(0, 229, 255, 0.5), 0 0 40px rgba(124, 58, 237, 0.3);
      transform: translateY(-2px);
    .btn-neon:hover { box-shadow:0 0 25px rgba(0,229,255,.5),0 0 40px rgba(124,58,237,.3); transform:translateY(-2px); }
    .btn-sport {
      background:linear-gradient(135deg,#ff6b35,var(--violet));
      color:#fff; font-weight:600;
      box-shadow:0 0 15px rgba(255,107,53,.3);
      transition:all .3s ease; border:none; cursor:pointer;
      animation:pulseOrange 2s infinite;
    }
    
    .btn-neon.pulse {
      animation: pulseNeon 2s infinite;
    }
    
    .btn-sport:hover { box-shadow:0 0 30px rgba(255,107,53,.6); transform:translateY(-2px); }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #e2e8f0;
      transition: all 0.2s ease;
      cursor: pointer;
      background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
      color:#e2e8f0; transition:all .2s ease; cursor:pointer;
    }
    
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }
    
    /* === NAVIGATION === */
    .nav-item {
      transition: all 0.2s ease;
      border-radius: 12px;
      cursor: pointer;
    }
    
    .nav-item.active {
      background: rgba(0, 229, 255, 0.1);
      color: var(--neon-cyan);
      border-left: 4px solid var(--neon-cyan);
      padding-left: calc(0.75rem - 4px);
    }
    
    .nav-item:hover:not(.active) {
      background: rgba(255, 255, 255, 0.05);
      color: #e2e8f0;
    }
    
    /* === ALERTS & NOTIFICATIONS === */
    .btn-secondary:hover { background:rgba(255,255,255,0.1); border-color:rgba(255,255,255,0.2); }
    .nav-item { transition:all .2s ease; border-radius:12px; cursor:pointer; }
    .alert-neon {
      background: linear-gradient(135deg, rgba(0, 229, 255, 0.1), rgba(124, 58, 237, 0.1));
      border: 1px solid rgba(0, 229, 255, 0.3);
      border-radius: 12px;
      padding: 12px 16px;
      animation: slideUpFade 0.4s ease-out;
      background:linear-gradient(135deg,rgba(0,229,255,0.1),rgba(124,58,237,0.1));
      border:1px solid rgba(0,229,255,0.3); border-radius:12px;
      padding:12px 16px; animation:slideUpFade .4s ease-out;
    }
    
    .alert-warning {
      background: rgba(255, 68, 68, 0.1);
      border: 1px solid rgba(255, 68, 68, 0.3);
      color: #ff9999;
    }
    
    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { 
      background: rgba(0, 229, 255, 0.2);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: rgba(0, 229, 255, 0.4);
    }
    
    /* === INPUTS & FORMS === */
    .alert-warning { background:rgba(255,68,68,0.1); border:1px solid rgba(255,68,68,0.3); color:#ff9999; }
    ::-webkit-scrollbar { width:8px; height:8px; }
    ::-webkit-scrollbar-track { background:transparent; }
    ::-webkit-scrollbar-thumb { background:rgba(0,229,255,0.2); border-radius:4px; }
    ::-webkit-scrollbar-thumb:hover { background:rgba(0,229,255,0.4); }
    input, textarea, select {
      background: rgba(0, 0, 0, 0.3) !important;
      border: 1px solid rgba(255, 255, 255, 0.1) !important;
      color: #e2e8f0 !important;
      border-radius: 8px !important;
      padding: 10px 12px !important;
      transition: all 0.2s ease !important;
      background:rgba(0,0,0,0.3) !important; border:1px solid var(--border) !important;
      color:#e2e8f0 !important; border-radius:8px !important;
      padding:10px 12px !important; transition:all .2s ease !important;
    }
    
    input:focus, textarea:focus, select:focus {
      outline: none !important;
      border-color: var(--neon-cyan) !important;
      box-shadow: 0 0 15px rgba(0, 229, 255, 0.2) !important;
    input:focus, textarea:focus, select:focus { outline:none !important; border-color:var(--cyan) !important; box-shadow:0 0 15px rgba(0,229,255,0.2) !important; }
    @media(max-width:768px) {
      .glass-sidebar { position:fixed; left:-100%; top:0; width:100%; height:100%; z-index:999; transition:left .3s ease; }
      .glass-sidebar.mobile-open { left:0; }
    }
    
    /* === RESPONSIVE === */
    @media (max-width: 768px) {
      .glass-sidebar {
        position: fixed;
        left: -100%;
        top: 0;
        width: 100%;
        height: 100%;
        z-index: 999;
        transition: left 0.3s ease;
      }
      
      .glass-sidebar.mobile-open {
        left: 0;
      }
    }
    
    /* === UTILITY CLASSES === */
    .text-gradient {
      background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      background:linear-gradient(135deg,var(--cyan),var(--violet));
      -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
    }
    
    .shimmer {
      animation: shimmer 2s infinite;
    .sport-badge {
      display:inline-flex; align-items:center; gap:4px;
      background:rgba(255,107,53,0.15); border:1px solid rgba(255,107,53,0.4);
      color:#ff9d78; border-radius:8px; padding:2px 10px; font-size:11px; font-weight:600;
    }
    
    @keyframes shimmer {
      0% { opacity: 0.5; }
      50% { opacity: 1; }
      100% { opacity: 0.5; }
    .loading-spinner {
      width:32px; height:32px;
      border:3px solid rgba(0,229,255,0.2);
      border-top-color:var(--cyan);
      border-radius:50%; animation:spin .8s linear infinite;
    }
    @keyframes spin { to { transform:rotate(360deg); } }
  </style>
</head>
<body>

<!-- ======== NAVBAR ======== -->
<nav class="fixed top-0 left-0 right-0 bg-gradient-to-b from-[#0a0b10] via-[rgba(10,11,16,0.8)] to-transparent backdrop-blur-xl border-b border-white/5 z-40 px-4 md:px-8 py-4">
  <div class="max-w-7xl mx-auto flex justify-between items-center">
    <!-- Logo -->
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 bg-gradient-to-br from-[#00e5ff] to-[#7c3aed] rounded-lg rotate-12 flex items-center justify-center font-bold text-white text-lg">F</div>
      <h1 class="text-xl font-bold tracking-tight text-white hidden sm:block">FitAI</h1>
    </div>
    
    <!-- Right Menu -->
    <div class="flex items-center gap-4">
      <!-- User Switcher (Dropdown) -->
      <div class="relative group">
        <button id="userMenuBtn" class="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors text-sm font-medium">
          <span id="currentUserDisplay">👤 Użytkownik</span>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
          </svg>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
        </button>
        <div id="userDropdown" class="absolute right-0 mt-2 w-48 bg-gradient-to-b from-white/10 to-white/5 backdrop-blur-xl border border-white/10 rounded-lg shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 p-2">
          <div id="userList" class="space-y-1 max-h-64 overflow-y-auto"></div>
          <div class="border-t border-white/10 mt-2 pt-2">
            <button onclick="showTab('profile')" class="w-full text-left px-3 py-2 text-sm text-gray-400 hover:bg-white/5 rounded transition-colors">⚙️ Ustawienia</button>
            <button id="addUserBtn" class="w-full text-left px-3 py-2 text-sm text-cyan-400 hover:bg-cyan-500/10 rounded transition-colors">+ Dodaj użytkownika</button>
          </div>
        </div>
      </div>
      
      <!-- Main PANEL Button (Pulsing Neon) -->
      <button onclick="showTab('dashboard')" class="btn-neon pulse px-6 py-2 rounded-lg font-bold text-sm">PANEL</button>
      
      <!-- Mobile Menu Toggle -->
      <button id="mobileMenuBtn" class="md:hidden p-2 hover:bg-white/10 rounded-lg transition-colors">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
        </svg>
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
      </button>
    </div>
  </div>
</nav>

<!-- ======== LAYOUT CONTAINER ======== -->
<div class="flex pt-16 min-h-screen">

  <!-- ======== SIDEBAR (GLASSMORPHISM) ======== -->
  <!-- ======== SIDEBAR ======== -->
  <aside id="sidebar" class="hidden md:flex w-64 glass-sidebar p-6 border-r border-white/5 fixed md:sticky top-16 h-[calc(100vh-64px)] flex-col gap-6 overflow-y-auto md:z-0 z-50">
    <nav class="space-y-2 flex-1">
      <div class="px-3 py-2 text-xs font-bold text-gray-500 uppercase tracking-wide">Menu</div>
      
      <a href="#" onclick="showTab('dashboard'); return false;" class="nav-item active flex items-center gap-3 p-3 text-sm font-medium">
        <span class="text-lg">🏠</span> <span>Home</span>
      </a>
      
      <a href="#" onclick="showTab('my-day'); return false;" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span class="text-lg">📋</span> <span>Mój Dzień</span>
      </a>
      
      <a href="#" onclick="showTab('plan'); return false;" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span class="text-lg">📅</span> <span>Plan</span>
      </a>
      
      <a href="#" onclick="showTab('profile'); return false;" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span class="text-lg">👤</span> <span>Profil</span>
      </a>
      
      <a href="#" onclick="showTab('contact'); return false;" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white">
        <span class="text-lg">💬</span> <span>Kontakt</span>
      </a>
      <a href="#" onclick="showTab('dashboard'); return false;" data-tab="dashboard" class="nav-item active flex items-center gap-3 p-3 text-sm font-medium"><span class="text-lg">🏠</span><span>Home</span></a>
      <a href="#" onclick="showTab('my-day'); return false;" data-tab="my-day" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white"><span class="text-lg">📋</span><span>Mój Dzień</span></a>
      <a href="#" onclick="showTab('plan'); return false;" data-tab="plan" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white"><span class="text-lg">📅</span><span>Plan</span></a>
      <a href="#" onclick="showTab('profile'); return false;" data-tab="profile" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white"><span class="text-lg">👤</span><span>Profil</span></a>
      <a href="#" onclick="showTab('contact'); return false;" data-tab="contact" class="nav-item flex items-center gap-3 p-3 text-sm font-medium text-gray-400 hover:text-white"><span class="text-lg">💬</span><span>Kontakt</span></a>
    </nav>
    
    <!-- Footer Info -->
    <div class="glass rounded-2xl p-4">
      <p class="text-xs font-bold text-gray-500 uppercase mb-3">Twój Fundament</p>
      <div class="space-y-2 text-xs">
        <div class="flex justify-between"><span class="text-gray-500">Kalorie/dzień</span><span class="text-cyan-400 font-bold" id="sidebarCalories">—</span></div>
        <div class="flex justify-between"><span class="text-gray-500">Białko</span><span class="text-violet-400 font-bold" id="sidebarProtein">—</span></div>
        <div class="flex justify-between"><span class="text-gray-500">Waga cel</span><span class="text-yellow-400 font-bold" id="sidebarTarget">—</span></div>
      </div>
    </div>
    <div class="border-t border-white/5 pt-4">
      <div class="text-xs text-gray-500 space-y-1">
        <p>📊 <span id="versionInfo">FitAI v2.0</span></p>
        <p>📊 <span id="versionInfo">FitAI v3.0</span></p>
        <button id="logoutBtn" class="text-red-400 hover:text-red-300 text-xs font-medium transition-colors w-full text-left">🚪 Wyloguj</button>
      </div>
    </div>
  </aside>

  <!-- ======== MAIN CONTENT ======== -->
  <main class="flex-1 p-4 md:p-8 w-full">
    <!-- Header with User Greeting -->
    <header class="mb-8 animate-fadeIn">
    <header class="mb-8">
      <div class="flex justify-between items-start md:items-center">
        <div>
          <h2 class="text-3xl md:text-4xl font-bold text-white mb-1">
            👋 Witaj, <span id="greetingName">Użytkowniku</span>!
          </h2>
          <h2 class="text-3xl md:text-4xl font-bold text-white mb-1">👋 Witaj, <span id="greetingName">Użytkowniku</span>!</h2>
          <p class="text-gray-400 text-sm md:text-base">Twój cel jest blisko. Sprawdzaj postęp każdego dnia.</p>
        </div>
        <div class="text-right">
          <p id="todayDate" class="text-sm text-gray-500 font-mono"></p>
        </div>
        <div class="text-right"><p id="todayDate" class="text-sm text-gray-500 font-mono"></p></div>
      </div>
    </header>

    <!-- ======== TAB: HOME ======== -->
    <section id="dashboard" class="tab-content space-y-8">
      <!-- KPI Cards Grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <!-- Consistency -->
        <div class="glass-card p-4 md:p-6 border-l-4 border-cyan-500">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">🔥 Spójność</p>
          <h3 class="text-2xl md:text-3xl font-bold text-cyan-400 mb-2" id="kpiConsistency">0%</h3>
          <div class="w-full bg-white/5 h-1 rounded-full overflow-hidden">
            <div id="consistencyBar" class="h-full bg-gradient-to-r from-cyan-500 to-purple-500 w-0 transition-all duration-500"></div>
          </div>
          <h3 class="text-2xl md:text-3xl font-bold text-cyan-400 mb-2" id="kpiConsistency">--%</h3>
          <div class="w-full bg-white/5 h-1 rounded-full overflow-hidden"><div id="consistencyBar" class="h-full bg-gradient-to-r from-cyan-500 to-purple-500 w-0 transition-all duration-500"></div></div>
        </div>
        
        <!-- Calories Today -->
        <div class="glass-card p-4 md:p-6">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">🍽️ Dzisiaj</p>
          <h3 class="text-2xl md:text-3xl font-bold text-white mb-2">
            <span id="caloriesEaten">0</span> / <span id="caloriesTarget">2500</span>
          </h3>
          <p class="text-xs text-gray-500" id="caloriesRemaining">2500 kcal pozostało</p>
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">🍽️ Cel Kcal</p>
          <h3 class="text-2xl md:text-3xl font-bold text-white mb-2" id="caloriesTarget">-- kcal</h3>
          <p class="text-xs text-gray-500" id="proteinTarget">Białko: -- g</p>
        </div>
        
        <!-- Current Weight -->
        <div class="glass-card p-4 md:p-6">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">⚖️ Waga</p>
          <h3 class="text-2xl md:text-3xl font-bold text-white" id="kpiWeight">-- kg</h3>
          <p class="text-xs text-gray-500 mt-1" id="weightTrend">Oczekuję na dane</p>
        </div>
        
        <!-- Plan Status -->
        <div class="glass-card p-4 md:p-6">
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">📊 Plan</p>
          <h3 class="text-2xl md:text-3xl font-bold text-gradient mb-2" id="planStatus">Free</h3>
          <button onclick="showTab('profile')" class="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">Uaktualnij plan →</button>
          <p class="text-gray-400 text-xs font-semibold uppercase mb-2">🔥 Streak</p>
          <h3 class="text-2xl md:text-3xl font-bold text-gradient mb-2" id="kpiStreak">0 dni</h3>
          <p class="text-xs text-gray-500">Consecutive check-ins</p>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Consistency Chart -->
        <div class="lg:col-span-2 glass-card p-6">
          <h4 class="text-lg font-bold text-white mb-4">Analiza Spójności (7 dni)</h4>
          <div class="h-64">
            <canvas id="consistencyChart"></canvas>
          </div>
          <div class="h-64"><canvas id="consistencyChart"></canvas></div>
        </div>

        <!-- Next Steps Card -->
        <div class="glass-card p-6 flex flex-col justify-between">
          <div>
            <h4 class="text-lg font-bold text-white mb-4">🎯 Następny Krok</h4>
            <div id="nextStepContent" class="space-y-3">
              <div class="p-3 bg-white/5 rounded-lg border border-white/10">
                <p class="text-sm text-gray-400">Ładowanie danych...</p>
              </div>
              <div class="p-3 bg-white/5 rounded-lg border border-white/10"><p class="text-sm text-gray-400">Ładowanie danych…</p></div>
            </div>
          </div>
          <button class="btn-neon px-4 py-2 rounded-lg text-sm font-bold mt-4 w-full">+ DODAJ POSIŁEK</button>
          <button onclick="showTab('my-day')" class="btn-neon px-4 py-2 rounded-lg text-sm font-bold mt-4 w-full">+ DODAJ CHECK-IN</button>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="glass-card p-6">
        <h4 class="text-lg font-bold text-white mb-4">📈 Ostatnia Aktywność</h4>
        <div id="recentActivityContainer" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="text-center text-gray-500 text-sm italic py-8">Brak logów do wyświetlenia</div>
        </div>
      </div>
    </section>

    <!-- ======== TAB: MY DAY ======== -->
    <section id="my-day" class="tab-content hidden space-y-6">
      <h3 class="text-2xl md:text-3xl font-bold">Mój Dzień</h3>
      
      <!-- Neon Alert for Macro Deficiency (if applicable) -->
      <div id="macroAlert" class="hidden">
        <div class="alert-neon alert-warning">
          <p class="text-sm font-medium" id="macroAlertText"></p>
        </div>
        <div class="alert-neon alert-warning"><p class="text-sm font-medium" id="macroAlertText"></p></div>
      </div>

      <!-- Two Containers: Diet & Training -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        <!-- DIET CONTAINER -->
        <div class="glass-card p-6">
          <h4 class="text-xl font-bold text-white mb-4">🍽️ Dieta</h4>
          
          <!-- Diet Log -->
          <div id="dietLogContainer" class="space-y-3 mb-6 max-h-96 overflow-y-auto pr-2">
            <p class="text-gray-500 text-sm italic">Dodaj posiłki z planu lub manualnie</p>
          </div>
          
          <!-- Buttons -->
          <div class="flex gap-3">
            <button onclick="addFromPlan('diet')" class="flex-1 btn-secondary py-2 rounded-lg text-sm font-medium">📌 Z Planu</button>
            <button onclick="showManualForm('diet')" class="flex-1 btn-secondary py-2 rounded-lg text-sm font-medium">✏️ Inny</button>
          </div>
        </div>

        <!-- TRAINING CONTAINER -->
        <div class="glass-card p-6">
          <h4 class="text-xl font-bold text-white mb-4">💪 Trening</h4>
          
          <!-- Training Log -->
          <div id="trainingLogContainer" class="space-y-3 mb-6 max-h-96 overflow-y-auto pr-2">
            <p class="text-gray-500 text-sm italic">Dodaj ćwiczenia z planu lub manualnie</p>
          </div>
          
          <!-- Buttons -->
          <div class="flex gap-3">
            <button onclick="addFromPlan('training')" class="flex-1 btn-secondary py-2 rounded-lg text-sm font-medium">📌 Z Planu</button>
            <button onclick="showManualForm('training')" class="flex-1 btn-secondary py-2 rounded-lg text-sm font-medium">✏️ Inny</button>
          </div>
        </div>
      </div>

      <!-- Manual Entry Form (Hidden by default) -->
      <div id="manualFormContainer" class="glass-card p-6 hidden">
        <h4 class="text-lg font-bold text-white mb-4" id="manualFormTitle">Dodaj pozycję</h4>
        <form id="manualEntryForm" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Nazwa</label>
            <input type="text" id="entryName" placeholder="np. Baton proteinowy, Pompki" class="w-full p-3 rounded-lg">
          </div>
          <div class="grid grid-cols-3 gap-3">
      <!-- Check-in Form -->
      <div class="glass-card p-6">
        <h4 class="text-lg font-bold text-white mb-4">📝 Wyślij Dzienny Check-in</h4>
        <form id="checkinForm" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">Białko (g)</label>
              <input type="number" id="entryProtein" placeholder="0" class="w-full p-3 rounded-lg">
              <label class="block text-sm font-medium text-gray-300 mb-2">Dzisiejsze Posiłki</label>
              <textarea id="checkinFood" rows="3" placeholder="np. owsianka, kurczak z ryżem, shake proteinowy…" class="w-full p-3 rounded-lg"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">Węgle (g)</label>
              <input type="number" id="entryCarbs" placeholder="0" class="w-full p-3 rounded-lg">
              <label class="block text-sm font-medium text-gray-300 mb-2">Trening</label>
              <textarea id="checkinWorkout" rows="3" placeholder="np. push day 45 min, bieganie 5km…" class="w-full p-3 rounded-lg"></textarea>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">Tłuszcz (g)</label>
              <input type="number" id="entryFat" placeholder="0" class="w-full p-3 rounded-lg">
              <label class="block text-sm font-medium text-gray-300 mb-2">Samopoczucie / Nastrój</label>
              <input type="text" id="checkinMood" placeholder="np. zmęczony, świetnie, ból nogi…" class="w-full p-3 rounded-lg">
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">Waga (kg, opcjonalnie)</label>
              <input type="number" id="checkinWeight" step="0.1" placeholder="84.5" class="w-full p-3 rounded-lg">
            </div>
          </div>
          <div class="flex gap-3 items-center">
            <button type="submit" class="btn-neon px-6 py-2 rounded-lg font-bold">Wyślij Check-in</button>
            <span id="checkinStatus" class="text-sm text-gray-500"></span>
          </div>
        </form>
      </div>

      <!-- Manual Entry -->
      <div id="manualFormContainer" class="glass-card p-6 hidden">
        <h4 class="text-lg font-bold text-white mb-4" id="manualFormTitle">Dodaj pozycję</h4>
        <form id="manualEntryForm" class="space-y-4">
          <div><label class="block text-sm font-medium text-gray-300 mb-2">Nazwa</label><input type="text" id="entryName" placeholder="np. Baton proteinowy, Pompki" class="w-full p-3 rounded-lg"></div>
          <div class="grid grid-cols-3 gap-3">
            <div><label class="block text-sm font-medium text-gray-300 mb-2">Białko (g)</label><input type="number" id="entryProtein" placeholder="0" class="w-full p-3 rounded-lg"></div>
            <div><label class="block text-sm font-medium text-gray-300 mb-2">Węgle (g)</label><input type="number" id="entryCarbs" placeholder="0" class="w-full p-3 rounded-lg"></div>
            <div><label class="block text-sm font-medium text-gray-300 mb-2">Tłuszcz (g)</label><input type="number" id="entryFat" placeholder="0" class="w-full p-3 rounded-lg"></div>
          </div>
          <div class="flex gap-3">
            <button type="submit" class="flex-1 btn-neon py-2 rounded-lg font-bold">Dodaj</button>
            <button type="button" onclick="closeManualForm()" class="flex-1 btn-secondary py-2 rounded-lg font-medium">Anuluj</button>
          </div>
        </form>
      </div>
    </section>

    <!-- ======== TAB: PLAN ======== -->
    <section id="plan" class="tab-content hidden space-y-6">
      <div class="flex justify-between items-center">
      <div class="flex justify-between items-center flex-wrap gap-3">
        <h3 class="text-2xl md:text-3xl font-bold">Plan Treningowy & Dieta</h3>
        <div class="flex items-center gap-2">
          <button onclick="fetchAndRenderPlan(true)" id="refreshPlanBtn" class="btn-neon px-4 py-2 rounded-lg text-sm font-bold">⟳ Generuj nowy plan</button>
          <button onclick="prevDay()" class="btn-secondary p-2 rounded-lg">←</button>
          <span id="currentDay" class="text-sm font-medium text-gray-400">Pon</span>
          <span id="currentDay" class="text-sm font-medium text-gray-400 min-w-[40px] text-center">Pon</span>
          <button onclick="nextDay()" class="btn-secondary p-2 rounded-lg">→</button>
        </div>
      </div>

      <!-- Day Selector Carousel -->
      <!-- Autoregulation banner (shown when mood triggered) -->
      <div id="autoregBanner" class="hidden alert-neon">
        <p class="text-sm font-medium" id="autoregText"></p>
      </div>

      <!-- Day Carousel -->
      <div class="glass-card p-4 overflow-x-auto">
        <div class="flex gap-2" id="dayCarousel">
          <!-- Days generated by JS -->
        <div class="flex gap-2" id="dayCarousel"></div>
      </div>

      <!-- Plan loading state -->
      <div id="planLoader" class="hidden flex-col items-center justify-center py-16 gap-4">
        <div class="loading-spinner"></div>
        <p class="text-gray-400 text-sm">Pobieram plan z API…</p>
      </div>

      <!-- Day Macros summary -->
      <div id="dayMacrosBanner" class="hidden glass-card p-4">
        <div class="flex flex-wrap gap-4 items-center justify-between">
          <div>
            <span class="text-xs text-gray-500 uppercase font-bold">Typ dnia</span>
            <span id="dayTypeBadge" class="ml-2 px-3 py-1 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300"></span>
          </div>
          <div class="flex gap-6 text-sm">
            <span>🔥 <strong id="macroKcal" class="text-cyan-400"></strong> kcal</span>
            <span>🥩 <strong id="macroProtein" class="text-green-400"></strong>g białka</span>
            <span>🍞 <strong id="macroCarbs" class="text-yellow-400"></strong>g węgli</span>
            <span>🥑 <strong id="macroFat" class="text-orange-400"></strong>g tłuszczu</span>
          </div>
        </div>
      </div>

      <!-- Two Column Layout: Diet & Training -->
      <!-- Plan content: diet + training -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- DIET PLAN -->
        <div class="glass-card p-6">
          <h4 class="text-xl font-bold text-white mb-4">🍽️ Dieta Zaplanowana</h4>
          <div id="planDietContainer" class="space-y-3">
            <div class="p-4 bg-white/5 rounded-lg text-gray-500 text-sm italic text-center">
              Zaplanowane posiłki pojawią się tutaj
            </div>
            <div class="p-4 bg-white/5 rounded-lg text-gray-500 text-sm italic text-center">Zaplanowane posiłki pojawią się tutaj</div>
          </div>
        </div>

        <!-- TRAINING PLAN -->
        <div class="glass-card p-6">
          <h4 class="text-xl font-bold text-white mb-4">💪 Trening Zaplanowany</h4>
          <h4 class="text-xl font-bold text-white mb-4" id="trainingPanelTitle">💪 Trening Zaplanowany</h4>
          <div id="planTrainingContainer" class="space-y-3">
            <div class="p-4 bg-white/5 rounded-lg text-gray-500 text-sm italic text-center">
              Zaplanowane ćwiczenia pojawią się tutaj
            </div>
            <div class="p-4 bg-white/5 rounded-lg text-gray-500 text-sm italic text-center">Zaplanowane ćwiczenia pojawią się tutaj</div>
          </div>
        </div>
      </div>

      <!-- Expand Details Modal (Hidden by default) -->
      <!-- Expand Details Modal -->
      <div id="expandModal" class="hidden fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div class="glass-card max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
        <div class="glass max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
          <div class="flex justify-between items-start mb-4">
            <h5 id="expandTitle" class="text-xl font-bold text-white"></h5>
            <button onclick="closeExpandModal()" class="text-gray-400 hover:text-white">✕</button>
            <button onclick="closeExpandModal()" class="text-gray-400 hover:text-white text-xl">✕</button>
          </div>
          <div id="expandContent" class="space-y-4 text-gray-300">
            <!-- Content populated by JS -->
          </div>
          <div class="mt-6 flex gap-3">
          <div id="expandContent" class="space-y-4 text-gray-300"></div>
          <div class="mt-6 flex gap-3" id="expandActions">
            <button onclick="swapItem()" class="flex-1 btn-neon py-2 rounded-lg font-bold">Zamień na inne</button>
            <button onclick="closeExpandModal()" class="flex-1 btn-secondary py-2 rounded-lg font-medium">Zamknij</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ======== TAB: PROFILE ======== -->
    <section id="profile" class="tab-content hidden space-y-6">
      <h3 class="text-2xl md:text-3xl font-bold">Profil</h3>

      <!-- Profile Sub-tabs -->
      <!-- Sub-tabs -->
      <div class="glass-card p-2 flex gap-2 overflow-x-auto">
        <button onclick="switchProfileTab('user-data')" class="profile-tab active px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">👤 Dane</button>
        <button onclick="switchProfileTab('goals')" class="profile-tab px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">🎯 Cele</button>
        <button onclick="switchProfileTab('preferences')" class="profile-tab px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">⚙️ Preferencje</button>
        <button onclick="switchProfileTab('payments')" class="profile-tab px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">💳 Płatności</button>
      <div class="glass p-2 flex gap-2 overflow-x-auto">
        <button onclick="switchProfileTab('user-data')" class="profile-tab active bg-white/10 text-cyan-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">👤 Dane</button>
        <button onclick="switchProfileTab('goals')" class="profile-tab text-gray-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">🎯 Cele</button>
        <button onclick="switchProfileTab('sport')" class="profile-tab text-gray-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">🏀 Sport</button>
        <button onclick="switchProfileTab('preferences')" class="profile-tab text-gray-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">⚙️ Preferencje</button>
        <button onclick="switchProfileTab('payments')" class="profile-tab text-gray-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap">💳 Płatności</button>
      </div>

      <!-- USER DATA TAB -->
      <!-- USER DATA -->
      <div id="profile-user-data" class="profile-tab-content space-y-4">
        <div class="glass-card p-6">
        <div class="glass p-6">
          <h4 class="text-lg font-bold text-white mb-4">Informacje Podstawowe</h4>
          <form id="userDataForm" class="space-y-4">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Imię</label>
                <input type="text" id="firstName" placeholder="Imię" class="w-full p-3 rounded-lg">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Wiek</label>
                <input type="number" id="age" placeholder="Wiek" class="w-full p-3 rounded-lg">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Wzrost (cm)</label>
                <input type="number" id="height" placeholder="180" class="w-full p-3 rounded-lg">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Waga (kg)</label>
                <input type="number" id="weight" placeholder="80" step="0.1" class="w-full p-3 rounded-lg">
              </div>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Imię</label><input type="text" id="firstName" placeholder="Imię" class="w-full p-3 rounded-lg"></div>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Wiek</label><input type="number" id="age" placeholder="Wiek" class="w-full p-3 rounded-lg"></div>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Wzrost (cm)</label><input type="number" id="height" placeholder="180" class="w-full p-3 rounded-lg"></div>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Waga (kg)</label><input type="number" id="weight" placeholder="80" step="0.1" class="w-full p-3 rounded-lg"></div>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Cel (waga, kg)</label>
                <input type="number" id="targetWeight" placeholder="75" step="0.1" class="w-full p-3 rounded-lg">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Płeć</label>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Cel (waga, kg)</label><input type="number" id="targetWeight" placeholder="75" step="0.1" class="w-full p-3 rounded-lg"></div>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Płeć</label>
                <select id="gender" class="w-full p-3 rounded-lg">
                  <option value="">Wybierz</option>
                  <option value="mężczyzna">Mężczyzna</option>
                  <option value="kobieta">Kobieta</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-2">Alergie</label>
                <input type="text" id="allergies" placeholder="np. orzechy, mleko" class="w-full p-3 rounded-lg">
              </div>
              <div><label class="block text-sm font-medium text-gray-300 mb-2">Alergie</label><input type="text" id="allergies" placeholder="np. orzechy, mleko" class="w-full p-3 rounded-lg"></div>
            </div>
            <button type="submit" class="btn-neon px-6 py-2 rounded-lg font-bold">Zapisz Zmiany</button>
            <div class="flex gap-3 items-center">
              <button type="submit" class="btn-neon px-6 py-2 rounded-lg font-bold">Zapisz Zmiany</button>
              <span id="profileStatus" class="text-sm text-gray-500"></span>
            </div>
          </form>
        </div>
      </div>

      <!-- GOALS TAB -->
      <!-- GOALS -->
      <div id="profile-goals" class="profile-tab-content hidden space-y-4">
        <div class="glass-card p-6">
        <div class="glass p-6">
          <h4 class="text-lg font-bold text-white mb-4">🎯 Cele Treningowe</h4>
          <p class="text-sm text-gray-400 mb-4">Zaznacz cele, które Cię interesują. Wpłyną na Twój plan treningowy.</p>
          <div id="goalsCheckboxes" class="space-y-3">
            <!-- Populated by JS -->
          </div>
          <p class="text-sm text-gray-400 mb-4">Zaznacz cele, które Cię interesują.</p>
          <div id="goalsCheckboxes" class="space-y-3"></div>
          <button onclick="saveGoals()" class="btn-neon px-6 py-2 rounded-lg font-bold mt-4">Zapisz Cele</button>
        </div>
      </div>

      <!-- PREFERENCES TAB -->
      <!-- ======== SPORT TAB (NEW) ======== -->
      <div id="profile-sport" class="profile-tab-content hidden space-y-4">
        <div class="glass-card p-6">
        <div class="glass p-6">
          <div class="flex items-center gap-3 mb-4">
            <h4 class="text-lg font-bold text-white">🏀 Moduł Sportowy</h4>
            <span class="sport-badge">NOWE</span>
          </div>
          <p class="text-sm text-gray-400 mb-6">Wybierz sport i specjalizację. W wybranych dniach system zastąpi siłownię treningiem techniki sportowej.</p>

          <div class="space-y-6">
            <!-- Sport Focus -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">Dyscyplina Sportowa</label>
              <select id="sportFocus" onchange="onSportFocusChange()" class="w-full p-3 rounded-lg">
                <option value="">Brak (wyłącz moduł sportowy)</option>
                <option value="koszykówka">🏀 Koszykówka</option>
              </select>
            </div>

            <!-- Sport Specialization (shown when sport selected) -->
            <div id="sportSpecSection" class="hidden">
              <label class="block text-sm font-medium text-gray-300 mb-2">Specjalizacja</label>
              <div id="sportSpecOptions" class="grid grid-cols-2 md:grid-cols-3 gap-3"></div>
            </div>

            <!-- Sport Training Days -->
            <div id="sportDaysSection" class="hidden">
              <label class="block text-sm font-medium text-gray-300 mb-3">Dni Treningu Sportowego</label>
              <p class="text-xs text-gray-500 mb-3">Zaznacz dni, w których chcesz trenować technikę zamiast siłowni.</p>
              <div class="grid grid-cols-3 md:grid-cols-7 gap-2" id="sportDaysCheckboxes">
                <!-- populated by JS -->
              </div>
            </div>

            <!-- Save button -->
            <div class="flex gap-3 items-center pt-2">
              <button onclick="saveSportConfig()" class="btn-sport px-6 py-2 rounded-lg font-bold">Zapisz Konfigurację Sportową</button>
              <span id="sportStatus" class="text-sm text-gray-500"></span>
            </div>
          </div>
        </div>

        <!-- Sport info card -->
        <div class="glass-card p-6 sport-card">
        <div class="glass p-6 sport-card">
          <h5 class="font-bold text-white mb-3">📋 Dostępne Drille (Koszykówka)</h5>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="bg-white/5 p-3 rounded-lg">
              <p class="text-sm font-medium text-white">🏀 Rzuty</p>
              <p class="text-xs text-gray-400 mt-1">Rzuty osobiste, za 3 pkt, z odchylenia, Mikan Drill</p>
            </div>
            <div class="bg-white/5 p-3 rounded-lg">
              <p class="text-sm font-medium text-white">🤾 Drybling</p>
              <p class="text-xs text-gray-400 mt-1">Figure-8, Stationary Crossover</p>
            </div>
            <div class="bg-white/5 p-3 rounded-lg">
              <p class="text-sm font-medium text-white">🛡️ Obrona</p>
              <p class="text-xs text-gray-400 mt-1">Defensive Slides</p>
            </div>
          </div>
        </div>
      </div>

      <!-- PREFERENCES -->
      <div id="profile-preferences" class="profile-tab-content hidden space-y-4">
        <div class="glass-card p-6">
        <div class="glass p-6">
          <h4 class="text-lg font-bold text-white mb-4">⚙️ Preferencje</h4>
          
          <div class="space-y-4">
            <div>
              <h5 class="text-sm font-bold text-white mb-2">Dostępny Sprzęt</h5>
              <p class="text-xs text-gray-500 mb-3">Jeśli odznaczysz sprzęt, zostanie usunięty z Twojego planu.</p>
              <div id="equipmentCheckboxes" class="space-y-2">
                <!-- Populated by JS -->
              </div>
              <p class="text-xs text-gray-500 mb-3">Jeśli odznaczysz sprzęt, zostanie usunięty z planu.</p>
              <div id="equipmentCheckboxes" class="space-y-2"></div>
            </div>
            
            <div class="border-t border-white/10 pt-4">
              <h5 class="text-sm font-bold text-white mb-2">Wykluczone Potrawy</h5>
              <input type="text" id="excludedFoods" placeholder="np. kurczak, ryż, orzechy (oddzielone przecinkami)" class="w-full p-3 rounded-lg">
              <input type="text" id="excludedFoods" placeholder="np. kurczak, ryż, orzechy (przecinkami)" class="w-full p-3 rounded-lg">
            </div>
            
            <button onclick="savePreferences()" class="btn-neon px-6 py-2 rounded-lg font-bold w-full">Zapisz Preferencje</button>
          </div>
        </div>
      </div>

      <!-- PAYMENTS TAB -->
      <!-- PAYMENTS -->
      <div id="profile-payments" class="profile-tab-content hidden space-y-4">
        <div class="glass-card p-6">
        <div class="glass p-6">
          <h4 class="text-lg font-bold text-white mb-4">💳 Płatności</h4>
          <div class="text-center py-8">
            <div class="text-4xl mb-2">🚀</div>
            <p class="text-gray-400">Moduł płatności jest w przygotowaniu.</p>
            <p class="text-sm text-gray-500 mt-2">Wkrótce będziesz mógł uaktualnić swój plan Premium.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ======== TAB: CONTACT ======== -->
    <section id="contact" class="tab-content hidden space-y-6">
      <h3 class="text-2xl md:text-3xl font-bold">Kontakt</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Discord Tile -->
        <div class="glass-card p-8 flex flex-col items-center justify-center text-center hover:border-cyan-500/50 cursor-pointer transition-all group">
        <div class="glass p-8 flex flex-col items-center justify-center text-center hover:border-cyan-500/50 cursor-pointer transition-all group">
          <div class="text-5xl mb-4 group-hover:scale-110 transition-transform">💜</div>
          <h4 class="text-xl font-bold text-white mb-2">Discord</h4>
          <p class="text-sm text-gray-400 mb-4">Dołącz do naszej społeczności i czat z innymi użytkownikami.</p>
          <p class="text-sm text-gray-400 mb-4">Dołącz do naszej społeczności.</p>
          <div class="flex gap-2 w-full">
            <button onclick="window.open('https://discord.gg/z3tol', '_blank')" class="flex-1 btn-neon py-2 rounded-lg text-sm font-bold">Otwórz Discord</button>
            <button onclick="window.open('https://discord.gg/z3tol','_blank')" class="flex-1 btn-neon py-2 rounded-lg text-sm font-bold">Otwórz Discord</button>
            <button onclick="copyToClipboard('z3tol')" class="btn-secondary px-3 py-2 rounded-lg text-sm">📋</button>
          </div>
          <p class="text-xs text-gray-600 mt-2">Nazwa: z3tol</p>
        </div>

        <!-- Email Tile -->
        <div class="glass-card p-8 flex flex-col items-center justify-center text-center hover:border-cyan-500/50 cursor-pointer transition-all group">
        <div class="glass p-8 flex flex-col items-center justify-center text-center hover:border-cyan-500/50 cursor-pointer transition-all group">
          <div class="text-5xl mb-4 group-hover:scale-110 transition-transform">✉️</div>
          <h4 class="text-xl font-bold text-white mb-2">Email</h4>
          <p class="text-sm text-gray-400 mb-4">Napisz do nas bezpośrednio ze swoimi pytaniami.</p>
          <p class="text-sm text-gray-400 mb-4">Napisz do nas bezpośrednio.</p>
          <div class="flex gap-2 w-full">
            <button onclick="window.location.href='mailto:adam.zamorski.10@gmail.com'" class="flex-1 btn-neon py-2 rounded-lg text-sm font-bold">Wyślij Email</button>
            <button onclick="copyToClipboard('adam.zamorski.10@gmail.com')" class="btn-secondary px-3 py-2 rounded-lg text-sm">📋</button>
          </div>
          <p class="text-xs text-gray-600 mt-2">adam.zamorski.10@gmail.com</p>
        </div>
      </div>
    </section>
  </main>
</div>

      <!-- FAQ Section -->
      <div class="glass-card p-6">
        <h4 class="text-lg font-bold text-white mb-4">❓ Popularne Pytania</h4>
        <div class="space-y-4">
          <details class="group">
            <summary class="flex cursor-pointer items-center justify-between font-medium text-white hover:text-cyan-400 transition-colors">
              Jak dodać nowy posiłek?
              <span class="transition group-open:rotate-180">▼</span>
            </summary>
            <p class="text-sm text-gray-400 mt-2">Przejdź do „Mój Dzień" → Kliknij „✏️ Inny" w sekcji Dieta. Wpisz nazwę, makroskładniki i gotowe!</p>
          </details>
          
          <details class="group">
            <summary class="flex cursor-pointer items-center justify-between font-medium text-white hover:text-cyan-400 transition-colors">
              Czy mogę zamienić ćwiczenie?
              <span class="transition group-open:rotate-180">▼</span>
            </summary>
            <p class="text-sm text-gray-400 mt-2">Oczywiście! W zakładce „Plan" kliknij na ćwiczenie, a następnie przycisk „Zamień na inne". System zaproponuje alternatywy.</p>
          </details>
          
          <details class="group">
            <summary class="flex cursor-pointer items-center justify-between font-medium text-white hover:text-cyan-400 transition-colors">
              Czy działam offline?
              <span class="transition group-open:rotate-180">▼</span>
            </summary>
            <p class="text-sm text-gray-400 mt-2">Tak! FitAI jest Progressive Web App. Wszystkie dane synchronizują się automatycznie.</p>
          </details>
<!-- ====== ADD OTHER MODAL ====== -->
<div id="addOtherModal" class="hidden fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
  <div class="glass w-full max-w-sm p-6" style="border-color:var(--border-cyan)!important;">
    <div class="flex justify-between items-center mb-5">
      <h5 class="text-lg font-bold text-white" id="addOtherTitle">Dodaj własne</h5>
      <button onclick="closeAddOtherModal()" class="text-gray-500 hover:text-white text-xl">✕</button>
    </div>
    <div class="space-y-3">
      <div><label class="block text-xs text-gray-400 mb-1">Nazwa *</label><input type="text" id="otherName" placeholder="np. Baton proteinowy" class="w-full"></div>
      <div id="otherDietFields" class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-xs text-gray-400 mb-1">Kalorie (kcal)</label><input type="number" id="otherKcal" placeholder="200" class="w-full"></div>
          <div><label class="block text-xs text-gray-400 mb-1">Białko (g)</label><input type="number" id="otherProtein" placeholder="0" class="w-full"></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-xs text-gray-400 mb-1">Węgle (g)</label><input type="number" id="otherCarbs" placeholder="0" class="w-full"></div>
          <div><label class="block text-xs text-gray-400 mb-1">Tłuszcz (g)</label><input type="number" id="otherFat" placeholder="0" class="w-full"></div>
        </div>
      </div>
      <div id="otherTrainingFields" class="hidden">
        <label class="block text-xs text-gray-400 mb-1">Czas / opis</label>
        <input type="text" id="otherDuration" placeholder="np. 30 min, 3×10 powt." class="w-full">
      </div>
    </div>
    <div class="flex gap-3 mt-5">
      <button onclick="submitAddOther()" class="flex-1 btn-neon py-2 rounded-xl font-bold text-sm">Dodaj</button>
      <button onclick="closeAddOtherModal()" class="flex-1 btn-secondary py-2 rounded-xl text-sm">Anuluj</button>
    </div>
  </div>
</div>


<!-- ======== DRILL RESULT MODAL ======== -->
<div id="drillModal" class="hidden fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4">
  <div class="glass-card max-w-lg w-full p-6 sport-card">
<div id="drillModal" class="hidden fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-[120] p-4">
  <div class="glass max-w-lg w-full p-6 sport-card">
    <div class="flex justify-between items-start mb-4">
      <div>
        <h5 class="text-xl font-bold text-white" id="drillModalTitle">Wynik Drilla</h5>
        <p class="text-xs text-gray-400 mt-1" id="drillModalDesc"></p>
      </div>
      <button onclick="closeDrillModal()" class="text-gray-400 hover:text-white text-xl">✕</button>
    </div>

    <div class="space-y-5">
      <!-- Trafienia / próby -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">✅ Trafienia / Powtórzenia</label>
          <input type="number" id="drillSuccess" min="0" placeholder="np. 14" class="w-full p-3 rounded-lg text-lg font-bold">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">🎯 Łączna liczba prób</label>
          <input type="number" id="drillTotal" min="1" placeholder="np. 20" class="w-full p-3 rounded-lg text-lg font-bold">
        </div>
      </div>
    </section>

  </main>
      <!-- Accuracy preview -->
      <div id="accuracyPreview" class="bg-white/5 rounded-lg p-3 text-center hidden">
        <p class="text-xs text-gray-400 mb-1">Skuteczność</p>
        <p class="text-2xl font-bold text-cyan-400" id="accuracyValue">--%</p>
        <div class="w-full bg-white/10 h-2 rounded-full mt-2 overflow-hidden">
          <div id="accuracyBar" class="h-full bg-gradient-to-r from-orange-500 to-cyan-400 transition-all duration-300" style="width:0%"></div>
        </div>
      </div>

      <!-- RPE Slider -->
      <div>
        <label class="block text-sm font-medium text-gray-300 mb-2">
          💢 Trudność (RPE): <span id="rpeValue" class="text-cyan-400 font-bold">5</span>/10
        </label>
        <input type="range" id="drillRpe" min="1" max="10" value="5" oninput="document.getElementById('rpeValue').textContent=this.value" class="w-full accent-cyan-400">
        <div class="flex justify-between text-xs text-gray-500 mt-1">
          <span>Bardzo łatwe</span><span>Maksymalny wysiłek</span>
        </div>
      </div>

      <!-- Notes -->
      <div>
        <label class="block text-sm font-medium text-gray-300 mb-2">📝 Notatki (opcjonalnie)</label>
        <textarea id="drillNotes" rows="2" placeholder="np. Lewa strona wyraźnie słabsza…" class="w-full p-3 rounded-lg"></textarea>
      </div>
    </div>

    <div class="mt-6 flex gap-3">
      <button onclick="submitDrillResult()" class="flex-1 btn-sport py-3 rounded-lg font-bold">📊 Zapisz Wynik</button>
      <button onclick="closeDrillModal()" class="btn-secondary px-4 py-3 rounded-lg font-medium">Anuluj</button>
    </div>
    <p id="drillSubmitStatus" class="text-sm text-center mt-3 text-gray-500 hidden"></p>
  </div>
</div>

<!-- ======== JAVASCRIPT - CORE LOGIC ======== -->
<!-- ======== JAVASCRIPT ======== -->
<script>
  // ============ STATE MANAGEMENT ============
  const state = {
    currentUser: null,
    users: {},
    substitutes: {}, // Persistent AI-generated alternatives
    currentDay: 0,
    expandedItem: null,
    manualFormType: null,
    days: ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Niedz']
  };
// ─────────────────────────────────────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';

  const mockGoals = [
    { id: 'strength', label: 'Siłownia', emoji: '🏋️' },
    { id: 'cardio', label: 'Kardio/Bieganie', emoji: '🏃' },
    { id: 'mobility', label: 'Mobilność/Joga', emoji: '🧘' },
    { id: 'mass', label: 'Budowanie Masy', emoji: '📈' }
  ];
// Identity – in real integration replace with Netlify Identity token
const getIdentityId = () => state.identityId || 'demo_user_001';

  const mockEquipment = [
    { id: 'dumbbells', label: 'Hantle', emoji: '🏋️' },
    { id: 'barbell', label: 'Sztanga', emoji: '⚖️' },
    { id: 'cables', label: 'Kable/Maszyny', emoji: '⚙️' },
    { id: 'mat', label: 'Mata treningowa', emoji: '🧵' }
  ];
// ─────────────────────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────────────────────
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
const getDayName = (idx) => state.days[idx];

  // ============ INIT & LOAD ============
  function initApp() {
    updateDate();
    loadUsersFromStorage();
    renderUserList();
    if (!state.currentUser && Object.keys(state.users).length > 0) {
      switchUser(Object.keys(state.users)[0]);
    }
    initCharts();
    renderGoalsCheckboxes();
    renderEquipmentCheckboxes();
    renderDayCarousel();
  }
const SPORT_SPECS = {
  'koszykówka': [
    { value: 'rzuty',   label: '🏀 Rzuty' },
    { value: 'drybling', label: '🤾 Drybling' },
    { value: 'obrona',  label: '🛡️ Obrona' },
  ],
};

/** Zwraca specjalizacje dla danego sportu.
 *  Używa .toLowerCase() żeby "Koszykówka" i "koszykówka" trafiały na ten sam klucz. */
function getSportSpecs(sportValue) {
  if (!sportValue) return [];
  return SPORT_SPECS[String(sportValue).trim().toLowerCase()] || [];
}

  function updateDate() {
    const today = new Date();
    document.getElementById('todayDate').textContent = today.toLocaleDateString('pl-PL', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }
const mockGoals = [
  { id: 'strength', label: 'Siłownia',        emoji: '🏋️' },
  { id: 'cardio',   label: 'Kardio/Bieganie', emoji: '🏃' },
  { id: 'mobility', label: 'Mobilność/Joga',  emoji: '🧘' },
  { id: 'mass',     label: 'Budowanie Masy',  emoji: '📈' },
];
const mockEquipment = [
  { id: 'dumbbells', label: 'Hantle',        emoji: '🏋️' },
  { id: 'barbell',   label: 'Sztanga',       emoji: '⚖️' },
  { id: 'cables',    label: 'Kable/Maszyny', emoji: '⚙️' },
  { id: 'mat',       label: 'Mata',          emoji: '🧵' },
];

  // ============ MULTI-USER SYSTEM ============
  function loadUsersFromStorage() {
    // In a real app, fetch from API: fetch('/api/users').then(r => r.json())
    // For now, using mock data from fitai_users.json
    state.users = {
      'user123': {
        name: 'Marek',
        age: 28,
        height: 182,
        weight: 84.5,
        targetWeight: 78,
        gender: 'mężczyzna',
        goal: 'Redukcja',
        caloriesTarget: 2463,
        proteinTarget: 185,
        goals: ['strength', 'cardio'],
        equipment: ['dumbbells', 'barbell', 'mat'],
        excludedFoods: [],
        logs: [],
        dietPlan: {
          'Pon': [
            { id: '1', name: 'Owsianka', protein: 15, carbs: 50, fat: 5, kcal: 300 }
          ]
        },
        trainingPlan: {
          'Pon': [
            { id: '1', name: 'Wyciskanie sztangi leżąc', sets: 4, reps: 6, weight: 120, tags: ['hantle', 'klatka'] }
          ]
        }
      }
    };
// ─────────────────────────────────────────────────────────────────────────────
// API HELPERS
// ─────────────────────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const url = API_BASE + path;
  const defaults = { headers: { 'Content-Type': 'application/json' } };
  const res = await fetch(url, { ...defaults, ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

  function renderUserList() {
    const userList = document.getElementById('userList');
    userList.innerHTML = Object.entries(state.users).map(([id, user]) => `
      <button onclick="switchUser('${id}')" class="w-full text-left px-3 py-2 text-sm hover:bg-white/10 rounded transition-colors ${state.currentUser === id ? 'text-cyan-400 bg-white/10' : 'text-gray-400'}" >
        ${user.name} ${state.currentUser === id ? '✓' : ''}
      </button>
    `).join('');
async function pingApi() {
  try {
    const d = await apiFetch('/');
    console.log('API status:', d.status);
  } catch {
    console.warn('API offline');
  }
}

  function switchUser(userId) {
    state.currentUser = userId;
    const user = state.users[userId];
    document.getElementById('greetingName').textContent = user.name;
    document.getElementById('currentUserDisplay').textContent = `👤 ${user.name}`;
    document.getElementById('kpiWeight').textContent = user.weight + ' kg';
    document.getElementById('caloriesTarget').textContent = user.caloriesTarget;
    renderUserList();
    updateDashboard();
// ─────────────────────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────────────────────
async function initApp() {
  updateDate();
  renderDayCarousel();
  renderGoalsCheckboxes();
  renderEquipmentCheckboxes();
  renderSportDaysCheckboxes();
  initCharts();
  await pingApi();
  await loadProfile();
  if (!state.weeklyPlan) await fetchAndRenderPlan(false);
  loadTodayPlanChecklist();
  updateDashboard();
}

function updateDate() {
  document.getElementById('todayDate').textContent =
    new Date().toLocaleDateString('pl-PL', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
}

// ─────────────────────────────────────────────────────────────────────────────
// PROFILE  – load + populate form
// ─────────────────────────────────────────────────────────────────────────────
async function loadProfile() {
  try {
    const data = await apiFetch(`/app/profile/${getIdentityId()}`);
    state.profile = data;
    populateProfileUI(data);
    updateDashboardKpis(data);
    document.getElementById('greetingName').textContent = data.name || 'Użytkowniku';
    document.getElementById('currentUserDisplay').textContent = `👤 ${data.name || 'Użytkownik'}`;
  } catch (e) {
    console.warn('Nie udało się załadować profilu:', e.message);
  }
}

  // ============ TAB SWITCHING ============
  function showTab(tabId) {
    // Fade out all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
      if (!tab.classList.contains('hidden')) {
        tab.classList.add('exit');
        setTimeout(() => {
          tab.classList.add('hidden');
          tab.classList.remove('exit');
        }, 200);
      }
    });
function populateProfileUI(p) {
  const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.value = val; };
  set('firstName',    p.name);
  set('age',          p.age);
  set('height',       p.height);
  set('weight',       p.weight);
  set('targetWeight', p.target_weight);
  set('gender',       p.gender);
  set('allergies',    p.allergies);
  set('excludedFoods', (p.avoid_foods || []).join(', '));

    // Show new tab
    setTimeout(() => {
      document.getElementById(tabId).classList.remove('hidden');
    }, 200);
  // Goals
  (p.training_focus || []).forEach(g => {
    const cb = document.querySelector(`.goal-checkbox[value="${g}"]`);
    if (cb) cb.checked = true;
  });

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
    });
    event?.currentTarget?.classList.add('active');
  // Sport fields
  const sf = p.sport_focus || '';
  set('sportFocus', sf);
  onSportFocusChange(p.sport_specialization, p.sport_training_days || []);
}

    // Close mobile menu
    document.getElementById('sidebar').classList.remove('mobile-open');
function updateDashboardKpis(p) {
  const el = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  el('caloriesTarget', (p.calories_target || '--') + ' kcal');
  el('proteinTarget',  'Białko: ' + (p.protein_target || '--') + ' g');
  el('kpiWeight',      (p.weight || '--') + ' kg');
  el('kpiStreak',      (p.streak_days || 0) + ' dni');
  el('sidebarCalories', (p.calories_target || '--') + ' kcal');
  el('sidebarProtein',  (p.protein_target || '--') + ' g');
  el('sidebarTarget',   (p.target_weight || '--') + ' kg');
  
  // Consistency KPI
  const todayIdx = (new Date().getDay() + 6) % 7;
  const k = `${getIdentityId()}_${getDayName(todayIdx)}`;
  const checked = state.dayChecked[k] || {};
  const dayData = state.weeklyPlan?.days?.[todayIdx];
  if (dayData) {
      const total = (dayData.meals?.length || 0) + (dayData.workout?.exercises?.length || 0);
      const done = Object.values(checked).filter(v => v).length;
      const pct = total > 0 ? Math.round(done/total*100) : 0;
      el('kpiConsistency', pct + '%');
      const bar = document.getElementById('consistencyBar');
      if (bar) bar.style.width = pct + '%';
  }

  // ============ PROFILE TABS ============
  function switchProfileTab(tab) {
    document.querySelectorAll('.profile-tab-content').forEach(el => {
      el.classList.add('hidden');
  // Rings Logic
  updateRings(p);
}

function updateRings(p) {
    const todayIdx = (new Date().getDay() + 6) % 7;
    const k = `${getIdentityId()}_${getDayName(todayIdx)}`;
    const checked = state.dayChecked[k] || {};
    const dayData = state.weeklyPlan?.days?.[todayIdx];
    if (!dayData) return;

    let eatenKcal = 0, eatenProt = 0;
    dayData.meals?.forEach((m, i) => {
        if (checked['meal_'+i]) {
            eatenKcal += (m.macro_target?.kcal || m.kcal_catalog || 0);
            eatenProt += (m.macro_target?.protein_g || 0);
        }
    });
    document.querySelectorAll('.profile-tab').forEach(el => {
      el.classList.remove('active', 'bg-white/10', 'text-cyan-400');
      el.classList.add('text-gray-400');
    // Add extra items
    (state.extraItems[getIdentityId()] || []).forEach(ex => {
        if (ex.type === 'diet') { eatenKcal += ex.kcal; eatenProt += ex.protein; }
    });
    document.getElementById(`profile-${tab}`).classList.remove('hidden');
    event.currentTarget.classList.add('active', 'bg-white/10', 'text-cyan-400');
  }

  // ============ DASHBOARD RENDERING ============
  function updateDashboard() {
    const user = state.users[state.currentUser];
    if (!user) return;
    const targetKcal = p.calories_target || 2000;
    const targetProt = p.protein_target || 150;

    // Update KPIs
    const consistency = Math.round(Math.random() * 100);
    document.getElementById('kpiConsistency').textContent = consistency + '%';
    document.getElementById('consistencyBar').style.width = consistency + '%';
    setRing('ringCalories', eatenKcal, targetKcal, 'ringCalPct');
    setRing('ringProtein', eatenProt, targetProt, 'ringProtPct');
    
    const macroPct = Math.round(((eatenKcal/targetKcal) + (eatenProt/targetProt)) / 2 * 100);
    setRing('ringMacro', Math.min(macroPct, 100), 100, 'ringMacroPct');
}

    // Update calories
    const caloriesEaten = Math.round(Math.random() * user.caloriesTarget);
    document.getElementById('caloriesEaten').textContent = caloriesEaten;
    document.getElementById('caloriesRemaining').textContent = (user.caloriesTarget - caloriesEaten) + ' kcal pozostało';
function setRing(circleId, val, max, pctId) {
    const pct = max > 0 ? Math.min(Math.round(val/max*100), 100) : 0;
    const offset = 226 - (226 * (pct/100));
    const el = document.getElementById(circleId);
    if (el) el.style.strokeDashoffset = offset;
    if (pctId) document.getElementById(pctId).textContent = pct+'%';
}

    // Update next steps
    const steps = [
      '🍽️ Dodaj drugi posiłek',
      '💪 Zrób dzisiejszy trening',
      '💧 Pij więcej wody',
      '📊 Zalog swoją wagę'
    ];
    document.getElementById('nextStepContent').innerHTML = `
      <div class="p-3 bg-white/5 rounded-lg border border-white/10">
        <p class="text-sm text-white font-medium">${steps[Math.floor(Math.random() * steps.length)]}</p>
      </div>
    `;

    // Render recent activity
    renderRecentActivity(user);

    // Check for macro deficiencies and show alert
    if (caloriesEaten > 0 && (user.caloriesTarget - caloriesEaten) < 300) {
      const alert = document.getElementById('macroAlert');
      alert.classList.remove('hidden');
      document.getElementById('macroAlertText').textContent = `🚀 Brakuje Ci ${user.caloriesTarget - caloriesEaten} kcal! Dodaj ostatni posiłek.`;
// ─────────────────────────────────────────────────────────────────────────────
// TAB SWITCHING
// ─────────────────────────────────────────────────────────────────────────────
function showTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(tab => {
    if (!tab.classList.contains('hidden')) {
      tab.classList.add('exit');
      setTimeout(() => { tab.classList.add('hidden'); tab.classList.remove('exit'); }, 200);
    }
  }
  });
  setTimeout(() => document.getElementById(tabId)?.classList.remove('hidden'), 200);
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  if (tabId === 'plan' && !state.weeklyPlan) fetchAndRenderPlan(false);
}

  function renderRecentActivity(user) {
    const container = document.getElementById('recentActivityContainer');
    const activities = [
      { icon: '🥗', name: 'Sałatka grecka', date: 'Dzisiaj 12:30', kcal: 350 },
      { icon: '🏃', name: 'Bieganie 5km', date: 'Dzisiaj 07:00', kcal: -450 }
    ];
    container.innerHTML = activities.map(a => `
      <div class="glass-card p-4">
        <div class="flex items-start justify-between">
          <div class="flex gap-3">
            <span class="text-2xl">${a.icon}</span>
            <div>
              <p class="text-white font-medium">${a.name}</p>
              <p class="text-xs text-gray-500">${a.date}</p>
            </div>
          </div>
          <span class="text-sm font-medium ${a.kcal > 0 ? 'text-yellow-400' : 'text-cyan-400'}">${a.kcal > 0 ? '+' : ''}${a.kcal} kcal</span>
        </div>
      </div>
    `).join('');
  }
function switchProfileTab(tab) {
  document.querySelectorAll('.profile-tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.profile-tab').forEach(el => {
    el.classList.remove('active','bg-white/10','text-cyan-400');
    el.classList.add('text-gray-400');
  });
  document.getElementById(`profile-${tab}`)?.classList.remove('hidden');
  event.currentTarget.classList.add('active','bg-white/10','text-cyan-400');
  event.currentTarget.classList.remove('text-gray-400');
}

  // ============ CHARTS ============
  function initCharts() {
    const ctx = document.getElementById('consistencyChart');
    if (!ctx) return;
// ─────────────────────────────────────────────────────────────────────────────
// PLAN  –  fetch from API + render
// ─────────────────────────────────────────────────────────────────────────────
async function fetchAndRenderPlan(force = false) {
  const loader = document.getElementById('planLoader');
  const btn    = document.getElementById('refreshPlanBtn');
  loader?.classList.remove('hidden');
  loader?.classList.add('flex');
  if (btn) btn.disabled = true;
  document.getElementById('dayMacrosBanner')?.classList.add('hidden');

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Niedz'],
        datasets: [{
          label: 'Spójność (%)',
          data: [80, 85, 70, 90, 75, 92, 88],
          backgroundColor: 'rgba(0, 229, 255, 0.2)',
          borderColor: '#00e5ff',
          borderWidth: 2,
          borderRadius: 8,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          filler: { propagate: true }
        },
        scales: {
          y: { 
            beginAtZero: true,
            max: 100,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#64748b' }
          },
          x: { grid: { display: false }, ticks: { color: '#64748b' } }
        }
      }
  try {
    const data = await apiFetch(`/app/plan/${getIdentityId()}/generate`, {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
    state.weeklyPlan = data.plan;
    renderCurrentDay();
    loadTodayPlanChecklist();
    updateDashboard();
  } catch (e) {
    showToast('Błąd pobierania planu: ' + e.message, 'error');
  } finally {
    loader?.classList.add('hidden');
    loader?.classList.remove('flex');
    if (btn) btn.disabled = false;
  }
}

  // ============ PLAN & CAROUSEL ============
  function renderDayCarousel() {
    const carousel = document.getElementById('dayCarousel');
    carousel.innerHTML = state.days.map((day, i) => `
      <button onclick="selectDay(${i})" class="day-carousel-item px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${i === state.currentDay ? 'btn-neon' : 'btn-secondary'}">
        ${day}
      </button>
    `).join('');
  }
function renderCurrentDay() {
  if (!state.weeklyPlan?.days) return;
  const dayData = state.weeklyPlan.days[state.currentDay];
  if (!dayData) return;

  function selectDay(dayIndex) {
    state.currentDay = dayIndex;
    document.getElementById('currentDay').textContent = state.days[dayIndex];
    renderDayCarousel();
    loadPlanForDay();
  // Autoregulation banner
  const arBanner = document.getElementById('autoregBanner');
  const arText   = document.getElementById('autoregText');
  const arReason = dayData.autoregulation?.reason;
  if (arReason) {
    arText.textContent = '⚠️ Autoregulacja: ' + arReason;
    arBanner.classList.remove('hidden');
  } else {
    arBanner.classList.add('hidden');
  }

  function prevDay() {
    state.currentDay = (state.currentDay - 1 + 7) % 7;
    selectDay(state.currentDay);
  // Day macros
  const m = dayData.macros;
  if (m) {
    document.getElementById('dayMacrosBanner').classList.remove('hidden');
    document.getElementById('dayTypeBadge').textContent = dayData.day_type || '';
    document.getElementById('macroKcal').textContent    = m.kcal || '--';
    document.getElementById('macroProtein').textContent = m.protein_g || '--';
    document.getElementById('macroCarbs').textContent   = m.carbs_g || '--';
    document.getElementById('macroFat').textContent     = m.fat_g || '--';
  }

  function nextDay() {
    state.currentDay = (state.currentDay + 1) % 7;
    selectDay(state.currentDay);
  }
  // Training panel title
  const isSport = dayData.is_sport_session || dayData.workout?.is_sport_session;
  const titleEl = document.getElementById('trainingPanelTitle');
  titleEl.innerHTML = isSport
    ? `🏀 Trening Sportowy <span class="sport-badge ml-2">SKILL DAY</span>`
    : '💪 Trening Zaplanowany';

  function loadPlanForDay() {
    const user = state.users[state.currentUser];
    const day = state.days[state.currentDay];
    const dietPlan = user.dietPlan[day] || [];
    const trainingPlan = user.trainingPlan[day] || [];
  // Diet
  renderPlanDiet(dayData.meals || []);

    const dietContainer = document.getElementById('planDietContainer');
    dietContainer.innerHTML = dietPlan.map(meal => `
      <div class="glass-card p-4 cursor-pointer hover:border-cyan-500/50 transition-colors" onclick="openExpandModal('diet', ${meal.id}, '${meal.name}')">
  // Training
  renderPlanTraining(dayData.workout || {}, isSport);
}

// ─────────────────────────────────────────────────────────────────────────────
// TODAY CHECKLIST LOGIC (Premium SaaS Design)
// ─────────────────────────────────────────────────────────────────────────────
function loadTodayPlanChecklist() {
    const todayIdx = (new Date().getDay() + 6) % 7;
    const dayName = getDayName(todayIdx);
    const k = `${getIdentityId()}_${dayName}`;
    const checked = state.dayChecked[k] || {};
    const dayData = state.weeklyPlan?.days?.[todayIdx];

    document.getElementById('todayDayLabel').textContent = new Date().toLocaleDateString('pl-PL',{weekday:'long',day:'numeric',month:'long'});

    const container = document.getElementById('planChecklistContainer');
    if (!dayData) {
        container.innerHTML = '<p class="text-sm text-gray-500 italic text-center py-8">Brak planu na dziś. Wygeneruj go w zakładce Plan.</p>';
        return;
    }

    let html = '';
    // Posiłki
    if (dayData.meals?.length) {
        html += '<p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">🍽️ Posiłki</p>';
        html += dayData.meals.map((m, i) => {
            const isDone = !!checked['meal_'+i];
            return `<div class="flex items-center gap-3 glass p-3 mb-2 transition-all ${isDone?'opacity-50':''}">
                <div class="check-circle ${isDone?'checked':''}" onclick="toggleCheckAndRefresh('meal_${i}', ${todayIdx})"></div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-white ${isDone?'line-through':''}">${m.name}</p>
                    <p class="text-xs text-gray-500">${m.slot} · ${m.macro_target?.kcal || m.kcal_catalog} kcal</p>
                </div>
            </div>`;
        }).join('');
    }

    // Trening
    const workout = dayData.workout || {};
    const exercises = workout.exercises || [];
    if (exercises.length) {
        const isSport = dayData.is_sport_session || workout.is_sport_session;
        html += `<p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 mt-5">${isSport?'🏀 Skill Drille':'💪 Trening'}</p>`;
        html += exercises.map((e, i) => {
            const isDone = !!checked['ex_'+i];
            return `<div class="flex items-center gap-3 glass p-3 mb-2 transition-all ${isDone?'opacity-50':''}">
                <div class="check-circle ${isDone?'checked':''}" onclick="toggleCheckAndRefresh('ex_${i}', ${todayIdx})"></div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-white ${isDone?'line-through':''}">${e.name}</p>
                    <p class="text-xs text-gray-500">${isSport ? e.total_attempts + ' prób' : e.sets + ' serii × ' + e.reps}</p>
                </div>
                ${isSport && !isDone ? `<button onclick="openDrillModal('${esc(e.name)}', ${e.total_attempts}, '${esc(e.description || '')}')" class="btn-sport px-3 py-1 rounded text-[10px]">LOG</button>` : ''}
            </div>`;
        }).join('');
    }

    container.innerHTML = html;
    renderExtraItems();
    updateDayProgress();
}

function toggleCheckAndRefresh(key, dayIdx) {
    const k = `${getIdentityId()}_${getDayName(dayIdx)}`;
    if (!state.dayChecked[k]) state.dayChecked[k] = {};
    state.dayChecked[k][key] = !state.dayChecked[k][key];
    localStorage.setItem('fitai_checked_v3', JSON.stringify(state.dayChecked));
    loadTodayPlanChecklist();
    updateDashboard();
    renderCurrentDay();
}

function updateDayProgress() {
    const todayIdx = (new Date().getDay() + 6) % 7;
    const k = `${getIdentityId()}_${getDayName(todayIdx)}`;
    const checked = state.dayChecked[k] || {};
    const dayData = state.weeklyPlan?.days?.[todayIdx];
    if (!dayData) return;

    const total = (dayData.meals?.length || 0) + (dayData.workout?.exercises?.length || 0);
    const done = Object.values(checked).filter(v => v).length;
    const pct = total > 0 ? Math.round(done / total * 100) : 0;

    document.getElementById('dayProgressLabel').textContent = pct + '%';
    document.getElementById('dayProgressBar').style.width = pct + '%';
    document.getElementById('dayProgressCount').textContent = done + ' / ' + total + ' zadań';
    
    // Sum counters
    let totalKcal = 0, totalProt = 0;
    dayData.meals?.forEach((m, i) => {
        if (checked['meal_'+i]) {
            totalKcal += (m.macro_target?.kcal || m.kcal_catalog || 0);
            totalProt += (m.macro_target?.protein_g || 0);
        }
    });
    document.getElementById('daySumKcal').textContent = totalKcal;
    document.getElementById('daySumProt').textContent = totalProt;
    document.getElementById('dayTrainCount').textContent = exercisesDoneCount(checked);
}

const exercisesDoneCount = (checked) => Object.keys(checked).filter(k => k.startsWith('ex_') && checked[k]).length;

// ── DIET RENDERING ──
function renderPlanDiet(meals) {
  container.innerHTML = meals.map((meal, i) => {
    return `
      &lt;div class="glass p-4 cursor-pointer hover:border-cyan-500/50 transition-colors"
           onclick="openMealModal(${i})">
        <div class="flex justify-between items-start mb-2">
          <p class="font-medium text-white">${meal.name}</p>
          <span class="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-1 rounded">${meal.kcal} kcal</span>
          <div>
            <p class="text-xs text-gray-500 font-medium">${meal.slot || ''}</p>
            <p class="font-medium text-white">${meal.name}</p>
          </div>
          <span class="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-1 rounded">${mt.kcal || meal.kcal_catalog || '--'} kcal</span>
        </div>
        <div class="flex gap-4 text-xs text-gray-400">
          <span>P: ${meal.protein}g</span>
          <span>W: ${meal.carbs}g</span>
          <span>T: ${meal.fat}g</span>
        <div class="flex gap-3 text-xs text-gray-400 flex-wrap">
          ${mt.protein_g ? `<span>P: ${mt.protein_g}g</span>` : ''}
          ${mt.carbs_g   ? `<span>W: ${mt.carbs_g}g</span>`   : ''}
          ${mt.fat_g     ? `<span>T: ${mt.fat_g}g</span>`     : ''}
        </div>
      </div>`;
  }).join('');
}

// ── TRAINING RENDERING ──
function renderPlanTraining(workout, isSport) {
  const container = document.getElementById('planTrainingContainer');
  const exercises = workout.exercises || [];

  if (!exercises.length) {
    container.innerHTML = '<div class="text-center text-gray-500 text-sm italic py-8">Dzień odpoczynku 🛌</div>';
    return;
  }

  if (isSport) {
    // ── SKILL DAY: show drills with total_attempts and progression_tip ──
    container.innerHTML = `
      <div class="mb-4 p-3 sport-card rounded-lg">
        <p class="text-sm font-bold text-orange-300">🏀 ${workout.title || 'Sesja Sportowa'}</p>
        <p class="text-xs text-gray-400 mt-1">Zaznacz wykonanie drilla, aby zapisać wynik i otrzymać wskazówkę progresji.</p>
      </div>
    `).join('');

    const trainingContainer = document.getElementById('planTrainingContainer');
    trainingContainer.innerHTML = trainingPlan.map(exercise => `
      <div class="glass-card p-4 cursor-pointer hover:border-cyan-500/50 transition-colors" onclick="openExpandModal('training', ${exercise.id}, '${exercise.name}')">
        <p class="font-medium text-white mb-2">${exercise.name}</p>
        <div class="flex justify-between items-center">
          <div class="flex gap-4 text-xs text-gray-400">
            <span>${exercise.sets} sety</span>
            <span>${exercise.reps} powtórzeń</span>
            <span>${exercise.weight}kg</span>
      ${exercises.map((ex, i) => `
        <div class="sport-card rounded-xl p-4 space-y-2">
          <div class="flex justify-between items-start">
            <p class="font-medium text-white">${ex.name}</p>
            <span class="text-xs bg-orange-500/20 text-orange-300 px-2 py-1 rounded">
              ${ex.total_attempts} prób
            </span>
          </div>
          <div class="flex gap-1 flex-wrap">
            ${exercise.tags.map(tag => `<span class="text-[10px] bg-white/10 px-2 py-1 rounded text-gray-400">#${tag}</span>`).join('')}
          <p class="text-xs text-gray-400">${ex.description || ex.notes || ''}</p>
          <div class="bg-black/20 rounded-lg p-2 mt-1">
            <p class="text-xs text-orange-300 font-medium">💡 Cel progresji:</p>
            <p class="text-xs text-gray-300 mt-0.5">${ex.progression_tip || ex.how_to || ''}</p>
          </div>
          <button onclick="openDrillModal('${esc(ex.name)}', ${ex.total_attempts}, '${esc(ex.description || '')}')"
                  class="btn-sport w-full py-2 rounded-lg text-sm font-bold mt-1">
            ✅ Zapisz wynik drilla
          </button>
        </div>
      `).join('')}`;
  } else {
    // ── STANDARD GYM SESSION ──
    const fmtLabel = workout.workout_format || 'standard';
    const fmtBadge = fmtLabel !== 'standard'
      ? `<span class="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded ml-2">${fmtLabel.toUpperCase()}</span>` : '';

    container.innerHTML = `
      <div class="mb-3 flex items-center flex-wrap gap-2">
        <p class="text-sm font-bold text-gray-300">${workout.title || 'Sesja'}</p>
        ${fmtBadge}
        ${workout.location ? `<span class="text-xs text-gray-500">📍 ${workout.location}</span>` : ''}
        ${workout.duration_limit_min ? `<span class="text-xs text-gray-500">⏱ ${workout.duration_limit_min} min</span>` : ''}
      </div>
    `).join('') || '<div class="text-center text-gray-500 text-sm italic py-8">Brak zaplanowanych ćwiczeń</div>';
      ${exercises.map((ex, i) => {
        const superset = ex.superset ? `<span class="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded">${ex.superset}</span>` : '';
        return `
          <div class="glass-card p-4 cursor-pointer hover:border-cyan-500/50 transition-colors"
          <div class="glass p-4 cursor-pointer hover:border-cyan-500/50 transition-colors"
               onclick="openExerciseModal(${i})">
            <div class="flex justify-between items-start mb-2">
              <p class="font-medium text-white">${ex.name}</p>
              <div class="flex gap-1 items-center">${superset}</div>
            </div>
            <div class="flex gap-4 text-xs text-gray-400">
              <span>${ex.sets} serii</span>
              <span>${ex.reps} powtórzeń</span>
            </div>
            ${ex.notes ? `<p class="text-xs text-gray-500 mt-1 italic">${ex.notes}</p>` : ''}
          </div>`;
      }).join('')}`;
  }
}

  // ============ EXPAND MODAL ============
  function openExpandModal(type, itemId, name) {
    const modal = document.getElementById('expandModal');
    const title = document.getElementById('expandTitle');
    const content = document.getElementById('expandContent');
// ─────────────────────────────────────────────────────────────────────────────
// MODALS
// ─────────────────────────────────────────────────────────────────────────────

    title.textContent = name;
    state.expandedItem = { type, itemId, name };
// Meal detail modal (reuses expandModal)
function openMealModal(mealIndex) {
  const dayData = state.weeklyPlan?.days?.[state.currentDay];
  if (!dayData) return;
  const meal = dayData.meals[mealIndex];
  if (!meal) return;

    if (type === 'diet') {
      content.innerHTML = `
        <div>
          <h6 class="font-bold text-white mb-2">Makroskładniki</h6>
          <div class="grid grid-cols-3 gap-4 text-center">
            <div class="bg-white/5 p-3 rounded">
              <p class="text-xs text-gray-400">Białko</p>
              <p class="text-lg font-bold text-cyan-400">20g</p>
            </div>
            <div class="bg-white/5 p-3 rounded">
              <p class="text-xs text-gray-400">Węgle</p>
              <p class="text-lg font-bold text-yellow-400">50g</p>
            </div>
            <div class="bg-white/5 p-3 rounded">
              <p class="text-xs text-gray-400">Tłuszcz</p>
              <p class="text-lg font-bold text-orange-400">8g</p>
            </div>
          </div>
        </div>
        <div>
          <h6 class="font-bold text-white mb-2">Sposób przygotowania</h6>
          <ol class="list-decimal list-inside text-sm space-y-1 text-gray-400">
            <li>Odparuj w wodzie z odrobiną soli</li>
            <li>Dodaj przyprawy: czosnek, pieprz, zioła</li>
            <li>Smażyć na oliwie przez 3 minuty</li>
          </ol>
        </div>
      `;
    } else if (type === 'training') {
      content.innerHTML = `
        <div>
          <h6 class="font-bold text-white mb-2">Instrukcja Techniki</h6>
          <p class="text-sm text-gray-400 leading-relaxed">1. Ustaw sztangę na wysokości klatki piersiowej. 2. Wciągnij łopatkę w dół i do tyłu. 3. Wciśnij sztangę w linii prostej ponad klatką. 4. Powoli opuszczaj kontrolując ruch.</p>
        </div>
        <div>
          <h6 class="font-bold text-white mb-2">Na co pomaga</h6>
          <p class="text-sm text-gray-400">Buduje mięśnie klatki piersiowej, przedniej części ramienia i tricepsów. Świetne dla budowania masy.</p>
        </div>
      `;
    }
  state.expandedItem = { type: 'meal', index: mealIndex, data: meal };
  const mt = meal.macro_target || {};
  document.getElementById('expandTitle').textContent = meal.name;
  document.getElementById('expandContent').innerHTML = `
    <p class="text-xs text-gray-500">${meal.slot || ''}</p>
    <div class="grid grid-cols-4 gap-3 text-center mt-2">
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Kcal</p><p class="text-lg font-bold text-cyan-400">${mt.kcal || meal.kcal_catalog || '--'}</p></div>
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Białko</p><p class="text-lg font-bold text-green-400">${mt.protein_g || '--'}g</p></div>
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Węgle</p><p class="text-lg font-bold text-yellow-400">${mt.carbs_g || '--'}g</p></div>
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Tłuszcz</p><p class="text-lg font-bold text-orange-400">${mt.fat_g || '--'}g</p></div>
    </div>
    ${meal.alternatives?.length ? `
    <div class="mt-3">
      <p class="text-sm font-bold text-white mb-2">Alternatywy z katalogu:</p>
      <div class="space-y-1">
        ${meal.alternatives.map((a,i) => `
          <button onclick="swapMeal(${mealIndex},${i})" class="w-full text-left text-sm p-2 bg-white/5 rounded hover:bg-white/10 transition-colors text-gray-300">
            ${a.name} <span class="text-gray-500 text-xs">${a.kcal} kcal</span>
          </button>`).join('')}
      </div>
    </div>` : ''}`;
  document.getElementById('expandActions').innerHTML = `
    <button onclick="closeExpandModal()" class="flex-1 btn-secondary py-2 rounded-lg font-medium">Zamknij</button>`;
  document.getElementById('expandModal').classList.remove('hidden');
}

    modal.classList.remove('hidden');
  }
// Exercise detail modal
function openExerciseModal(exIndex) {
  const dayData = state.weeklyPlan?.days?.[state.currentDay];
  if (!dayData) return;
  const ex = dayData.workout?.exercises?.[exIndex];
  if (!ex) return;

  function closeExpandModal() {
    document.getElementById('expandModal').classList.add('hidden');
  }
  state.expandedItem = { type: 'exercise', index: exIndex, data: ex };
  document.getElementById('expandTitle').textContent = ex.name;
  document.getElementById('expandContent').innerHTML = `
    <div class="grid grid-cols-2 gap-3">
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Serie</p><p class="text-xl font-bold text-cyan-400">${ex.sets}</p></div>
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Powtórzenia</p><p class="text-xl font-bold text-cyan-400">${ex.reps}</p></div>
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Serie</p><p class="text-xl font-bold text-cyan-400">${ex.sets || '--'}</p></div>
      <div class="bg-white/5 p-3 rounded"><p class="text-xs text-gray-400">Powtórzenia</p><p class="text-xl font-bold text-cyan-400">${ex.reps || '--'}</p></div>
    </div>
    ${ex.how_to ? `<div class="mt-3"><p class="text-sm font-bold text-white mb-1">Technika:</p><p class="text-sm text-gray-400 leading-relaxed">${ex.how_to}</p></div>` : ''}
    ${ex.notes ? `<div class="mt-2 bg-white/5 p-3 rounded"><p class="text-xs text-gray-400 italic">${ex.notes}</p></div>` : ''}
    ${ex.progression ? `<div class="mt-3 bg-cyan-500/10 border border-cyan-500/30 p-3 rounded-lg">
      <p class="text-xs font-bold text-cyan-400 mb-1">💡 Progresja AI:</p>
      <p class="text-xs text-gray-300">${ex.progression.reason || ''}</p>
      ${ex.progression.suggested_weight_kg ? `<p class="text-xs text-cyan-300 mt-1">Sugerowany ciężar: <strong>${ex.progression.suggested_weight_kg} kg × ${ex.progression.suggested_reps} pow.</strong></p>` : ''}
    </div>` : ''}
    ${ex.alternatives?.length ? `
    <div class="mt-3">
      <p class="text-sm font-bold text-white mb-2">Zamienniki:</p>
      <div class="space-y-1">
        ${ex.alternatives.map((a,i) => `
          <button onclick="swapExercise(${exIndex},${i})" class="w-full text-left text-sm p-2 bg-white/5 rounded hover:bg-white/10 transition-colors text-gray-300">
            ${a.name}
          </button>`).join('')}
      </div>
    </div>` : ''}`;
  document.getElementById('expandActions').innerHTML = `
    <button onclick="closeExpandModal()" class="flex-1 btn-secondary py-2 rounded-lg font-medium">Zamknij</button>`;
  document.getElementById('expandModal').classList.remove('hidden');
}

  function swapItem() {
    if (!state.expandedItem) return;
    alert(`Wymiana ${state.expandedItem.name} - AI zaproponuje alternatywy (funkcja w opracowaniu)`);
function closeExpandModal() { document.getElementById('expandModal').classList.add('hidden'); }

async function swapMeal(mealIndex, altIndex) {
  try {
    const data = await apiFetch(`/app/plan/${getIdentityId()}/swap`, {
      method: 'POST',
      body: JSON.stringify({ day_index: state.currentDay, section: 'meal', item_index: mealIndex, alternative_index: altIndex }),
    });
    state.weeklyPlan = data.plan;
    closeExpandModal();
    renderCurrentDay();
    showToast('Posiłek zamieniony!'); loadTodayPlanChecklist();
  } catch(e) { showToast('Błąd zamiany: ' + e.message, 'error'); }
}

async function swapExercise(exIndex, altIndex) {
  try {
    const data = await apiFetch(`/app/plan/${getIdentityId()}/swap`, {
      method: 'POST',
      body: JSON.stringify({ day_index: state.currentDay, section: 'exercise', item_index: exIndex, alternative_index: altIndex }),
    });
    state.weeklyPlan = data.plan;
    closeExpandModal();
    renderCurrentDay();
    showToast('Ćwiczenie zamienione!'); loadTodayPlanChecklist();
  } catch(e) { showToast('Błąd zamiany: ' + e.message, 'error'); }
}

// ─────────────────────────────────────────────────────────────────────────────
// DRILL RESULT MODAL
// ─────────────────────────────────────────────────────────────────────────────
function openDrillModal(drillName, totalAttempts, description) {
  state.activeDrillName  = drillName;
  state.activeDrillTotal = totalAttempts;
  document.getElementById('drillModalTitle').textContent = drillName;
  document.getElementById('drillModalDesc').textContent  = description;
  document.getElementById('drillTotal').value   = totalAttempts;
  document.getElementById('drillSuccess').value = '';
  document.getElementById('drillRpe').value     = 5;
  document.getElementById('rpeValue').textContent = '5';
  document.getElementById('drillNotes').value   = '';
  document.getElementById('accuracyPreview').classList.add('hidden');
  document.getElementById('drillSubmitStatus').classList.add('hidden');
  document.getElementById('drillModal').classList.remove('hidden');
}

function closeDrillModal() { document.getElementById('drillModal').classList.add('hidden'); }

// Live accuracy preview
document.addEventListener('input', (e) => {
  if (e.target.id === 'drillSuccess' || e.target.id === 'drillTotal') {
    const s = parseInt(document.getElementById('drillSuccess').value) || 0;
    const t = parseInt(document.getElementById('drillTotal').value)   || 1;
    const pct = Math.min(100, Math.round(s / t * 100));
    document.getElementById('accuracyValue').textContent = pct + '%';
    document.getElementById('accuracyBar').style.width   = pct + '%';
    document.getElementById('accuracyPreview').classList.remove('hidden');
    // color feedback
    document.getElementById('accuracyValue').className = pct >= 70
      ? 'text-2xl font-bold text-green-400'
      : pct >= 50
        ? 'text-2xl font-bold text-yellow-400'
        : 'text-2xl font-bold text-red-400';
  }
});

  // ============ MY DAY LOGIC ============
  function showManualForm(type) {
    state.manualFormType = type;
    const container = document.getElementById('manualFormContainer');
    const title = document.getElementById('manualFormTitle');
    
    title.textContent = type === 'diet' ? 'Dodaj Posiłek' : 'Dodaj Trening';
    container.classList.remove('hidden');
async function submitDrillResult() {
  const success = parseInt(document.getElementById('drillSuccess').value);
  const total   = parseInt(document.getElementById('drillTotal').value);
  const rpe     = parseInt(document.getElementById('drillRpe').value);
  const notes   = document.getElementById('drillNotes').value;
  const statusEl = document.getElementById('drillSubmitStatus');

    // Clear form
    document.getElementById('entryName').value = '';
    document.getElementById('entryProtein').value = '';
    document.getElementById('entryCarbs').value = '';
    document.getElementById('entryFat').value = '';
  if (isNaN(success) || isNaN(total) || total < 1) {
    statusEl.textContent = '❌ Wypełnij liczbę trafień i prób.';
    statusEl.className   = 'text-sm text-center mt-3 text-red-400';
    statusEl.classList.remove('hidden');
    return;
  }

  function closeManualForm() {
    document.getElementById('manualFormContainer').classList.add('hidden');
  try {
    const data = await apiFetch(`/app/drill-result/${getIdentityId()}`, {
      method: 'POST',
      body: JSON.stringify({
        drill_name: state.activeDrillName,
        success_count: success,
        total_attempts: total,
        rpe,
        notes,
      }),
    });

    const prog = data.progression || {};
    closeDrillModal();
    showProgressionToast(state.activeDrillName, data.result?.accuracy_pct, prog); loadTodayPlanChecklist();
  } catch(e) {
    statusEl.textContent = '❌ Błąd: ' + e.message;
    statusEl.className   = 'text-sm text-center mt-3 text-red-400';
    statusEl.classList.remove('hidden');
  }
}

  function addFromPlan(type) {
    const user = state.users[state.currentUser];
    const container = type === 'diet' ? document.getElementById('dietLogContainer') : document.getElementById('trainingLogContainer');
function showProgressionToast(name, accuracy, prog) {
  const toast = document.createElement('div');
  toast.className = 'fixed bottom-6 right-6 glass sport-card p-5 max-w-sm z-[150] animate-[slideUpFade_.4s_ease-out]';
  toast.innerHTML = `
    <div class="flex justify-between items-start mb-2">
      <p class="font-bold text-white">📊 Wynik zapisany!</p>
      <button onclick="this.closest('div').remove()" class="text-gray-400 hover:text-white ml-4">✕</button>
    </div>
    <p class="text-sm text-orange-300 font-medium">${name}</p>
    <p class="text-sm text-gray-300 mt-1">Skuteczność: <strong class="text-cyan-400">${accuracy ?? '--'}%</strong></p>
    ${prog.reason ? `<div class="mt-3 bg-black/20 rounded-lg p-3">
      <p class="text-xs text-gray-500 font-bold uppercase mb-1">Progresja AI</p>
      <p class="text-xs text-gray-300">${prog.reason}</p>
      ${prog.suggested_attempts ? `<p class="text-xs text-cyan-400 mt-1 font-bold">Następna sesja: ${prog.suggested_attempts} prób</p>` : ''}
    </div>` : ''}`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 8000);
}

    const mockItems = {
      diet: [
        { name: 'Kurczak z ryżem', protein: 35, carbs: 50, fat: 5, kcal: 450 },
        { name: 'Sałatka grecka', protein: 15, carbs: 20, fat: 12, kcal: 250 }
      ],
      training: [
        { name: 'Pompki 3x20', sets: 3, reps: 20 },
        { name: 'Przysiad ze sztangą 4x6', sets: 4, reps: 6, weight: 120 }
      ]
    };
// ─────────────────────────────────────────────────────────────────────────────
// DAY CAROUSEL
// ─────────────────────────────────────────────────────────────────────────────
function renderDayCarousel() {
  const carousel = document.getElementById('dayCarousel');
  carousel.innerHTML = state.daysShort.map((day, i) => {
    const isSport = state.weeklyPlan?.days?.[i]?.is_sport_session;
    return `
      <button onclick="selectDay(${i})" class="day-carousel-item px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${i === state.currentDay ? (isSport ? 'btn-sport' : 'btn-neon') : 'btn-secondary'}">
        ${day}${isSport ? ' 🏀' : ''}
      </button>`;
  }).join('');
}

    const item = mockItems[type][0];
    const html = type === 'diet'
      ? `<div class="glass-card p-3 flex justify-between items-start"><div><p class="text-white font-medium">${item.name}</p><p class="text-xs text-gray-500">P: ${item.protein}g | W: ${item.carbs}g | T: ${item.fat}g</p></div><button onclick="this.parentElement.parentElement.remove()" class="text-red-400 text-sm">✕</button></div>`
      : `<div class="glass-card p-3 flex justify-between items-start"><div><p class="text-white font-medium">${item.name}</p></div><button onclick="this.parentElement.parentElement.remove()" class="text-red-400 text-sm">✕</button></div>`;
function selectDay(dayIndex) {
  state.currentDay = dayIndex;
  document.getElementById('currentDay').textContent = state.daysShort[dayIndex];
  renderDayCarousel();
  if (state.weeklyPlan) renderCurrentDay();
}

    container.innerHTML = html;
  }
function prevDay() { state.currentDay = (state.currentDay - 1 + 7) % 7; selectDay(state.currentDay); }
function nextDay() { state.currentDay = (state.currentDay + 1) % 7; selectDay(state.currentDay); }

  document.getElementById('manualEntryForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('entryName').value;
    const protein = document.getElementById('entryProtein').value;
    const carbs = document.getElementById('entryCarbs').value;
    const fat = document.getElementById('entryFat').value;
// ─────────────────────────────────────────────────────────────────────────────
// SPORT CONFIG  (Profile → Sport tab)
// ─────────────────────────────────────────────────────────────────────────────
function onSportFocusChange(presetSpec, presetDays) {
  const val     = document.getElementById('sportFocus').value;
  const specSec = document.getElementById('sportSpecSection');
  const daysSec = document.getElementById('sportDaysSection');

    const container = state.manualFormType === 'diet' ? document.getElementById('dietLogContainer') : document.getElementById('trainingLogContainer');
    const html = state.manualFormType === 'diet'
      ? `<div class="glass-card p-3 flex justify-between items-start"><div><p class="text-white font-medium">${name}</p><p class="text-xs text-gray-500">P: ${protein}g | W: ${carbs}g | T: ${fat}g</p></div><button onclick="this.parentElement.parentElement.remove()" class="text-red-400 text-sm">✕</button></div>`
      : `<div class="glass-card p-3 flex justify-between items-start"><div><p class="text-white font-medium">${name}</p></div><button onclick="this.parentElement.parentElement.remove()" class="text-red-400 text-sm">✕</button></div>`;
  if (!val) {
    specSec.classList.add('hidden');
    daysSec.classList.add('hidden');
    return;
  }
  specSec.classList.remove('hidden');
  daysSec.classList.remove('hidden');

    container.innerHTML += html;
    closeManualForm();
  });
  // Render spec options — używamy getSportSpecs() zamiast SPORT_SPECS[val]
  // żeby "Koszykówka" i "koszykówka" były traktowane tak samo (toLowerCase)
  const specs  = getSportSpecs(val);
  const optEl  = document.getElementById('sportSpecOptions');
  optEl.innerHTML = specs.map(s => `
    <label class="flex items-center gap-2 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-orange-500/10 border border-white/5 hover:border-orange-500/30 transition-all">
      <input type="radio" name="sportSpec" value="${s.value}" class="accent-orange-400">
      <span class="text-white font-medium">${s.label}</span>
    </label>`).join('');

  // ============ PROFILE HELPERS ============
  function renderGoalsCheckboxes() {
    const container = document.getElementById('goalsCheckboxes');
    container.innerHTML = mockGoals.map(goal => `
      <label class="flex items-center gap-3 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors">
        <input type="checkbox" class="goal-checkbox" value="${goal.id}" />
        <span class="text-white font-medium">${goal.emoji} ${goal.label}</span>
      </label>
    `).join('');
  if (presetSpec) {
    const rb = document.querySelector(`input[name="sportSpec"][value="${presetSpec}"]`);
    if (rb) rb.checked = true;
  }

  function renderEquipmentCheckboxes() {
    const container = document.getElementById('equipmentCheckboxes');
    container.innerHTML = mockEquipment.map(equip => `
      <label class="flex items-center gap-3 p-2 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors">
        <input type="checkbox" class="equipment-checkbox" value="${equip.id}" checked />
        <span class="text-white font-medium">${equip.emoji} ${equip.label}</span>
      </label>
    `).join('');
  // Mark preset training days
  if (presetDays?.length) {
    presetDays.forEach(d => {
      const cb = document.querySelector(`.sport-day-checkbox[value="${d}"]`);
      if (cb) cb.checked = true;
    });
  }
}

  function saveGoals() {
    const selected = Array.from(document.querySelectorAll('.goal-checkbox:checked')).map(cb => cb.value);
    state.users[state.currentUser].goals = selected;
    alert('Cele zostały zaktualizowane!');
function renderSportDaysCheckboxes() {
  const container = document.getElementById('sportDaysCheckboxes');
  container.innerHTML = state.days.map(day => `
    <label class="flex flex-col items-center gap-1 p-2 bg-white/5 rounded-lg cursor-pointer hover:bg-orange-500/10 border border-white/5 hover:border-orange-500/30 transition-all">
      <input type="checkbox" class="sport-day-checkbox accent-orange-400" value="${day}">
      <span class="text-xs text-gray-300">${day.slice(0,3)}</span>
    </label>`).join('');
}

async function saveSportConfig() {
  const sportFocus = document.getElementById('sportFocus').value;
  const specEl     = document.querySelector('input[name="sportSpec"]:checked');
  const sportSpec  = specEl ? specEl.value : '';
  const sportDays  = Array.from(document.querySelectorAll('.sport-day-checkbox:checked')).map(cb => cb.value);
  const statusEl   = document.getElementById('sportStatus');

  statusEl.textContent = 'Zapisuję…';
  try {
    await apiFetch(`/app/sport-config/${getIdentityId()}`, {
      method: 'POST',
      body: JSON.stringify({ sport_focus: sportFocus, sport_specialization: sportSpec, sport_training_days: sportDays }),
    });
    state.weeklyPlan = null; // invalidate cached plan
    statusEl.textContent = '✅ Zapisano! Plan zostanie wygenerowany na nowo.';
    statusEl.className   = 'text-sm text-green-400';
  } catch(e) {
    statusEl.textContent = '❌ ' + e.message;
    statusEl.className   = 'text-sm text-red-400';
  }
  setTimeout(() => { statusEl.textContent = ''; }, 5000);
}

  function savePreferences() {
    const equipment = Array.from(document.querySelectorAll('.equipment-checkbox:checked')).map(cb => cb.value);
    const excluded = document.getElementById('excludedFoods').value.split(',').map(s => s.trim()).filter(s => s);
    state.users[state.currentUser].equipment = equipment;
    state.users[state.currentUser].excludedFoods = excluded;
    alert('Preferencje zostały zaktualizowane!');
// ─────────────────────────────────────────────────────────────────────────────
// CHECK-IN
// ─────────────────────────────────────────────────────────────────────────────
document.getElementById('checkinForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const statusEl = document.getElementById('checkinStatus');
  statusEl.textContent = 'Wysyłam…';
  try {
    const res = await apiFetch(`/app/checkin/${getIdentityId()}`, {
      method: 'POST',
      body: JSON.stringify({
        food:    document.getElementById('checkinFood').value,
        workout: document.getElementById('checkinWorkout').value,
        mood:    document.getElementById('checkinMood').value,
        weight:  parseFloat(document.getElementById('checkinWeight').value) || null,
      }),
    });
    statusEl.textContent = '✅ Check-in zapisany! Streak: ' + (res.streak_days || 0) + ' dni';
    statusEl.className   = 'text-sm text-green-400';
    document.getElementById('kpiStreak').textContent = (res.streak_days || 0) + ' dni';
    e.target.reset();
    // Refresh profile kpis
    await loadProfile();
  } catch(err) {
    statusEl.textContent = '❌ ' + err.message;
    statusEl.className   = 'text-sm text-red-400';
  }
});

  // ============ UTILITY FUNCTIONS ============
  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    alert('Skopiowano: ' + text);
// ─────────────────────────────────────────────────────────────────────────────
// PROFILE SAVE
// ─────────────────────────────────────────────────────────────────────────────
document.getElementById('userDataForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const statusEl = document.getElementById('profileStatus');
  statusEl.textContent = 'Zapisuję…';
  const payload = {
    identity_id:  getIdentityId(),
    email:        state.profile?.email || '',
    name:         document.getElementById('firstName').value,
    age:          parseInt(document.getElementById('age').value) || 0,
    height:       parseInt(document.getElementById('height').value) || 0,
    weight:       parseFloat(document.getElementById('weight').value) || 0,
    target_weight: parseFloat(document.getElementById('targetWeight').value) || 0,
    gender:       document.getElementById('gender').value,
    allergies:    document.getElementById('allergies').value,
    goal:         state.profile?.goal || 'Zdrowie i kondycja',
    frequency:    state.profile?.frequency || '3-4 razy w tygodniu',
    diet:         state.profile?.diet || 'Zbilansowana',
  };
  try {
    await apiFetch('/app/onboarding', { method: 'POST', body: JSON.stringify(payload) });
    statusEl.textContent = '✅ Profil zapisany!';
    statusEl.className   = 'text-sm text-green-400';
    document.getElementById('greetingName').textContent = payload.name;
    await loadProfile();
    state.weeklyPlan = null; // Nowe dane → nowy plan
  } catch(err) {
    statusEl.textContent = '❌ ' + err.message;
    statusEl.className   = 'text-sm text-red-400';
  }
  setTimeout(() => { statusEl.textContent = ''; }, 5000);
});

  // Mobile menu toggle
  document.getElementById('mobileMenuBtn')?.addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('mobile-open');
// ─────────────────────────────────────────────────────────────────────────────
// GOALS & PREFERENCES (local for now)
// ─────────────────────────────────────────────────────────────────────────────
function renderGoalsCheckboxes() {
  document.getElementById('goalsCheckboxes').innerHTML = mockGoals.map(g => `
    <label class="flex items-center gap-3 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors">
      <input type="checkbox" class="goal-checkbox accent-cyan-400" value="${g.id}">
      <span class="text-white font-medium">${g.emoji} ${g.label}</span>
    </label>`).join('');
}

function renderEquipmentCheckboxes() {
  document.getElementById('equipmentCheckboxes').innerHTML = mockEquipment.map(eq => `
    <label class="flex items-center gap-3 p-2 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors">
      <input type="checkbox" class="equipment-checkbox accent-cyan-400" value="${eq.id}" checked>
      <span class="text-white font-medium">${eq.emoji} ${eq.label}</span>
    </label>`).join('');
}

function saveGoals() {
  const selected = Array.from(document.querySelectorAll('.goal-checkbox:checked')).map(cb => cb.value);
  showToast('Cele zaktualizowane: ' + selected.join(', '));
}

function savePreferences() {
  const equipment = Array.from(document.querySelectorAll('.equipment-checkbox:checked')).map(cb => cb.value);
  const excluded  = document.getElementById('excludedFoods').value.split(',').map(s => s.trim()).filter(s => s);
  showToast('Preferencje zapisane lokalnie.');
}

// ─────────────────────────────────────────────────────────────────────────────
// MY DAY – manual entry
// ─────────────────────────────────────────────────────────────────────────────
function openAddOtherModal(type) {
  state.manualFormType = type;
  document.getElementById('addOtherTitle').textContent = type === 'diet' ? '🍽️ Dodaj posiłek' : '💪 Dodaj trening';
  document.getElementById('otherDietFields').classList.toggle('hidden', type !== 'diet');
  document.getElementById('otherTrainingFields').classList.toggle('hidden', type !== 'training');
  ['otherName','otherKcal','otherProtein','otherCarbs','otherFat','otherDuration'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  document.getElementById('addOtherModal').classList.remove('hidden');
}

  // Logout
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    if (confirm('Wylogować się?')) {
      state.currentUser = null;
      alert('Wylogowano!');
function closeAddOtherModal() { document.getElementById('addOtherModal').classList.add('hidden'); }

function submitAddOther() {
    const name = document.getElementById('otherName').value.trim();
    if (!name) return;
    const id = getIdentityId();
    if (!state.extraItems[id]) state.extraItems[id] = [];
    
    const type = state.manualFormType;
    const item = { type, name, ts: Date.now() };
    if (type === 'diet') {
        item.kcal = parseInt(document.getElementById('otherKcal').value) || 0;
        item.protein = parseInt(document.getElementById('otherProtein').value) || 0;
    } else {
        item.duration = document.getElementById('otherDuration').value || '';
    }
  });
    state.extraItems[id].push(item);
    localStorage.setItem('fitai_extras_v3', JSON.stringify(state.extraItems));
    closeAddOtherModal();
    loadTodayPlanChecklist();
    updateDayProgress();
}

  // User form submission
  document.getElementById('userDataForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const user = state.users[state.currentUser];
    user.name = document.getElementById('firstName').value || user.name;
    user.age = parseInt(document.getElementById('age').value) || user.age;
    user.height = parseInt(document.getElementById('height').value) || user.height;
    user.weight = parseFloat(document.getElementById('weight').value) || user.weight;
    user.targetWeight = parseFloat(document.getElementById('targetWeight').value) || user.targetWeight;
    user.gender = document.getElementById('gender').value || user.gender;
    user.allergies = document.getElementById('allergies').value || '';
function renderExtraItems() {
    const extras = state.extraItems[getIdentityId()] || [];
    const container = document.getElementById('extraItemsContainer');
    if (!extras.length) { container.innerHTML = ''; return; }
    container.innerHTML = '<p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 mt-2">➕ Własne wpisy</p>'
        + extras.map((ex, i) => `<div class="flex items-center gap-3 glass p-3 mb-2">
            <span class="text-lg">${ex.type==='diet'?'🍽️':'💪'}</span>
            <div class="flex-1"><p class="text-sm font-medium text-white">${ex.name}</p></div>
            <button onclick="removeExtraItem(${i})" class="text-red-400 text-sm">✕</button>
        </div>`).join('');
}

function removeExtraItem(idx) {
    state.extraItems[getIdentityId()].splice(idx, 1);
    localStorage.setItem('fitai_extras_v3', JSON.stringify(state.extraItems));
    loadTodayPlanChecklist();
}

function addFromPlan(type) {
    const todayIdx = (new Date().getDay() + 6) % 7;
    const dayData = state.weeklyPlan?.days?.[todayIdx];
    if (!dayData) return;
    const k = `${getIdentityId()}_${getDayName(todayIdx)}`;
    if (!state.dayChecked[k]) state.dayChecked[k] = {};
    
    alert('Dane zostały zaktualizowane!');
    document.getElementById('greetingName').textContent = user.name;
    if (type === 'diet') {
        dayData.meals.forEach((_, i) => state.dayChecked[k]['meal_'+i] = true);
    } else {
        dayData.workout.exercises.forEach((_, i) => state.dayChecked[k]['ex_'+i] = true);
    }
    localStorage.setItem('fitai_checked_v3', JSON.stringify(state.dayChecked));
    loadTodayPlanChecklist(); updateDashboard();
}

// ─────────────────────────────────────────────────────────────────────────────
// CHARTS
// ─────────────────────────────────────────────────────────────────────────────
function initCharts() {
  const ctx = document.getElementById('consistencyChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: state.daysShort,
      datasets: [{
        label: 'Spójność (%)',
        data: [80,85,70,90,75,92,88],
        backgroundColor: 'rgba(0,229,255,0.2)',
        borderColor: '#00e5ff', borderWidth:2, borderRadius:8,
      }]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins: { legend:{ display:false } },
      scales: {
        y:{ beginAtZero:true, max:100, grid:{ color:'rgba(255,255,255,0.05)' }, ticks:{ color:'#64748b' } },
        x:{ grid:{ display:false }, ticks:{ color:'#64748b' } },
      }
    }
  });
}

  // ============ STARTUP ============
  window.addEventListener('load', initApp);
  window.addEventListener('beforeunload', () => {
    // Save state to localStorage (in real app, save to backend)
    localStorage.setItem('fitai_state', JSON.stringify(state));
  });
// ─────────────────────────────────────────────────────────────────────────────
// TOAST
// ─────────────────────────────────────────────────────────────────────────────
function showToast(msg, type='success') {
  const toast = document.createElement('div');
  toast.className = `fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl text-sm font-medium z-50 ${
    type === 'error' ? 'bg-red-900/80 text-red-200 border border-red-500/40' : 'bg-[#00e5ff]/10 text-cyan-300 border border-cyan-500/30'
  } backdrop-blur-xl`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ─────────────────────────────────────────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────────────────────────────────────────
function esc(s) { return String(s).replace(/'/g,"\\u0027").replace(/"/g,"\\u0022"); }

function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
  showToast('Skopiowano: ' + text);
}

// Mobile menu
document.getElementById('mobileMenuBtn')?.addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('mobile-open');
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', () => {
  if (confirm('Wylogować się?')) showToast('Wylogowano.');
});

// ─────────────────────────────────────────────────────────────────────────────
// STARTUP
// ─────────────────────────────────────────────────────────────────────────────
window.addEventListener('load', initApp);
</script>

<!-- PWA Service Worker Registration -->
<!-- PWA Service Worker -->
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      console.log('Service Worker not available');
    });
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
</script>

</body>
</html>
"""

# ============ SAVE HTML TO FILE ============
# ============ SAVE ============
import os

try:
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ FitAI SaaS Platform - Premium Dashboard wygenerowany!")
    print("📄 Plik: index.html")
    print("🎨 Cechy: Glassmorphism, Multi-user, Animations, PWA-ready")
    print("\n📋 Implementowane funkcje:")
    print("   ✓ 5 głównych zakładek: Home, My Day, Plan, Profile, Contact")
    print("   ✓ Modern Tech Noir design z gradientami i Glassmorphism")
    print("   ✓ Zaawansowane animacje (Slide-up, Spring, Pulse)")
    print("   ✓ Multi-user support z przełączaniem użytkowników")
    print("   ✓ Interaktywny dzień karuzelowy z przyciskami strzałek")
    print("   ✓ Expand modal dla szczegółów posiłków/ćwiczeń")
    print("   ✓ Funkcjonalność zamienników (AI suggestions)")
    print("   ✓ Neonowe alerty dla brakujących makroskładników")
    print("   ✓ Profile z 4 podtabami (Dane, Cele, Preferencje, Płatności)")
    print("   ✓ Kontakt z Discord i Email (z kopią do schowka)")
    print("   ✓ PWA manifest i Service Worker ready")
    print("   ✓ Responsywny design (Mobile-First)")
    print("   ✓ Offline support gotowy")
    print("✅ FitAI v3.0 — generate_html_complete.py → index.html")
    print("\n📋 Zaimplementowane funkcje:")
    print("   ✓ Zakładka Sport: sport_focus dropdown, spec radiobuttony, checklisty dni")
    print("   ✓ POST /app/sport-config/{id} przy zapisie konfiguracji sportowej")
    print("   ✓ POST /app/plan/{id}/generate – plan pobierany z FastAPI (nie lokalnie)")
    print("   ✓ Skill Day: karty drilli z total_attempts + progression_tip + neon-orange UI")
    print("   ✓ Modal logowania wyników drilla (trafienia, próby, RPE 1-10, notatki)")
    print("   ✓ POST /app/drill-result/{id} – zapis wyniku + toast z sugestią progresji AI")
    print("   ✓ Autoregulacja: banner wyświetlany gdy mood wyzwolił recovery/low-intensity")
    print("   ✓ Carb Cycling macros per-day wyświetlane w pasku nad planem")
    print("   ✓ POST /app/checkin/{id} – check-in z mood (zasila autoregulację)")
    print("   ✓ Zamiana posiłku/ćwiczenia przez /app/plan/{id}/swap")
    print("   ✓ pingApi() – status połączenia z API w sidebarze")
    print("   ✓ Zachowany styl Tech Noir / Glassmorphism + sport-card neon-orange")
except Exception as e:
    print(f"❌ Błąd: {e}")