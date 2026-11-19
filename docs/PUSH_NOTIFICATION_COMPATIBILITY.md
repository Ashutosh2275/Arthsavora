# ARTHSAVORA — Web Push Notification & Device Compatibility

**Document Reference:** `docs/PUSH_NOTIFICATION_COMPATIBILITY.md`  
**Authoritative Standard:** Stage 6 Push Notification Protocols & Device Matrix  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Overview & Architecture

ARTHSAVORA implements W3C-standard Web Push using Voluntary Application Server Identification (VAPID, RFC 8292). Push messages are transmitted from the backend service ([web_push.py](file:///d:/Arthsavora/backend/app/services/notification/channels/web_push.py)) via browser push services to user devices.

---

## 2. Lock-Screen Data Scrubbing & Privacy Guarantees

Because push notifications appear on device lock screens, public banners, and wearable displays, ARTHSAVORA strictly enforces **lock-screen data sanitization**:
1. **Masked Card Numbers:** Any credit/debit card number matching `\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b` is replaced with `**** **** **** ****`.
2. **Masked PAN Identifiers:** Any Indian Permanent Account Number matching `\b[A-Z]{5}\d{4}[A-Z]\b` is masked as `*********`.
3. **No Account Balances on Lock Screen:** Notifications communicate category percentages (e.g., *"Budget Alert: Dining at 90%"*) rather than exact raw account ledger balances.

---

## 3. Platform Compatibility Matrix

| Platform / Browser | Native Push Support | Installation Required? | Notes & Technical Caveats |
| :--- | :--- | :--- | :--- |
| **Android Chrome / Edge** | **Full (W3C Push)** | No (Works in browser & PWA)| High reliability, background wake-up |
| **Android Firefox / Brave** | **Full (W3C Push)** | No | Full background delivery |
| **Desktop Chrome / Edge** | **Full (W3C Push)** | No | System notification center integration |
| **Desktop Firefox** | **Full (W3C Push)** | No | Standard desktop notifications |
| **Desktop Safari (macOS 13+)**| **Full (WebKit Push)**| No (macOS Ventura+) | Standard Web Push support |
| **iOS / iPadOS Safari (16.4+)**| **Supported in PWA Only**| **YES (Must Add to Home Screen)**| **Apple Platform Limitation:** Web Push on iOS requires the user to install the app to the Home Screen first! |
| **iOS Safari (< 16.4)** | **Unsupported** | N/A | Apple did not support Web Push prior to iOS 16.4 |

> [!IMPORTANT]
> **iOS Safari Policy:** On iOS Safari, the browser does NOT expose `PushManager` in ordinary browser tabs. It is only unlocked once the user performs **"Add to Home Screen"** and launches ARTHSAVORA as an installed web app. The UI explicitly marks push as *"Unavailable in browser tab — Install to Home Screen to activate"* on iOS devices.

---

## 4. Subscription Management Lifecycle

1. **Permission Check:** The `useWebPush` hook verifies `('serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window)`.
2. **Explicit Consent:** The user clicks *"Enable Web Push Alerts"* in the Notification Center settings tab. The app never triggers unprompted native permission dialogs.
3. **Subscription Generation:** `registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })` creates the ECDSA encryption keys (`p256dh`, `auth`).
4. **Backend Registration:** Dispatches `POST /api/v1/notifications/push-subscriptions` with device details and user agent.
5. **Subscription Revocation:** Dispatches `DELETE /api/v1/notifications/push-subscriptions/{id}` and calls `subscription.unsubscribe()`.
