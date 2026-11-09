const CACHE_NAME = 'balaji-connect-v2.4';
const STATIC_ASSETS = [
    '/offline/',
    '/static/css/styles.css?v=4.0',
    '/static/js/api.js?v=4.0',
    '/static/js/chat.js?v=4.0',
    '/static/js/app.js?v=4.0',
    '/static/images/balaji_logo.jpg',
    '/static/images/icons/icon-192.png',
    '/static/images/icons/icon-512.png',
    '/static/images/icons/apple-touch-icon.png'
];

// Install: Cache essential application shell and offline fallback
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.warn('PWA: Some static assets failed to precache:', err);
            });
        }).then(() => self.skipWaiting())
    );
});

// Activate: Clean up outdated caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== CACHE_NAME) {
                        return caches.delete(name);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch: Strategy depending on request type
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Skip non-GET requests and WebSocket connections
    if (request.method !== 'GET' || url.protocol === 'ws:' || url.protocol === 'wss:') {
        return;
    }

    // 1. Navigation requests (HTML pages): Network-only with offline fallback
    // Never cache dynamic user-authenticated HTML to prevent cross-account issues and redirect loops
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(async () => {
                // Server is down or phone is offline: return offline fallback
                const offlineFallback = await caches.match('/offline/');
                if (offlineFallback) {
                    return offlineFallback;
                }
                return new Response(
                    '<h1>Balaji Connect Offline</h1><p>The company server is currently unreachable. Please check your connection.</p>',
                    { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                );
            })
        );
        return;
    }

    // 2. API requests (/api/): Always bypass Service Worker and use native network directly
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // 3. Static assets: Network first with cache fallback
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            fetch(request)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const copy = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
                    }
                    return networkResponse;
                })
                .catch(async () => {
                    const cached = await caches.match(request);
                    if (cached) return cached;
                    return new Response('', { status: 404, statusText: 'Not Found' });
                })
        );
        return;
    }

    // Default: Network with cache fallback
    event.respondWith(
        fetch(request).catch(() => caches.match(request))
    );
});

