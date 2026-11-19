# ARTHSAVORA — Browser & Platform Compatibility Matrix

**Document Reference:** `docs/BROWSER_COMPATIBILITY.md`  
**Authoritative Standard:** Stage 6 Platform Verification & Browser Matrix  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Verified Browser Matrix

| Platform / Operating System | Browser Engine | PWA Installable | Service Worker | Web Push Notifications | Camera Capture |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Android (10+)** | Chrome 110+ | Yes | Yes | Yes | Yes (`capture="environment"`) |
| **Android (10+)** | Edge / Brave | Yes | Yes | Yes | Yes |
| **Android (10+)** | Firefox 115+ | Yes | Yes | Yes | Yes |
| **iOS / iPadOS (16.4+)** | Safari (PWA Mode)| Yes (Home Screen)| Yes | Yes (in installed PWA)| Yes |
| **iOS / iPadOS (< 16.4)** | Safari | Yes (Home Screen)| Yes | No (Platform limitation)| Yes (File picker fallback) |
| **Windows 11 / 10** | Chrome / Edge | Yes | Yes | Yes | Yes (Webcam / File upload) |
| **macOS (Ventura+)** | Safari / Chrome | Yes | Yes | Yes | Yes (File upload) |
| **Linux (Ubuntu/Debian)** | Chrome / Firefox | Yes | Yes | Yes | Yes (File upload) |

---

## 2. Platform Nuances & Graceful Fallbacks

### 2.1 iOS Safari Web Push Restriction
- iOS Safari only allows Web Push subscriptions if the website has been added to the Home Screen and launched in standalone mode.
- In standard Safari browser tabs, `window.PushManager` is undefined. The UI automatically displays a helpful explanation rather than failing with an error.

### 2.2 Camera Capture on Desktop
- On mobile devices, `<input type="file" capture="environment" />` launches the rear camera viewfinder directly.
- On desktop workstations lacking native rear camera triggers, the browser falls back gracefully to a file selection dialog allowing users to pick PDF or image files.

### 2.3 Standalone Window Detection
The application detects whether it is currently executing as an installed standalone PWA via:
```typescript
const isStandalone = 
  window.matchMedia('(display-mode: standalone)').matches ||
  (window.navigator as any).standalone === true;
```
When running standalone, browser install prompts are suppressed automatically.
