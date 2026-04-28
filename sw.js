// FitAI Progressive Web App - Service Worker
// Obsługuje offline mode, caching i push notifications

const CACHE_VERSION = 'fitai-v2-1';
const CACHE_URLS = [
    '/',
    '/index.html',
    '/app/index.html',
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js'
];

// ============ INSTALL EVENT ============
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_VERSION).then((cache) => {
            console.log('[Service Worker] Caching app shell');
            // Nie cachujemy wszystkie URLs, by uniknąć błędów - tylko kluczowe
            return cache.addAll([
                '/',
                '/index.html'
            ]).catch(() => {
                console.log('[Service Worker] Algunas URLs no pudieron ser cacheadas (esperado para desarrollo local)');
            });
        })
    );
    self.skipWaiting();
});

// ============ ACTIVATE EVENT ============
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_VERSION)
                    .map((cacheName) => {
                        console.log('[Service Worker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    })
            );
        })
    );
    self.clients.claim();
});

// ============ FETCH EVENT - Network First Strategy ============
self.addEventListener('fetch', (event) => {
    const { request } = event;

    // Ignoruj non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Network first, fallback to cache
    event.respondWith(
        fetch(request)
            .then((response) => {
                // Clone response
                const clonedResponse = response.clone();

                // Cache successful responses
                if (response.status === 200) {
                    caches.open(CACHE_VERSION).then((cache) => {
                        cache.put(request, clonedResponse);
                    });
                }

                return response;
            })
            .catch(() => {
                // Fallback to cache when offline
                return caches.match(request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }

                    // Return offline page if available
                    if (request.mode === 'navigate') {
                        return caches.match('/index.html');
                    }

                    // Return placeholder
                    return new Response('Offline - treść niedostępna', {
                        status: 503,
                        statusText: 'Service Unavailable',
                        headers: new Headers({
                            'Content-Type': 'text/plain'
                        })
                    });
                });
            })
    );
});

// ============ PUSH NOTIFICATIONS ============
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'FitAI Notification';
    const options = {
        body: data.body || 'Masz nową wiadomość',
        icon: '/icon-192.png',
        badge: '/badge-72.png',
        tag: data.tag || 'fitai-notification',
        requireInteraction: false,
        actions: [
            {
                action: 'open',
                title: 'Otwórz'
            },
            {
                action: 'close',
                title: 'Zamknij'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// ============ NOTIFICATION CLICK ============
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'close') {
        return;
    }

    event.waitUntil(
        clients.matchAll({ type: 'window' }).then((clientList) => {
            // Sprawdź czy jest już otwarta karta
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url === '/' && 'focus' in client) {
                    return client.focus();
                }
            }
            // Otwórz nową kartę
            if (clients.openWindow) {
                return clients.openWindow('/');
            }
        })
    );
});

// ============ BACKGROUND SYNC (OPTIONAL) ============
self.addEventListener('sync', (event) => {
    if (event.tag === 'fitai-sync') {
        event.waitUntil(
            // Synchronizuj dane z serwerem
            fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(() => {
                console.log('[Service Worker] Sync failed - will retry later');
            })
        );
    }
});

console.log('[Service Worker] Script loaded and ready');
