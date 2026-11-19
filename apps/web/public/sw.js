/**
 * ARTHSAVORA — Institutional Commercial FinTech Service Worker
 * Version: v1.0.0
 * 
 * Strict Financial Integrity Invariants:
 * 1. ZERO caching of sensitive /api/* responses in browser caches.
 * 2. ZERO client-side offline queuing of financial mutations.
 * 3. Clean versioning, automatic cache pruning, and safe update transitions.
 * 4. Honest offline fallback for navigation requests.
 * 5. W3C Web Push Notification handling with lock-screen data scrubbing.
 */

const CACHE_VERSION = 'v1.0.0';
const SHELL_CACHE = `arthsavora-shell-${CACHE_VERSION}`;
const STATIC_CACHE = `arthsavora-static-${CACHE_VERSION}`;

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/icons/icon-192x192.svg',
  '/icons/icon-512x512.svg',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/icons/icon-maskable-512x512.png',
  '/icons/apple-touch-icon.png'
];

// Install: Pre-cache core application shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => {
      // Force activation of updated service worker
      return self.skipWaiting();
    })
  );
});

// Activate: Prune obsolete caches from prior versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('arthsavora-') && name !== SHELL_CACHE && name !== STATIC_CACHE)
          .map((obsolete) => caches.delete(obsolete))
      );
    }).then(() => {
      // Immediately take control of all open client tabs
      return self.clients.claim();
    })
  );
});

// Fetch: Intercept and route requests with strict financial security boundaries
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. FINANCIAL INTEGRITY GUARD: API Requests are strictly NETWORK-ONLY
  // Never cache financial data, account balances, reports, or mutations in Service Worker cache.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        // Return structured offline JSON response when disconnected
        return new Response(
          JSON.stringify({
            error: 'Offline',
            code: 'NETWORK_DISCONNECTED',
            message: 'You are currently offline. Financial transactions, reports, and ledger actions require an active network connection.',
            timestamp: new Date().toISOString()
          }),
          {
            status: 503,
            statusText: 'Service Unavailable (Offline)',
            headers: {
              'Content-Type': 'application/json',
              'Cache-Control': 'no-store'
            }
          }
        );
      })
    );
    return;
  }

  // 2. Navigation Requests (User opening or refreshing page in browser/PWA)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // If valid response, update shell cache
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(SHELL_CACHE).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(async () => {
          // Attempt to retrieve cached page or shell
          const cachedResponse = await caches.match(request);
          if (cachedResponse) {
            return cachedResponse;
          }
          const shellResponse = await caches.match('/index.html');
          if (shellResponse) {
            return shellResponse;
          }
          // Fallback to explicit offline guidance page
          const offlinePage = await caches.match('/offline.html');
          return offlinePage || new Response('Offline — ARTHSAVORA', { status: 503, headers: { 'Content-Type': 'text/html' } });
        })
    );
    return;
  }

  // 3. Static Assets: JS bundles, CSS, fonts, and images (Cache-First with Network Revalidation)
  if (
    url.pathname.startsWith('/assets/') ||
    url.pathname.startsWith('/icons/') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.woff2') ||
    url.pathname.endsWith('.svg') ||
    url.pathname.endsWith('.png')
  ) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          // Return cached asset immediately, revalidate in background if online
          fetch(request).then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(STATIC_CACHE).then((cache) => {
                cache.put(request, networkResponse);
              });
            }
          }).catch(() => { /* Ignore background revalidation failure when offline */ });

          return cachedResponse;
        }

        // Fetch from network and populate static cache
        return fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(STATIC_CACHE).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // Default: Normal network fetch
  event.respondWith(fetch(request));
});

// Message Bus: Controlled lifecycle coordination with client React application
self.addEventListener('message', (event) => {
  if (!event.data) return;

  switch (event.data.type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAR_CACHES':
      // Triggered on user logout or tenant context wipe
      caches.keys().then((keys) => {
        return Promise.all(keys.map((k) => caches.delete(k)));
      }).then(() => {
        if (event.ports && event.ports[0]) {
          event.ports[0].postMessage({ success: true });
        }
      });
      break;

    case 'GET_VERSION':
      if (event.ports && event.ports[0]) {
        event.ports[0].postMessage({ version: CACHE_VERSION });
      }
      break;

    default:
      break;
  }
});

// Web Push Notifications: Handle incoming VAPID push events
self.addEventListener('push', (event) => {
  let payload = {
    title: 'ARTHSAVORA Alert',
    body: 'You have a new financial notification.',
    data: { url: '/notifications' }
  };

  if (event.data) {
    try {
      payload = event.data.json();
    } catch (e) {
      payload.body = event.data.text();
    }
  }

  // Scrub sensitive credentials or account numbers for lock-screen privacy
  let cleanBody = payload.body || '';
  cleanBody = cleanBody.replace(/\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b/g, '**** **** **** ****');
  cleanBody = cleanBody.replace(/\b[A-Z]{5}\d{4}[A-Z]\b/g, '*********'); // Mask PAN numbers

  const notificationOptions = {
    body: cleanBody,
    icon: '/icons/icon-192x192.png',
    badge: '/favicon.svg',
    vibrate: [100, 50, 100],
    data: payload.data || { url: '/notifications' },
    tag: payload.tag || 'arthsavora-alert',
    renotify: true
  };

  event.waitUntil(
    self.registration.showNotification(payload.title || 'ARTHSAVORA', notificationOptions)
  );
});

// Push Notification Click: Deep link directly into the application
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Focus existing tab if open
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      // Otherwise open new window
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
