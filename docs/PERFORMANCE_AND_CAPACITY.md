# ARTHSAVORA — Performance and Capacity Planning

## 1. Latency Budgets & Target Benchmarks

| Endpoint Category | p50 Latency | p95 Latency | p99 Latency | Max Acceptable |
| :--- | :--- | :--- | :--- | :--- |
| **Health Probes (`/health/live`)** | < 2 ms | < 5 ms | < 10 ms | 50 ms |
| **Authentication (`/login`, `/token`)** | < 45 ms | < 120 ms | < 250 ms | 500 ms |
| **Read Queries (`/accounts`, `/transactions`)**| < 25 ms | < 80 ms | < 200 ms | 600 ms |
| **Write Transactions (Double-Entry Ledger Post)**| < 35 ms | < 110 ms | < 300 ms | 1000 ms |
| **Financial Reports Generation** | < 150 ms | < 450 ms | < 900 ms | 3000 ms |
| **AI Assistant Inference** | < 800 ms | < 1800 ms | < 3500 ms | 8000 ms |

## 2. Capacity Planning Assumptions

- **Baseline Transaction Volume**: 50 transactions/second sustained during peak Indian business hours (10:00 - 18:00 IST).
- **Peak Burst Volume**: 250 transactions/second during salary credit days (1st and last day of month).
- **Data Growth Rate**:
  - ~100,000 transactions/month per 10,000 active users.
  - Generates ~150 MB relational storage growth/month (including indexes and audit logs).
  - AWS RDS 100 GB gp3 storage accommodates > 3 years of growth before expansion.

## 3. Bottleneck Analysis & Mitigations

1. **Database Connection Saturation**:
   - Bottleneck: Max connections reached when scaling compute tasks.
   - Mitigation: Connection pooling in SQLAlchemy + RDS Proxy layer.
2. **Double-Entry Balance Verification**:
   - Bottleneck: Locking ledger accounts during concurrent journal posts.
   - Mitigation: Optimized account row lock ordering (sorted account ID locks) prevents deadlocks; batch insertion of ledger lines within single atomic transaction.
3. **Frontend Bundle Size**:
   - Bottleneck: Large initial JavaScript bundle delaying First Contentful Paint.
   - Mitigation: Gzip compression via Nginx/Cloudflare, Route-level lazy loading (`React.lazy`), and immutable 1-year asset caching.

## 4. Cross-Reference Links
- Scaling Strategy: [SCALING_STRATEGY.md](file:///d:/Arthsavora/docs/SCALING_STRATEGY.md)
- Load Test Results: [LOAD_TEST_RESULTS.md](file:///d:/Arthsavora/docs/LOAD_TEST_RESULTS.md)
