/**
 * FitAI — Service Worker v3.2.1
 * ─────────────────────────────────────────────────────────────────────────────
 * Strategie cachowania:
 *   • HTML (nawigacja)        → Network-First + fallback do cache
 *   • API JSON /app/* dane    → Network-First (timeout 4 s) + fallback do cache
 *   • AI / export endpointy   → Network-Only (nigdy nie cache'uj)
 *   • Fonty / CDN scripts     → Cache-First + Stale-While-Revalidate w tle
 *   • Obrazki / ikony         → Cache-First + inteligentny fallback
 *
 * Aktualizacje:
 *   • skipWaiting()  w install  → nowy SW aktywuje się natychmiast
 *   • clients.claim() w activate → przejmuje wszystkie otwarte karty
 *   • postMessage SW_UPDATED    → index.html pokazuje toast "Nowa wersja"
 *   • Zmień CACHE_VERSION przy każdym deploymencie
 *
 * Zmiany v3.1.0 → v3.2.0:
 *   • networkFirstJSON: dodany timeout 4 s (zapobiega zamrożeniu UI na LTE)
 *   • networkFirstJSON: naprawiony non-OK passthrough (401/403 dociera do UI)
 *   • networkFirstJSON: X-Cache-Age header (ile sekund ma cachedResponse)
 *   • jsonOfflineResponse: przyjmuje parametr reason (timeout/error/no-cache)
 *   • SHELL_ASSETS: dodano lucide-icons, animate.css, favicon, ikony PWA
 *   • message:FORCE_UPDATE: nowy typ — czyści cache + skipWaiting atomowo
 *   • message:CACHE_STATUS: nowy typ — zwraca diagnostykę bucketów cache
 *   • message:CLEAR_CACHE: rozszerzony o selektywne czyszczenie bucketów
 */

// ── Wersja — zmień przy każdym deploymencie ───────────────────────────────────
const CACHE_VERSION = 'fitai-v3.3.0';
const API_BASE = 'https://fitai-backend-l918.onrender.com';

// ── Nazwy bucketów cache ───────────────────────────────────────────────────────
const CACHE = {
  shell:  `${CACHE_VERSION}-shell`,   // HTML + CDN assets (fonty, Chart.js, Tailwind)
  api:    `${CACHE_VERSION}-api`,     // Odpowiedzi API z danymi (plan, profil, statystyki)
  images: `${CACHE_VERSION}-images`,  // Ikony, obrazki
};
const KNOWN_CACHES = new Set(Object.values(CACHE));

// ── App Shell — pre-cache przy instalacji ──────────────────────────────────────
//
// AUDYT CDN (v3.1.0 → v3.2.0):
//   Dodane brakujące zasoby, których brak powoduje "rozsypanie" UI offline:
//   ✅ lucide-icons      — ikony używane w całym interfejsie
//   ✅ animate.css       — animacje kart i modali
//   ✅ favicon.ico       — bez niego przeglądarka robi dodatkowy request przy starcie
//   ✅ ./icons/icon-192  — wymagany przez manifest jako PWA launcher icon
//   ✅ ./icons/icon-512  — wymagany przez Chromium do instalacji PWA
//   ✅ Google Fonts CSS  — zachowany; font-display:swap gwarantuje fallback systemowy
//   ✅ Tailwind CDN      — zachowany z ostrzeżeniem: cdn.tailwindcss.com
//                          jest narzędziem deweloperskim; produkcja wymaga
//                          zbudowanego pliku CSS (np. tailwind.min.css)
//   ✅ Chart.js 4.4.3    — zachowany
//   ✅ jsPDF 2.5.1       — zachowany
//
// Uwaga o CORS dla CDN:
//   Zasoby cross-origin muszą mieć CORS (Access-Control-Allow-Origin: *)
//   żeby trafić do cache z credentials. Większość publicznych CDN to spełnia.
//   cdn.tailwindcss.com MOŻE nie wysyłać CORS → fallback do opaque (pomijany).
const SHELL_ASSETS = [
  // ── Lokalne ──────────────────────────────────────────────────────────────
  './',
  './index.html',
  './manifest.json',
  './favicon.ico',
  './icons/icon-72.png',
  './icons/icon-96.png',
  './icons/icon-192.png',
  './icons/icon-512.png',

  // ── Google Fonts (CSS + preconnect) ─────────────────────────────────────
  'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Syne:wght@600;700;800&display=swap',
  // Uwaga: fonty .woff2 są pobierane lazily przez przeglądarkę — SW cache'uje je
  // automatycznie przez cacheFirstWithRevalidate gdy zostaną pierwszy raz użyte.

  // ── Tailwind CSS ─────────────────────────────────────────────────────────
  // ⚠ cdn.tailwindcss.com to CDN deweloperski (ładuje ~350 KB + runtime JS).
  //   W produkcji zastąp poniższe statycznie zbudowanym plikiem CSS.
  'https://cdn.tailwindcss.com',

  // ── Chart.js ─────────────────────────────────────────────────────────────
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js',

  // ── jsPDF — generowanie PDF offline ─────────────────────────────────────
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',

  // ── Lucide Icons — ikony używane w UI ────────────────────────────────────
  // Wersja UMD (pojedynczy plik JS) — działa bez bundlera
  'https://unpkg.com/lucide@latest/dist/umd/lucide.min.js',

  // ── Animate.css — animacje kart, modali, toastów ─────────────────────────
  'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css',
];

// ── API: Network-First + cache (dane z planem, profilem, statystykami) ─────────
const API_CACHEABLE = [
  /\/app\/checkin\//,
  /\/app\/stats\//,
  /\/app\/xp\//,
  /\/app\/profile\//,
  /\/app\/plan\//,
  /\/app\/overload\//,
  /\/weekly-plan\//,
];

// ── Nigdy nie cache'uj — zawsze świeże dane ────────────────────────────────────
const NEVER_CACHE = [
  /\/ai\//,           // streaming AI
  /\/app\/fridge/,    // fridge chef (per-request)
  /\/app\/meal-prep/, // meal prep (per-request)
  /\/app\/export\//,  // ICS / PDF exports
  /\/app\/log\//,     // zapis logów
];


// ══════════════════════════════════════════════════════════════════════════════
//  INSTALL
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('install', event => {
  console.log(`[SW ${CACHE_VERSION}] Install`);
  event.waitUntil(
    caches.open(CACHE.shell)
      .then(cache =>
        // allSettled — jeden błąd CDN nie wysypuje całej instalacji
        Promise.allSettled(
          SHELL_ASSETS.map(url =>
            cache.add(url).catch(err =>
              console.warn(`[SW] Pre-cache pominięty: ${url}`, err.message)
            )
          )
        )
      )
      .then(() => {
        console.log(`[SW ${CACHE_VERSION}] Shell gotowy. skipWaiting().`);
        // Nowy SW nie czeka na zamknięcie starych kart
        return self.skipWaiting();
      })
  );
});


// ══════════════════════════════════════════════════════════════════════════════
//  ACTIVATE
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('activate', event => {
  console.log(`[SW ${CACHE_VERSION}] Activate`);
  event.waitUntil((async () => {

    // 1. Usuń wszystkie stare cache (nie należące do KNOWN_CACHES tej wersji)
    const allKeys = await caches.keys();
    const stale = allKeys.filter(k => k.startsWith('fitai-') && !KNOWN_CACHES.has(k));
    if (stale.length) {
      console.log('[SW] Usuwam stare caches:', stale);
      await Promise.all(stale.map(k => caches.delete(k)));
    }

    // 2. Przejmij wszystkie otwarte karty natychmiast (bez przeładowania)
    await self.clients.claim();

    // 3. Powiadom każdą kartę → index.html pokaże toast "Nowa wersja dostępna"
    const allClients = await self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true,
    });
    for (const client of allClients) {
      client.postMessage({
        type:      'SW_UPDATED',
        version:   CACHE_VERSION,
        timestamp: Date.now(),
      });
    }
    console.log(`[SW] Aktywacja OK. Powiadomionych klientów: ${allClients.length}`);

  })());
});


// ══════════════════════════════════════════════════════════════════════════════
//  FETCH — routing requestów
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignoruj nie-GET i chrome-extension://
  if (request.method !== 'GET') return;
  if (url.protocol === 'chrome-extension:') return;

  const isLocalApi = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  const isProductionApi = url.hostname === 'fitai-api-v83w.onrender.com';
  const isApi = isLocalApi || isProductionApi;
  const path = url.pathname;

  // 1. Nigdy nie cache'uj (AI, eksport, logowanie)
  if (isApi && NEVER_CACHE.some(p => p.test(path))) {
    event.respondWith(networkOnly(request));
    return;
  }

  // 2. API z cache: Network-First → fallback do JSON cache
  if (isApi && API_CACHEABLE.some(p => p.test(path))) {
    event.respondWith(networkFirstJSON(request));
    return;
  }

  // 3. Pozostałe lokalne API — network-only
  if (isApi) {
    event.respondWith(networkOnly(request));
    return;
  }

  // 4. Nawigacja HTML
  if (request.mode === 'navigate') {
    event.respondWith(navigateFetch(request));
    return;
  }

  // 5. Obrazki i ikony — Cache-First z fallbackiem
  if (/\.(png|jpg|jpeg|webp|svg|ico)$/i.test(path)) {
    event.respondWith(cacheFirstImages(request));
    return;
  }

  // 6. CDN assets (fonty, JS) — Cache-First + SWR w tle
  event.respondWith(cacheFirstWithRevalidate(request));
});


// ══════════════════════════════════════════════════════════════════════════════
//  STRATEGIE CACHOWANIA
// ══════════════════════════════════════════════════════════════════════════════

/** Network-Only — bez żadnego cache */
async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch {
    return jsonOfflineResponse();
  }
}

/**
 * Network-First dla JSON API z timeoutem.
 *
 * Naprawione błędy względem v3.0:
 *   1. TIMEOUT RACE (4 s) — na słabym LTE nie czekamy w nieskończoność;
 *      po 4 s wygrywamy cache zamiast zawiesić interfejs.
 *   2. NON-OK PASSTHROUGH — odpowiedzi 4xx/5xx też wracają do aplikacji
 *      (błąd 401 musi dotrzeć do index.html, żeby przekierować na login).
 *   3. OPAQUE RESPONSES — zasoby cross-origin z no-cors nie trafiają do cache
 *      (nie możemy sprawdzić .ok, więc pomijamy opaque zamiast cache'ować 0-byte).
 *   4. CACHE-HIT HEADERS — X-Served-From i X-Cache-Age informują UI o źródle.
 */
async function networkFirstJSON(request) {
  const cache = await caches.open(CACHE.api);

  // Pomocnik: zwróć cachedResponse z nagłówkami diagnostycznymi
  async function serveCached(reason) {
    const cached = await cache.match(request);
    if (!cached) return jsonOfflineResponse(reason);

    const headers = new Headers(cached.headers);
    headers.set('X-Served-From', 'sw-cache');
    headers.set('X-Cache-Version', CACHE_VERSION);
    headers.set('X-Cache-Reason', reason);

    // Oblicz wiek cachedResponse jeśli Date jest dostępny
    const dateStr = cached.headers.get('Date');
    if (dateStr) {
      const ageSeconds = Math.round((Date.now() - new Date(dateStr).getTime()) / 1000);
      headers.set('X-Cache-Age', String(ageSeconds));
    }

    return new Response(cached.body, {
      status:     cached.status,
      statusText: cached.statusText,
      headers,
    });
  }

  // Race: fetch vs 4-sekundowy timeout → użytkownik zawsze dostaje odpowiedź
  const NETWORK_TIMEOUT_MS = 4000;
  const timeoutPromise = new Promise(resolve =>
    setTimeout(() => resolve(null), NETWORK_TIMEOUT_MS)
  );

  let response;
  try {
    response = await Promise.race([fetch(request), timeoutPromise]);
  } catch {
    // Błąd sieciowy (np. offline, DNS failure)
    return serveCached('network-error');
  }

  // Timeout wygrał — serwuj cache ze wskazówką dla UI
  if (response === null) {
    console.warn(`[SW] Timeout ${NETWORK_TIMEOUT_MS}ms dla ${request.url} — serwuję z cache`);
    return serveCached('network-timeout');
  }

  // Opaque response (cross-origin no-cors) — nie cache'uj, zwróć jak jest
  if (response.type === 'opaque') return response;

  // Odpowiedzi 4xx/5xx muszą dotrzeć do aplikacji (np. 401 → redirect do loginu)
  // Cache'ujemy TYLKO 200 OK
  if (response.ok) {
    cache.put(request, response.clone()); // nie blokuje — fire-and-forget
  }

  return response;
}

/**
 * Network-First dla HTML nawigacji.
 * Fallback: cached request → cached index.html → inline offline page.
 */
async function navigateFetch(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE.shell);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return (
      (await caches.match(request))       ||
      (await caches.match('./index.html')) ||
      (await caches.match('/index.html'))  ||
      offlineHTMLPage()
    );
  }
}

/**
 * Cache-First dla obrazków i ikon.
 *
 * Hierarchia fallbacków jeśli zasób niedostępny:
 *   badge-72.png → icon-72.png → icon-96.png → SVG placeholder
 *   icon-XXX.png (dowolny) → icon-72.png → SVG placeholder
 */
async function cacheFirstImages(request) {
  const url   = new URL(request.url);
  const cache = await caches.open(CACHE.images);

  // Sprawdź cache najpierw
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
      return response;
    }
    throw new Error(`HTTP ${response.status}`);
  } catch {
    const filename = url.pathname.split('/').pop() ?? '';
    const dir = url.href.replace(/\/[^/]+$/, '/');

    // badge-72.png → icon-72.png → icon-96.png
    if (filename.startsWith('badge-')) {
      const sizeStr = filename.replace('badge-', '').replace('.png', '');
      const candidates = [`icon-${sizeStr}.png`, 'icon-72.png', 'icon-96.png'];
      for (const name of candidates) {
        const r = await fetchAndCache(dir + name, cache);
        if (r) return r;
      }
    }

    // icon-512.png (duże) → icon-192.png → icon-72.png
    if (filename.startsWith('icon-')) {
      const sizeNum = parseInt(filename.replace('icon-', '').replace('.png', ''), 10);
      if (sizeNum > 192) {
        const r = await fetchAndCache(dir + 'icon-192.png', cache)
               ?? await fetchAndCache(dir + 'icon-72.png', cache);
        if (r) return r;
      } else {
        const r = await fetchAndCache(dir + 'icon-72.png', cache);
        if (r) return r;
      }
    }

    console.warn(`[SW] Ikona niedostępna, SVG placeholder: ${url.pathname}`);
    return svgPlaceholder();
  }
}

/**
 * Cache-First + Stale-While-Revalidate dla CDN assets.
 * Zwraca cache od razu; w tle aktualizuje niewidocznie.
 */
async function cacheFirstWithRevalidate(request) {
  const cache  = await caches.open(CACHE.shell);
  const cached = await cache.match(request);

  const revalidate = fetch(request)
    .then(response => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);

  return cached ?? (await revalidate) ?? offlineHTMLPage();
}


// ══════════════════════════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════════════════════════

async function fetchAndCache(url, cache) {
  try {
    const r = await fetch(url);
    if (r.ok) { cache.put(url, r.clone()); return r; }
  } catch { /* noop */ }
  return null;
}

function jsonOfflineResponse(reason = 'offline') {
  return new Response(
    JSON.stringify({
      error:       'offline',
      detail:      'Brak połączenia. Ostatnie znane dane z cache.',
      served_from: 'sw-offline-fallback',
      reason,
    }),
    {
      status:  503,
      headers: {
        'Content-Type': 'application/json',
        'X-Served-From': 'sw-offline-fallback',
        'X-Cache-Reason': reason,
      },
    }
  );
}

function svgPlaceholder() {
  return new Response(
    `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 72 72">
       <rect width="72" height="72" rx="16" fill="#0a0b10"/>
       <text x="36" y="46" text-anchor="middle" font-size="34" fill="#00e5ff"
             font-family="system-ui,sans-serif" font-weight="800">F</text>
     </svg>`,
    { status: 200, headers: { 'Content-Type': 'image/svg+xml' } }
  );
}

function offlineHTMLPage() {
  return new Response(
    `<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FitAI — Offline</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:system-ui,sans-serif;background:#0a0b10;color:#fff;
         min-height:100vh;display:flex;align-items:center;
         justify-content:center;padding:24px}
    .card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
          border-radius:24px;padding:48px 32px;max-width:380px;
          width:100%;text-align:center}
    .ico{font-size:3.5rem;margin-bottom:16px}
    .badge{display:inline-block;margin-bottom:20px;
           background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.3);
           color:#00e5ff;border-radius:999px;padding:3px 14px;
           font-size:11px;font-weight:700;letter-spacing:.05em}
    h1{font-size:1.5rem;font-weight:800;margin-bottom:10px}
    p{color:#64748b;font-size:.875rem;line-height:1.6;margin-bottom:28px}
    button{background:linear-gradient(135deg,#00e5ff,#7c3aed);color:#000;
           border:none;border-radius:12px;padding:12px 28px;
           font-size:.9rem;font-weight:700;cursor:pointer;
           width:100%;transition:opacity .2s}
    button:hover{opacity:.85}
    small{display:block;font-size:.72rem;color:#334155;margin-top:14px}
  </style>
</head>
<body>
  <div class="card">
    <div class="ico">📱</div>
    <span class="badge">TRYB OFFLINE</span>
    <h1>FitAI działa bez sieci</h1>
    <p>Twój plan treningowy i dieta są dostępne lokalnie.
       Połącz się z internetem, by zsynchronizować postępy.</p>
    <button onclick="location.reload()">Spróbuj ponownie</button>
    <small>Dane z ostatniej sesji zostaną przywrócone automatycznie.</small>
  </div>
</body>
</html>`,
    { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}


// ══════════════════════════════════════════════════════════════════════════════
//  BACKGROUND SYNC — kolejkowanie logów gdy offline
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('sync', event => {
  if (event.tag === 'fitai-sync-logs') {
    console.log('[SW] Background sync: wysyłam kolejkowane logi...');
    event.waitUntil(syncPendingLogs());
  }
});

async function getTokenFromClients() {
  try {
    const clients = await self.clients.matchAll({ type: 'window' });
    for (const client of clients) {
      return new Promise(resolve => {
        const channel = new MessageChannel();
        channel.port1.onmessage = e => resolve(e.data?.token || null);
        client.postMessage({ type: 'GET_TOKEN' }, [channel.port2]);
        setTimeout(() => resolve(null), 500);
      });
    }
  } catch { return null; }
  return null;
}

async function syncPendingLogs() {
  let pendingCache;
  try { pendingCache = await caches.open('fitai-pending-logs'); }
  catch { return; }

  const keys = await pendingCache.keys();
  let synced = 0, failed = 0;

  for (const req of keys) {
    const resp = await pendingCache.match(req);
    if (!resp) continue;
    try {
      const body   = await resp.json();
      const token  = await getTokenFromClients();
      const result = await fetch(req.url || (API_BASE + '/app/checkin'), {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': 'Bearer ' + token } : {}),
        },
        body:    JSON.stringify(body),
      });
      if (result.ok) { await pendingCache.delete(req); synced++; }
      else failed++;
    } catch { failed++; }
  }

  console.log(`[SW] Sync: ${synced} OK, ${failed} błędów.`);

  if (synced > 0) {
    const clients = await self.clients.matchAll({ type: 'window' });
    for (const client of clients) {
      client.postMessage({ type: 'SW_SYNC_DONE', synced, failed });
    }
  }
}


// ══════════════════════════════════════════════════════════════════════════════
//  PUSH NOTIFICATIONS
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data?.json() ?? {}; } catch { /* złe JSON */ }

  event.waitUntil((async () => {
    // Inteligentny fallback ikony powiadomień:
    // badge-72.png → icon-72.png → undefined (system pominie badge)
    const tryHead = async (path) => {
      try { const r = await fetch(path, { method: 'HEAD' }); return r.ok ? path : null; }
      catch { return null; }
    };
    const badge = (await tryHead('./icons/badge-72.png'))
               ?? (await tryHead('./icons/icon-72.png'))
               ?? undefined;

    await self.registration.showNotification(data.title ?? 'FitAI 💪', {
      body:    data.body    ?? 'Czas na trening!',
      icon:    data.icon    ?? './icons/icon-192.png',
      badge,
      vibrate: [100, 50, 100],
      tag:     data.tag     ?? 'fitai-reminder',
      renotify: true,
      data:    { url: data.url ?? './' },
      actions: [
        { action: 'open',    title: 'Otwórz FitAI' },
        { action: 'dismiss', title: 'Później'       },
      ],
    });
  })());
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const target = event.notification.data?.url ?? './';
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then(list => {
        // Skup istniejącą kartę jeśli otwarta
        const open = list.find(c => c.url.includes('index.html') || c.url.endsWith('/'));
        return open ? open.focus() : self.clients.openWindow(target);
      })
  );
});


// ══════════════════════════════════════════════════════════════════════════════
//  WIADOMOŚCI OD KLIENTÓW (index.html → SW)
// ══════════════════════════════════════════════════════════════════════════════
//
// Obsługiwane typy wiadomości:
//
//  ┌─────────────────┬──────────────────────────────────────────────────────┐
//  │ SKIP_WAITING    │ Natychmiastowa aktywacja nowego SW (bez reloadu karty)│
//  │ FORCE_UPDATE    │ Usuń WSZYSTKIE cache, aktywuj SW, przeładuj stronę   │
//  │ GET_VERSION     │ Zwróć aktualną wersję SW                             │
//  │ CACHE_STATUS    │ Zwróć listę bucketów cache i ich rozmiary            │
//  │ CLEAR_CACHE     │ Wyczyść wybrane lub wszystkie buckety cache FitAI    │
//  └─────────────────┴──────────────────────────────────────────────────────┘
self.addEventListener('message', event => {
  const { type, payload } = event.data ?? {};

  // ── SKIP_WAITING ───────────────────────────────────────────────────────────
  // index.html prosi o natychmiastową aktywację (przycisk "Zaktualizuj teraz").
  // Nie usuwa cache — to robi activate automatycznie (stale filter).
  if (type === 'SKIP_WAITING') {
    console.log('[SW] SKIP_WAITING → skipWaiting()');
    self.skipWaiting();
    return;
  }

  // ── FORCE_UPDATE ───────────────────────────────────────────────────────────
  // Wymuś pełną aktualizację: usuń WSZYSTKIE cache tej aplikacji, aktywuj
  // nowego SW, a po aktywacji powiadom klientów żeby przeładowali stronę.
  //
  // Kiedy używać: gdy użytkownik klika "Zaktualizuj i wyczyść" w ustawieniach,
  // lub gdy doszło do błędu cache corruption i dane się "rozsypały".
  //
  // Sekwencja:
  //   1. Usuń wszystkie buckety fitai-*
  //   2. skipWaiting() → nowy SW wchodzi jako active
  //   3. Po activate (clients.claim) → SW wyśle SW_UPDATED do klientów
  //   4. Klienci przeładowują stronę → nowy shell pobierany ze świeżej sieci
  if (type === 'FORCE_UPDATE') {
    console.log('[SW] FORCE_UPDATE — czyszczę cache i aktywuję nową wersję');
    event.waitUntil((async () => {
      // 1. Wyczyść wszystkie fitai-* buckety (w tym stary shell i api cache)
      const allKeys = await caches.keys();
      const fitaiKeys = allKeys.filter(k => k.startsWith('fitai-'));
      await Promise.all(fitaiKeys.map(k => caches.delete(k)));
      console.log(`[SW] FORCE_UPDATE: usunięto ${fitaiKeys.length} bucketów cache`);

      // 2. Potwierdzenie do wywołującego klienta (przed skipWaiting)
      event.source?.postMessage({
        type:          'FORCE_UPDATE_ACK',
        deleted_caches: fitaiKeys,
        version:       CACHE_VERSION,
        timestamp:     Date.now(),
      });

      // 3. Aktywuj nowy SW — activate wyśle SW_UPDATED do wszystkich klientów
      await self.skipWaiting();
    })());
    return;
  }

  // ── GET_VERSION ────────────────────────────────────────────────────────────
  if (type === 'GET_VERSION') {
    event.source?.postMessage({
      type:      'SW_VERSION',
      version:   CACHE_VERSION,
      timestamp: Date.now(),
    });
    return;
  }

  // ── CACHE_STATUS ───────────────────────────────────────────────────────────
  // Zwraca listę aktywnych bucketów cache z liczbą wpisów.
  // UI może wyświetlić panel diagnostyczny "ile danych mam offline".
  if (type === 'CACHE_STATUS') {
    event.waitUntil((async () => {
      const allKeys = await caches.keys();
      const buckets = await Promise.all(
        allKeys
          .filter(k => k.startsWith('fitai-'))
          .map(async (k) => {
            const c = await caches.open(k);
            const entries = await c.keys();
            return { name: k, entries: entries.length };
          })
      );
      event.source?.postMessage({
        type:      'CACHE_STATUS_RESULT',
        buckets,
        version:   CACHE_VERSION,
        timestamp: Date.now(),
      });
    })());
    return;
  }

  // ── CLEAR_CACHE ────────────────────────────────────────────────────────────
  // payload.buckets: string[] — konkretne nazwy bucketów do wyczyszczenia.
  // Brak payload → czyści WSZYSTKIE fitai-* buckety.
  if (type === 'CLEAR_CACHE') {
    event.waitUntil((async () => {
      const allKeys = await caches.keys();
      const fitaiKeys = allKeys.filter(k => k.startsWith('fitai-'));

      // Jeśli podano konkretne buckety — czyść tylko je; w przeciwnym razie wszystkie
      const targetKeys = Array.isArray(payload?.buckets)
        ? fitaiKeys.filter(k => payload.buckets.includes(k))
        : fitaiKeys;

      await Promise.all(targetKeys.map(k => caches.delete(k)));

      event.source?.postMessage({
        type:           'CACHE_CLEARED',
        deleted_caches: targetKeys,
        timestamp:      Date.now(),
      });
    })());
    return;
  }

  // ── GET_TOKEN ──────────────────────────────────────────────────────────────
  // Odpowiedź SW na żądanie tokenu z getTokenFromClients().
  // Klient może nadpisać to zachowanie, wysyłając faktyczny token przez port.
  if (type === 'GET_TOKEN') {
    const port = event.ports[0];
    if (port) {
      port.postMessage({ token: null });
    }
    return;
  }
});