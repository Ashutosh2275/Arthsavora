# ARTHSAVORA — Horizontal and Vertical Scaling Strategy

## 1. Compute Scaling (Stateless API Layer)

The FastAPI modular monolith backend is completely stateless, making horizontal scaling simple and safe.

```
                                [ Cloudflare Edge / WAF ]
                                           |
                                           v
                              [ Application Load Balancer ]
                                           |
               +---------------------------+---------------------------+
               |                           |                           |
               v                           v                           v
     [ ECS Fargate Task 1 ]      [ ECS Fargate Task 2 ]      [ ECS Fargate Task N ]
     (Min: 2 tasks)              (Min: 2 tasks)              (Auto-scaled up to 10)
```

### Auto-Scaling Policies (AWS ECS Target Tracking)
1. **Target Tracking Metric**: Average CPU Utilization = 70%.
2. **Scale-Out Evaluation**: 3 consecutive 1-minute data points > 70% CPU triggers addition of 2 container tasks.
3. **Scale-In Cooldown**: 300 seconds (prevents container thrashing during intermittent traffic spikes).
4. **Scale Bounds**:
   - Staging: Min 1, Max 2
   - Production: Min 2, Max 10

## 2. Database Scaling (PostgreSQL 18)

Relational datastore scaling balances write integrity with read scale:

1. **Vertical Scaling (Primary)**:
   - Starting tier: `db.t4g.medium` (2 vCPU, 4 GB RAM).
   - Scaling threshold: If average CPU > 65% for 1 hour, execute planned maintenance upgrade to `db.m6g.large` (2 vCPU, 8 GB RAM) or `db.m6g.xlarge` (4 vCPU, 16 GB RAM) via zero-downtime failover to updated standby.
2. **Horizontal Read Replicas (Secondary)**:
   - Provision asynchronous read replicas in Zone B / C for heavy analytical queries and month-end financial reporting exports.
   - Core financial ledger writes and balance queries remain strictly on the primary instance to guarantee read-your-writes consistency.

## 3. Cache Scaling (Redis 7)
- Memory eviction policy: `volatile-lru` (evicts least recently used keys with an explicit expiration).
- Redis Multi-AZ cluster auto-fails over if master node exceeds memory bounds or experiences hardware failure.

## 4. Cross-Reference Links
- Performance and Capacity: [PERFORMANCE_AND_CAPACITY.md](file:///d:/Arthsavora/docs/PERFORMANCE_AND_CAPACITY.md)
- Load Test Results: [LOAD_TEST_RESULTS.md](file:///d:/Arthsavora/docs/LOAD_TEST_RESULTS.md)
- Infrastructure Cost Management: [INFRASTRUCTURE_COST_MANAGEMENT.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_COST_MANAGEMENT.md)
