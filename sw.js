/**
 * FitAI — Service Worker v3.0
 * ─────────────────────────────────────────────────────────────────────────────
 * Strategie cachowania:
 *   • HTML (nawigacja)        → Network-First + fallback do cache
 *   • API JSON /app/* dane    → Network-First + fallback do cache
 *   • AI / export endpointy   → Network-Only (nigdy nie cache'uj)
 *   • Fonty / CDN scripts     → Cache-First + Stale-While-Revalidate w tle
 *   • Obrazki / ikony         → Cache-First + inteligentny fallback
 *
 * Aktualizacje:
 *   • skipWaiting()  w install  → nowy SW aktywuje się natychmiast
 *   • clients.claim() w activate → przejmuje wszystkie otwarte karty
 *   • postMessage SW_UPDATED    → index.html pokazuje toast "Nowa wersja"
 *   • Zmień CACHE_VERSION przy każdym deploymencie
 */

// ── Wersja — zmień przy każdym deploymencie ───────────────────────────────────
const CACHE_VERSION = 'fitai-v3.1.0';

// ── Nazwy bucketów cache ───────────────────────────────────────────────────────
const CACHE = {
  shell:  `${CACHE_VERSION}-shell`,   // HTML + CDN assets (fonty, Chart.js, Tailwind)
  api:    `${CACHE_VERSION}-api`,     // Odpowiedzi API z danymi (plan, profil, statystyki)
  images: `${CACHE_VERSION}-images`,  // Ikony, obrazki
};
const KNOWN_CACHES = new Set(Object.values(CACHE));

// ── App Shell — pre-cache przy instalacji ──────────────────────────────────────
const SHELL_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Syne:wght@600;700;800&display=swap',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
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
  const path = url.pathname;

  // 1. Nigdy nie cache'uj (AI, eksport, logowanie)
  if (isLocalApi && NEVER_CACHE.some(p => p.test(path))) {
    event.respondWith(networkOnly(request));
    return;
  }

  // 2. API z cache: Network-First → fallback do JSON cache
  if (isLocalApi && API_CACHEABLE.some(p => p.test(path))) {
    event.respondWith(networkFirstJSON(request));
    return;
  }

  // 3. Pozostałe lokalne API — network-only
  if (isLocalApi) {
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
 * Network-First dla JSON API.
 * Sukces → zapisz do CACHE.api.
 * Błąd sieciowy → zwróć z cache z nagłówkiem X-Served-From.
 */
async function networkFirstJSON(request) {
  const cache = await caches.open(CACHE.api);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone()); // async, nie blokuje
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) {
      const headers = new Headers(cached.headers);
      headers.set('X-Served-From', 'sw-cache');
      headers.set('X-Cache-Version', CACHE_VERSION);
      return new Response(cached.body, {
        status:     cached.status,
        statusText: cached.statusText,
        headers,
      });
    }
    return jsonOfflineResponse();
  }
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

function jsonOfflineResponse() {
  return new Response(
    JSON.stringify({
      error:       'offline',
      detail:      'Brak połączenia. Ostatnie znane dane z cache.',
      served_from: 'sw-offline-fallback',
    }),
    {
      status:  503,
      headers: {
        'Content-Type': 'application/json',
        'X-Served-From': 'sw-offline-fallback',
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
      const result = await fetch('/app/log/daily', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
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
self.addEventListener('message', event => {
  const { type } = event.data ?? {};

  // index.html prosi o natychmiastową aktywację (przycisk "Zaktualizuj teraz")
  if (type === 'SKIP_WAITING') {
    console.log('[SW] SKIP_WAITING → skipWaiting()');
    self.skipWaiting();
    return;
  }

  // Zwróć aktualną wersję SW
  if (type === 'GET_VERSION') {
    event.source?.postMessage({ type: 'SW_VERSION', version: CACHE_VERSION });
    return;
  }

  // Ręczne czyszczenie wszystkich cache (przycisk "Wyczyść dane")
  if (type === 'CLEAR_CACHE') {
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k.startsWith('fitai-')).map(k => caches.delete(k))
      ))
      .then(() => event.source?.postMessage({ type: 'CACHE_CLEARED' }));
  }
});