# ARTHSAVORA — Site Reliability Engineering (SRE) and Chaos Principles

## 1. Reliability Objectives & Error Budgets

ARTHSAVORA maintains an availability Service Level Objective (SLO) of **99.95%** (three and a half nines) for core financial transaction endpoints, corresponding to a maximum allowable monthly downtime budget of **21 minutes 54 seconds**.

```
Availability (%) = (Total Requests - 5xx Server Errors) / Total Requests * 100
Target: >= 99.95%
```

## 2. Defensive Engineering Patterns

1. **Circuit Breakers**:
   - Outbound connections to external banking APIs (Account Aggregator, Gemini AI, OCR services) are guarded by circuit breakers.
   - If failure rate exceeds 50% over 10 consecutive requests, the circuit trips OPEN for 30 seconds, immediately returning a cached result or fallback response rather than hanging client requests.
2. **Graceful Degradation**:
   - If Redis is unavailable, rate limiting falls back to local in-process memory tokens.
   - If Gemini AI assistant is unreachable, user receives a structured apology with direct links to standard manual reporting pages.
   - If database read replicas lag, read traffic is automatically directed to the primary instance.
3. **Bounded Timeouts**:
   - Database queries: 10.0s hard limit.
   - Readiness probe: 2.0s hard limit.
   - External HTTP calls (Gemini/AA): 15.0s hard limit with backoff.

## 3. Chaos Engineering and Resilience Drills

Quarterly chaos engineering drills simulate:
- Random termination of backend API tasks.
- Network latency injection (200ms synthetic jitter on database connection).
- Hard loss of Redis container.
- Forced AWS RDS Multi-AZ failover during active user load.

## 4. Cross-Reference Links
- Performance and Capacity: [PERFORMANCE_AND_CAPACITY.md](file:///d:/Arthsavora/docs/PERFORMANCE_AND_CAPACITY.md)
- Scaling Strategy: [SCALING_STRATEGY.md](file:///d:/Arthsavora/docs/SCALING_STRATEGY.md)
- Load Test Results: [LOAD_TEST_RESULTS.md](file:///d:/Arthsavora/docs/LOAD_TEST_RESULTS.md)
