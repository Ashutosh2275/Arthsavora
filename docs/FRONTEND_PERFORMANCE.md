# ARTHSAVORA — Frontend Performance & Optimization Engineering

**Document Reference:** `docs/FRONTEND_PERFORMANCE.md`  
**Authoritative Standard:** Stage 5/6 Web Performance & Asset Delivery  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Performance Goals & Core Web Vitals Targets

ARTHSAVORA targets institutional-level performance standards across all supported network tiers:

| Metric | Target | Production Strategy |
| :--- | :--- | :--- |
| **Largest Contentful Paint (LCP)** | < 1.8s | Fast initial bundle, critical CSS inlining, font display swap |
| **Interaction to Next Paint (INP)** | < 100ms | React 19 concurrent updates, debounced search triggers |
| **Cumulative Layout Shift (CLS)** | < 0.05 | Fixed component dimensions, aspect-ratio constraints |
| **Time to First Byte (TTFB)** | < 200ms | CDN edge caching for static assets, Gzip/Brotli compression |

---

## 2. Bundle Optimization & Code Splitting

The production build pipeline is managed via Vite with Rollup optimization:
- **Build Output Verification:**
  - `dist/index.html`: ~0.47 kB (Gzip: ~0.32 kB)
  - `dist/assets/index-*.css`: ~65.9 kB (Gzip: ~10.9 kB)
  - `dist/assets/index-*.js`: ~1.35 MB (Gzip: ~339.5 kB)
- **Vendor Chunking:** Heavy libraries (Lucide React, Charting engines, Date libraries) are isolated into reusable vendor chunks.
- **Tree-Shaking:** ESM exports across `@arthsavora/contracts` and `@arthsavora/utilities` ensure zero unused functions are bundled into the client runtime.

---

## 3. Runtime Rendering Optimization

### 3.1 Granular Zustand Subscriptions
Components avoid subscribing to entire store objects:
```typescript
// Subscribes only to transaction list mutations
const transactions = useTransactionStore((state) => state.transactions);
```
This isolates re-renders to only components consuming the changed slice.

### 3.2 Debounced Search & Input Dispatch
The `GlobalSearch.tsx` component applies a 200ms debounce window before querying stores or external search APIs, preventing excessive computational loops during fast user typing.

### 3.3 Virtualized Tables & Pagination
Large transaction datasets and general ledger journal postings utilize server-side pagination with default page sizes of 25–50 rows, preventing DOM node bloat and memory leaks.

---

## 4. Asset Compression & Caching Policies

1. **Immutable Asset Hashing:** All compiled JS/CSS artifacts include content hashes in their filenames (e.g. `index-BlVuj7kZ.js`), enabling aggressive `Cache-Control: public, max-age=31536000, immutable` headers on production CDNs.
2. **Zero Runtime CSS Ingestion:** Tailwind CSS compiles into static utility classes at build time. No runtime CSS-in-JS style evaluation overhead is incurred.
