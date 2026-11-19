# ARTHSAVORA — Progressive Web App (PWA) Architecture

**Document Reference:** `docs/PWA_ARCHITECTURE.md`  
**Authoritative Standard:** Stage 6 Progressive Web App & Mobile Platform Readiness  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Executive Summary & Architectural Mission

ARTHSAVORA is an institutional-grade financial management platform engineered for commercial enterprises, collaborative families, and individuals in India. Prompt 26 transforms the web frontend into a production-grade, installable **Progressive Web App (PWA)** that operates seamlessly across desktop, Android, and iOS environments without requiring duplicate business logic or divergent codebases.

### Fundamental Principle: Financial Integrity Over Fictional Offline Commitments
Unlike consumer social applications where offline actions can be optimistically queued and synced later, commercial double-entry financial software must **never pretend an offline financial transaction is committed**. Double-entry accounting requires:
1. Real-time balance validation across debit and credit legs.
2. Concurrent sequence numbering and journal entry locking.
3. Strict multi-tenant workspace authorization.

The ARTHSAVORA PWA architecture enforces **honest offline behavior**: the application shell, non-sensitive navigation, and cached visual structures remain instantly accessible offline, while mutations (transactions, reversals, tax estimates, invoices) explicitly require an authenticated network connection to the server engine.

---

## 2. PWA Layering & High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Client View Layer (React 19)                │
│    AppLayout ── TopBar ── MobileTabBar ── OfflineBanner ── Prompt│
└─────────────────────────────────┬────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────┐
│               PWA State & Service Worker Gateway                 │
│         usePwaStore ── registerServiceWorker ── useWebPush       │
└─────────────────────────────────┬────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────┐
│                 Service Worker (public/sw.js)                    │
│   ├── Precache Cache: arthsavora-shell-v1.0.0                    │
│   ├── Static Asset Cache: arthsavora-static-v1.0.0               │
│   ├── Navigation Routing: Network-First ──> Offline Fallback     │
│   ├── API Network Guard: Strict NETWORK-ONLY (Bypass Cache)      │
│   └── Push Notification: VAPID Push & Lock-Screen Scrubbing      │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ HTTPS Network
┌─────────────────────────────────▼────────────────────────────────┐
│                    ARTHSAVORA REST Backend                       │
│    PostgreSQL 18 ── Double-Entry Ledger ── PyWebPush Gateway     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Architectural Subsystems

### 3.1 Web App Manifest (`manifest.webmanifest`)
Provides application identity, branding colors (`#020617` and `#0f172a`), responsive icons (192x192, 512x512, maskable 512x512, Apple Touch icon, SVG favicon), and direct launch shortcuts for rapid ledger operations (`/transactions?action=new`, `/documents?action=scan`).

### 3.2 Service Worker Runtime (`public/sw.js`)
Autonomous background thread managing asset pre-caching, navigation resilience, network-only enforcement for financial APIs, and W3C Web Push event handling.

### 3.3 Offline Fallback (`public/offline.html`)
A standalone, self-contained offline recovery page styled with ARTHSAVORA's institutional theme, detailing data integrity guarantees and providing automated reconnection retries when network connectivity is restored.

### 3.4 Client State Synchronization (`apps/web/src/pwa/`)
- `usePwaStore.ts`: Reactive Zustand store tracking installability (`beforeinstallprompt`), offline state (`navigator.onLine`), and background service worker update availability.
- `registerServiceWorker.ts`: Lifecycle initializer hooking `window.addEventListener('online' | 'offline')`, `updatefound`, and `controllerchange`.
- `useWebPush.ts`: PushManager VAPID subscription manager interfacing with backend `/api/v1/notifications/push-subscriptions`.
