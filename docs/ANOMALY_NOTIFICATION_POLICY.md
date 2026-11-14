# Arthsavora Anomaly Notification & Alerting Policy

## 1. Principles of Financial Notification

Alert fatigue is the primary failure mode of automated risk detection systems. When users receive excessive notifications for trivial deviations, they disable alerts or overlook critical warnings.

Arthsavora enforces a **multi-tiered, anti-fatigue notification policy**:
1. **Urgent Alerts for Real Risks**: Immediate push/SMS alerts are restricted to `CRITICAL` events (e.g. charges on cancelled cards, massive unexpected outflows).
2. **Digest Delivery for Routine Variations**: `MEDIUM` and `LOW` alerts are bundled into weekly or bi-weekly financial digests.
3. **Respectful Tone**: Neutral phrasing is mandatory. The system never claims fraudulent behavior or attempts to incite panic.

---

## 2. Notification Dispatch Matrix

| Severity Tier | In-App Dashboard | Push Notification | Email Digest | Escalation Window |
| :--- | :--- | :--- | :--- | :--- |
| **Critical (85–100)** | Real-time Red Banner | Instant (within 60s) | Instant Security Alert | 24 Hours |
| **High (70–84)** | Top of Anomaly Feed | Daily Summary (Opt-in) | Daily Digest | 72 Hours |
| **Medium (50–69)** | Standard Feed Card | None | Weekly Digest | None (User Discretion) |
| **Low (30–49)** | Filterable in Feed | None | None | None |
| **Informational (0–29)** | Audit Log Only | None | None | None |

---

## 3. De-Duplication & Rate Limiting

- **Burst Throttling**: A single merchant burst (e.g., 4 swipes at a store within 10 minutes) generates exactly **one** consolidated alert with counterparty context, not 4 separate notifications.
- **Quiet Hours**: Non-critical notifications respect user-configured quiet hours (default: 22:00 to 07:00 IST).
- **Grace Period on New Accounts**: Newly connected bank accounts or statement imports are assigned an informational baseline period (first 7 days) where historical models calibrate before active alerts fire.
