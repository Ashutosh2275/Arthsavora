# ARTHSAVORA — Health and Readiness Check Standard

## 1. Objective and Probe Separation

To prevent cascading failures and avoid overloading downstream databases during traffic spikes or network blips, ARTHSAVORA maintains **two distinct probe contracts**:
1. **Liveness Probe (`/api/v1/health/live`)**: Answers *"Is the Python/Uvicorn process alive and responsive?"*
2. **Readiness Probe (`/api/v1/health/ready`)**: Answers *"Is the service currently capable of serving financial traffic and communicating with PostgreSQL?"*

## 2. Probe Specifications

### 2.1 Process Liveness Probe
- **Endpoint**: `GET /api/v1/health/live`
- **Dependency**: In-memory only; does NOT query databases or external caches.
- **Latency**: < 5 milliseconds.
- **Response**: HTTP 200 OK
  ```json
  {
    "status": "alive",
    "service": "ARTHSAVORA",
    "version": "1.1.0",
    "environment": "production",
    "timestamp": "2026-11-19T10:12:00.000000+00:00"
  }
  ```
- **Orchestrator Action**: If this fails for 3 consecutive intervals (15 seconds), the container orchestrator terminates and replaces the container.

### 2.2 Service Readiness Probe
- **Endpoint**: `GET /api/v1/health/ready`
- **Dependency**: Executes bounded query `SELECT 1` with a strict **2.0 second timeout**.
- **Latency**: < 20 milliseconds typical.
- **Success Response**: HTTP 200 OK
  ```json
  {
    "status": "ready",
    "service": "ARTHSAVORA",
    "database": "connected",
    "timestamp": "2026-11-19T10:12:00.000000+00:00"
  }
  ```
- **Failure Response**: HTTP 503 Service Unavailable
  ```json
  {
    "error": {
      "code": "DATABASE_UNAVAILABLE",
      "message": "Readiness probe failed: Database is unreachable."
    }
  }
  ```
- **Load Balancer Action**: If readiness returns 503, the load balancer temporarily removes the container from the active routing pool without restarting it, allowing transient database failover to complete.

## 3. Web Frontend Health Probe
- **Endpoint**: `GET /nginx-health` on port 80/8080 of the web container.
- **Response**: HTTP 200 `healthy\n`.
- **Purpose**: Verifies that the Nginx static file server is running.

## 4. Cross-Reference Links
- Observability Architecture: [OBSERVABILITY_ARCHITECTURE.md](file:///d:/Arthsavora/docs/OBSERVABILITY_ARCHITECTURE.md)
- Operational Monitoring: [OPERATIONAL_MONITORING.md](file:///d:/Arthsavora/docs/OPERATIONAL_MONITORING.md)
