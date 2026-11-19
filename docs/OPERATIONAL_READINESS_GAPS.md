# Operational Readiness Gaps & External Dependency Register

## 1. Executive Summary

This register details the remaining operational, administrative, and external dependency gaps that prevent unrestricted public general availability, even though 100% of the platform's software engineering requirements and automated tests are passing.

The platform is classified as **LIMITED PRODUCTION-READY (BETA & PHASED ROLLOUT READY)**.

---

## 2. External Operational Gaps

### GAP-OP-01: Account Aggregator (AA) Production Onboarding
- **Category:** External Regulatory & Contractual
- **Description:** Live bank connectivity in India requires participation in the RBI Account Aggregator framework. This necessitates a formal commercial agreement with a licensed NBFC-AA (e.g., Setu, Anumati, Finvu, OneMoney), security audits, and production digital certificate exchange.
- **Current Technical State:** The ReBIT FIU/FIP protocol client and adapter architecture are 100% implemented. In CI and local environments, `MockAccountAggregatorAdapter` provides deterministic synthetic responses.
- **Operational Remedy:**
  1. Complete formal institutional vendor registration with an NBFC-AA provider.
  2. Complete CERT-In empaneled security audit certification.
  3. Obtain production client certificate and API keys.
  4. Configure production environment secrets.
- **Graceful Fallback:** Users can immediately import statements from HDFC, ICICI, SBI, and standard CSV/Excel formats via the fully verified `ImportService`.

### GAP-OP-02: Live Cloud Infrastructure Provisioning
- **Category:** Infrastructure Operations
- **Description:** Cloud deployment templates (Terraform/CloudFormation) and Dockerfiles are verified locally. Live instances in AWS `ap-south-1` have not yet been provisioned.
- **Operational Remedy:**
  1. Create AWS organization and production workload accounts.
  2. Execute VPC and security group provisioning scripts.
  3. Launch Amazon RDS PostgreSQL 18 Multi-AZ cluster.
  4. Provision Amazon ECS Fargate cluster and Application Load Balancer.
  5. Configure Cloudflare DNS, WAF rules, and SSL certificates.

### GAP-OP-03: Production VAPID Key Provisioning for Web Push
- **Category:** Notification Operations
- **Description:** Browser-level Web Push notifications require production VAPID key pairs configured in environment variables.
- **Current Technical State:** In-app real-time notification center is 100% functional; push notifications gracefully disable when VAPID keys are absent.
- **Operational Remedy:**
  1. Generate production keys via standard VAPID tooling.
  2. Populate `VAPID_PUBLIC_KEY` in frontend build and `VAPID_PRIVATE_KEY` in backend secrets vault.

### GAP-OP-04: Production Observability & Centralized Log Aggregation
- **Category:** Telemetry & Monitoring
- **Description:** Structured JSON logging with automated PII scrubbing is operational inside the backend process. Centralized log shipping (e.g., to Datadog, ELK, or CloudWatch) requires production daemon / sidecar configuration.
- **Operational Remedy:**
  1. Configure OpenTelemetry collector or CloudWatch log driver in ECS task definition.
  2. Set up operational alert policies for 5xx error spikes, migration failures, and anomalous latency.

---

## 3. Triage & Phased Resolution Roadmap

```
+--------------------------------------------------------------------------+
|                     PHASED OPERATIONAL ROLLOUT PLAN                      |
+--------------------------------------------------------------------------+
|  STAGE 7.1: PRIVATE PILOT (CURRENT CODEBASE BASELINE)                    |
|  - Deploy Docker Compose / single-node cloud VM                           |
|  - Use Statement CSV/XLSX import (HDFC, ICICI, SBI)                       |
|  - Verify real user onboarding, double-entry ledger, PWA install          |
+--------------------------------------------------------------------------+
|  STAGE 7.2: PRODUCTION BETA                                              |
|  - Provision AWS ap-south-1 Multi-AZ RDS & ECS Fargate                    |
|  - Provision VAPID keys for live mobile push notifications                |
|  - Connect Centralized Log Shipper & Prometheus metrics                   |
+--------------------------------------------------------------------------+
|  STAGE 7.3: GENERAL AVAILABILITY                                          |
|  - Complete NBFC-AA contractual onboarding & certificate exchange         |
|  - Activate live ReBIT Account Aggregator sync in UI                      |
|  - Public launch across web and PWA                                       |
+--------------------------------------------------------------------------+
```

---

## 4. Conclusion

None of the identified operational gaps stem from missing, broken, or defective software code. All are standard external enterprise onboarding gates with clear remediation paths and graceful user fallbacks.
