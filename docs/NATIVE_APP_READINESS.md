# ARTHSAVORA — Future Native Android & iOS Readiness

**Document Reference:** `docs/NATIVE_APP_READINESS.md`  
**Authoritative Standard:** Stage 6 Cross-Platform Strategy & Native Migration Boundary  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Architectural Strategy: Single Source of Financial Truth

ARTHSAVORA explicitly rejects building duplicate calculation engines or parallel API sets for mobile. Whether accessed via the Web Browser, an installed PWA, or a future native Android (Kotlin) / iOS (Swift) client, **all financial math, ledger rules, and authorization boundaries reside exclusively in the backend core**:
- Double-entry balance calculation in Python ledger service.
- Indian Financial Year (Apr 1 – Mar 31) date math.
- Section 115BAC Income Tax calculation rules.
- GST summary calculations.
- Anomaly scoring and detection models.

Future native apps will consume the exact same versioned `/api/v1` REST endpoints.

---

## 2. Shared Assets & Reusable Boundaries

1. **Shared DTO Contracts (`@arthsavora/contracts`):**
   - TypeScript interfaces map directly to Kotlin data classes and Swift Codable structs.
2. **Canonical Design Tokens (`@arthsavora/design-tokens`):**
   - Color palettes, typography curves, and spacing constants export as JSON tokens for direct ingestion into Android Jetpack Compose or iOS SwiftUI themes.
3. **Deep-Link Structure:**
   - Canonical paths (`/transactions?action=new`, `/documents?action=scan`) map directly to Android App Links and Apple Universal Links.
4. **Push Notification Payloads:**
   - Unified push message schemas (`title`, `body`, `data.url`, `data.category`, `data.severity`) are compatible with both Web Push (VAPID) and future FCM / APNS delivery channels.

---

## 3. Migration Roadmap for Native App Wrappers

When native mobile wrappers are scheduled:
1. **Option A (Capacitor / PWA Shell):** Wraps the existing Vite production output into native Xcode and Android Studio projects with zero code rewrites, granting access to native biometric authentication (FaceID/Fingerprint) and hardware camera APIs.
2. **Option B (Pure Native Kotlin / Swift):** High-performance native views consuming `/api/v1` contracts directly while retaining the identical backend engine.
