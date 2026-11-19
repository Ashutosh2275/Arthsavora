# ARTHSAVORA — Web App Manifest & Installation Standards

**Document Reference:** `docs/PWA_MANIFEST_AND_INSTALLATION.md`  
**Authoritative Standard:** Stage 6 PWA Installation & Discovery  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Web App Manifest Specification

The ARTHSAVORA Web App Manifest is located at `apps/web/public/manifest.webmanifest` and referenced in `index.html`. It conforms strictly to W3C Web App Manifest standards:

```json
{
  "id": "arthsavora-pwa",
  "name": "ARTHSAVORA — Institutional Commercial FinTech Ecosystem",
  "short_name": "ARTHSAVORA",
  "description": "Institutional-grade financial intelligence, double-entry accounting, budgeting, and tax compliance for India.",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
  "theme_color": "#0f172a",
  "background_color": "#020617",
  "orientation": "any",
  "lang": "en-IN",
  "dir": "ltr",
  "categories": ["finance", "business", "productivity"],
  "prefer_related_applications": false
}
```

---

## 2. Icon Assets & Visual Dimensions

The application includes crisp, vector-scaled SVG and rasterized PNG icons in `public/icons/`:

| Asset Path | Format | Dimension | Purpose / Role |
| :--- | :--- | :--- | :--- |
| `/icons/icon-192x192.png` | PNG | 192 × 192 px | Android home screen & standard app drawer |
| `/icons/icon-512x512.png` | PNG | 512 × 512 px | High-resolution splash screens & app stores |
| `/icons/icon-maskable-512x512.png`| PNG | 512 × 512 px | Android adaptive/maskable icons (80% safe zone) |
| `/icons/apple-touch-icon.png` | PNG | 180 × 180 px | iOS Home screen bookmark icon |
| `/favicon.svg` | SVG | Scalable Vector | Browser tab icon and push notification badge |
| `/icons/*.svg` | SVG | Scalable Vector | High-DPI screens and modern vector display engines |

---

## 3. Launch Shortcuts

The manifest defines 4 direct shortcuts enabling users to launch specific workflows directly from their operating system's application launcher or home screen:
1. **New Transaction (`/transactions?action=new`):** Directly opens the transaction record modal.
2. **Dashboard (`/`):** Launches primary institutional financial overview.
3. **Scan Document (`/documents?action=scan`):** Launches camera capture or file ingestion for receipt OCR.
4. **AI Assistant (`/assistant`):** Opens natural-language financial co-pilot.

---

## 4. Multi-Platform Installation Flows

### 4.1 Chromium Browsers (Chrome, Edge, Brave on Android & Desktop)
- The browser fires the `beforeinstallprompt` event.
- `apps/web/src/pwa/registerServiceWorker.ts` intercepts this event and dispatches it to `usePwaStore`.
- The user can trigger installation via:
  1. The "Install App" button in the TopBar.
  2. The Profile menu dropdown option "Install Web App".
  3. Browser omnibox install icon.
- Clicking the action triggers `deferredPrompt.prompt()`, transitioning to standalone window execution upon user approval.

### 4.2 iOS Safari & iPadOS
- Safari on iOS does not support programmatic `beforeinstallprompt`.
- The `InstallPromptModal` component automatically detects iOS user agents (`/iPad|iPhone|iPod/`) and displays step-by-step instructions:
  1. Tap the Safari **Share** icon (square with arrow pointing up).
  2. Scroll down and select **Add to Home Screen**.
  3. Confirm by tapping **Add**.
- Once installed to the iOS Home Screen, ARTHSAVORA runs in full-screen standalone mode (`apple-mobile-web-app-capable`).
