# ARTHSAVORA — Service Worker Caching & Lifecycle Strategy

**Document Reference:** `docs/SERVICE_WORKER_STRATEGY.md`  
**Authoritative Standard:** Stage 6 Service Worker Lifecycle & Financial Safeguards  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Overview & Service Worker Responsibilities

The service worker (`apps/web/public/sw.js`) operates as a programmable network proxy running in an isolated background thread. Its responsibilities are strictly bounded:
1. Application shell caching for sub-second repeat loads.
2. Static asset caching (Vite JS bundles, CSS, fonts, SVG icons).
3. Offline fallback page delivery when network disconnection prevents navigation.
4. Strict network-only pass-through for all financial API calls (`/api/*`).
5. Web Push notification handling with lock-screen data scrubbing.
6. Controlled cache eviction on version upgrades and user logout.

---

## 2. Strict Financial Caching Invariants

> [!CAUTION]
> **Zero Financial Data in Browser Service Worker Caches**
> Financial records, account balances, tax reports, and transaction details must NEVER be cached by the Service Worker.

The fetch handler in `sw.js` enforces the following routing rules:

```javascript
// 1. API Requests are strictly NETWORK-ONLY
if (url.pathname.startsWith('/api/')) {
  event.respondWith(
    fetch(request).catch(() => {
      return new Response(
        JSON.stringify({
          error: 'Offline',
          code: 'NETWORK_DISCONNECTED',
          message: 'You are currently offline. Financial operations require an active network connection.',
          timestamp: new Date().toISOString()
        }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
        }
      );
    })
  );
  return;
}
```

### Why Financial API Caching is Prohibited in Service Worker:
- **Balance Invalidation:** Stale cached balances would mislead users regarding available funds or credit limits.
- **Double-Posting Risk:** Cached POST/PUT responses could trick client state into assuming a transaction was posted when it was not recorded on the server.
- **Shared Device Exposure:** Service Worker CacheStorage is unencrypted at rest within browser profiles. Storing private financial records in CacheStorage creates high-severity data leakage risks on shared or family computers.

---

## 3. Caching Strategies by Asset Category

| Request Type | Strategy | Cache Name | Fallback Behavior |
| :--- | :--- | :--- | :--- |
| **HTML Navigation (`mode: 'navigate'`)** | Network-First with Cache Fallback | `arthsavora-shell-v1.0.0` | Serves cached `/index.html` or `/offline.html` |
| **Static Bundles (`/assets/*.js`, `*.css`)** | Stale-While-Revalidate / Cache-First | `arthsavora-static-v1.0.0` | Serves cached version while revalidating |
| **Icons & Media (`/icons/*`, `/favicon.svg`)**| Cache-First | `arthsavora-static-v1.0.0` | Embedded SVG fallbacks |
| **Financial APIs (`/api/*`)** | **Strict Network-Only** | **NONE (Never Cached)** | Returns 503 JSON `{ error: 'Offline' }` |
| **Document Downloads (PDF/Images)** | Network-Only | **NONE (Never Cached)** | Fails gracefully with user retry alert |

---

## 4. Lifecycle & Controlled Update Management

### 4.1 Installation & Pre-Caching
On the `install` event, the service worker opens `arthsavora-shell-v1.0.0` and pre-fetches essential assets (`/`, `/index.html`, `/offline.html`, `/manifest.webmanifest`, `/favicon.svg`, icons). It calls `self.skipWaiting()` to stage the new version.

### 4.2 Activation & Obsolete Cache Deletion
On `activate`, the worker iterates over all existing caches in `caches.keys()`. Any cache key starting with `arthsavora-` that does not match the active `CACHE_VERSION` is permanently deleted:
```javascript
caches.keys().then((cacheNames) => {
  return Promise.all(
    cacheNames
      .filter((name) => name.startsWith('arthsavora-') && name !== SHELL_CACHE && name !== STATIC_CACHE)
      .map((obsolete) => caches.delete(obsolete))
  );
})
```
It then calls `self.clients.claim()` to take control of all active client windows.

### 4.3 Safe Update Notification (Non-Disruptive)
When a new service worker is detected by `registerServiceWorker.ts`:
1. `usePwaStore.getState().setUpdateAvailable(registration)` is invoked.
2. The user sees a non-modal update banner ([UpdatePrompt.tsx](file:///d:/Arthsavora/apps/web/src/components/pwa/UpdatePrompt.tsx)).
3. The application **never force-reloads** while a user is actively typing in a transaction form or reviewing an invoice.
4. When the user explicitly taps **Update Now**, `registration.waiting.postMessage({ type: 'SKIP_WAITING' })` is sent, and the window smoothly reloads.

### 4.4 Logout & Session Cache Purging
When a user signs out via `TopBar.tsx`, a message is posted to the service worker:
```javascript
navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHES' });
```
This wipes all temporary cached assets and ensures zero session residue on shared devices.
