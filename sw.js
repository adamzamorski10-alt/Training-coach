/**
 * FitAI — Service Worker v2.0
 * Strategia: Cache-First dla assetów, Network-First dla API.
 *
 * v2.0: Niezawodne czyszczenie cache + powiadomienie klientów o aktualizacji.
 * Aby wymusić aktualizację u wszystkich użytkowników: zmień CACHE_VERSION poniżej.
 */

const CACHE_VERSION = "fitai-v2";              // ← zmień tę wartość przy każdym deploymencie
const STATIC_CACHE  = `${CACHE_VERSION}-static`;
const API_CACHE     = `${CACHE_VERSION}-api`;

// Wszystkie znane cache tej wersji — używane do ochrony przed usunięciem
const KNOWN_CACHES = new Set([STATIC_CACHE, API_CACHE]);

// ─── Zasoby do pre-cache (zawsze dostępne offline) ────────────────────────────
const PRECACHE_ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "https://cdn.tailwindcss.com",
  "https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap",
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
];

// ─── Wzorce API które cache'ujemy (plan treningowy, profil) ───────────────────
const CACHEABLE_API_PATTERNS = [
  /\/app\/plan\//,
  /\/app\/profile\//,
  /\/app\/progress\//,
  /\/app\/meals\//,
];

// ─── Install: pre-cache statycznych zasobów ───────────────────────────────────
self.addEventListener("install", (event) => {
  console.log("[SW] Instalacja — pre-cache assetów...");
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
      .catch((err) => console.warn("[SW] Pre-cache błąd (CDN może być offline):", err))
  );
});

// ─── Activate: usuń WSZYSTKIE stare cache i przejmij klientów ─────────────────
self.addEventListener("activate", (event) => {
  console.log(`[SW] Aktywacja wersji ${CACHE_VERSION} — czyszczenie starych cache...`);

  event.waitUntil(
    (async () => {
      const allKeys = await caches.keys();

      // Usuń każdy cache który NIE należy do bieżącej wersji
      const toDelete = allKeys.filter((key) => !KNOWN_CACHES.has(key));

      if (toDelete.length) {
        console.log("[SW] Usuwam stare cache:", toDelete);
        await Promise.all(toDelete.map((key) => caches.delete(key)));
      } else {
        console.log("[SW] Brak starych cache do usunięcia.");
      }

      // Przejmij kontrolę nad wszystkimi otwartymi kartami natychmiast
      // (bez tego nowy SW czeka na zamknięcie starej karty)
      await self.clients.claim();

      // Powiadom wszystkie otwarte karty o dostępnej aktualizacji
      // — index.html nasłuchuje tego zdarzenia i wyświetla toast "Odśwież"
      const allClients = await self.clients.matchAll({ type: "window" });
      for (const client of allClients) {
        client.postMessage({ type: "SW_UPDATED", version: CACHE_VERSION });
      }

      console.log(`[SW] Aktywacja zakończona. Klientów powiadomionych: ${allClients.length}`);
    })()
  );
});

// ─── Fetch: logika routingu requestów ─────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Pomijamy inne originy niż własny + API localhost
  const isOwnOrigin = url.origin === self.location.origin;
  const isLocalApi  = url.hostname === "localhost" || url.hostname === "127.0.0.1";

  // ── API FitAI: Network-First z fallbackiem do cache ───────────────────────
  if (isLocalApi && CACHEABLE_API_PATTERNS.some((p) => p.test(url.pathname))) {
    event.respondWith(networkFirstWithCache(request, API_CACHE));
    return;
  }

  // ── HTML strona główna: Network-First (zawsze świeża wersja) ──────────────
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("./index.html"))
    );
    return;
  }

  // ── Statyczne assety (własny origin): Cache-First ─────────────────────────
  if (isOwnOrigin) {
    event.respondWith(cacheFirstWithNetworkFallback(request, STATIC_CACHE));
    return;
  }

  // ── CDN (Chart.js, fonts itp.): Stale-While-Revalidate ───────────────────
  event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
});

// ─── Strategie cachowania ─────────────────────────────────────────────────────

/**
 * Network-First: próbuj sieć, jeśli offline — zwróć cache.
 * Przy sukcesie sieciowym zapisz odpowiedź do cache.
 */
async function networkFirstWithCache(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      // Klonujemy bo body można odczytać tylko raz
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch {
    const cached = await cache.match(request);
    if (cached) {
      console.log("[SW] Offline – zwracam plan z cache:", request.url);
      return cached;
    }
    // Fallback offline page dla API
    return new Response(
      JSON.stringify({ error: "Brak połączenia. Dane z ostatniej sesji niedostępne.", offline: true }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * Cache-First: zwróć z cache, jeśli brak — pobierz z sieci i zapisz.
 */
async function cacheFirstWithNetworkFallback(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const cache = await caches.open(cacheName);
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch {
    return new Response("Offline — zasób niedostępny.", { status: 503 });
  }
}

/**
 * Stale-While-Revalidate: zwróć cache natychmiast, zaktualizuj w tle.
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache   = await caches.open(cacheName);
  const cached  = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((res) => {
      if (res.ok) cache.put(request, res.clone());
      return res;
    })
    .catch(() => null);

  return cached || fetchPromise;
}

// ─── Background Sync: kolejkuj logi gdy offline ───────────────────────────────
self.addEventListener("sync", (event) => {
  if (event.tag === "fitai-sync-logs") {
    console.log("[SW] Background sync: wysyłanie kolejkowanych logów...");
    event.waitUntil(syncPendingLogs());
  }
});

async function syncPendingLogs() {
  const cache   = await caches.open("fitai-pending-logs");
  const keys    = await cache.keys();
  for (const req of keys) {
    const resp = await cache.match(req);
    const body = await resp.json();
    try {
      await fetch("/app/log/daily", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });
      await cache.delete(req);
      console.log("[SW] Zsynchronizowano log:", req.url);
    } catch (err) {
      console.warn("[SW] Sync nieudany, spróbuj ponownie:", err);
    }
  }
}

// ─── Push Notifications (opcjonalne) ─────────────────────────────────────────
self.addEventListener("push", (event) => {
  const data    = event.data?.json() ?? {};
  const title   = data.title   ?? "FitAI 💪";
  const options = {
    body:    data.body    ?? "Czas na trening!",
    icon:    data.icon    ?? "./icons/icon-192.png",
    badge:   "./icons/badge-72.png",
    vibrate: [100, 50, 100],
    data:    { url: data.url ?? "/" },
    actions: [
      { action: "open",    title: "Otwórz aplikację" },
      { action: "dismiss", title: "Przypomnij później" },
    ],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action !== "dismiss") {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});