# ARTHSAVORA — Deployment Topology

## 1. Top-Level Physical Topology

ARTHSAVORA deploys into a regional Cloud Virtual Private Cloud (VPC) in **AWS Mumbai (ap-south-1)** or **GCP Mumbai (asia-south1)** to ensure strict compliance with Indian data localization requirements.

```
                                 [ Cloudflare Edge CDN / WAF ]
                                                |
               +--------------------------------+-------------------------------+
               | HTTPS (ap-south-1 Edge)                                        | HTTPS
               v                                                                v
+-------------------------------+                            +----------------------------------+
|   VPC Public Subnet Zone A    |                            |     VPC Public Subnet Zone B     |
| [ Application Load Balancer ] |                            |  [ Application Load Balancer ]   |
+---------------+---------------+                            +------------------+---------------+
                |                                                               |
  +-------------+-------------------------------+               +---------------+--------------+
  | Private Subnet A (Compute)                  |               | Private Subnet B (Compute)   |
  | [ FastAPI ECS Fargate Task 1 ]              |               | [ FastAPI ECS Fargate Task 2]|
  | [ Port 8000 (Internal) ]                    |               | [ Port 8000 (Internal) ]     |
  +-------------+-------------------------------+               +---------------+--------------+
                |                                                               |
  +-------------+-------------------------------+               +---------------+--------------+
  | Isolated Database Subnet A                  |               | Isolated Database Subnet B   |
  | [ PostgreSQL 18 Primary (RDS Multi-AZ) ] <===== Sync Rep =====> [ PostgreSQL 18 Standby ]  |
  | [ Redis 7 Primary Cluster Node ]            |               | [ Redis 7 Replica Node ]     |
  +---------------------------------------------+               +------------------------------+
```

## 2. Network Segmentation & Security Groups

1. **Public Load Balancer Security Group**:
   - Inbound: Ports `443` (HTTPS) and `80` (HTTP -> 301 redirect to HTTPS) restricted to Cloudflare IP ranges.
   - Outbound: Port `8000` to Compute Security Group.
2. **Compute (ECS Fargate / Container) Security Group**:
   - Inbound: Port `8000` from Load Balancer Security Group ONLY.
   - Outbound: Port `5432` to Database Security Group, Port `6379` to Cache Security Group, Port `443` outbound to NAT Gateway (for external banking APIs and Gemini AI).
3. **Database Security Group**:
   - Inbound: Port `5432` from Compute Security Group ONLY.
   - Outbound: None (Database isolated).
4. **Cache Security Group**:
   - Inbound: Port `6379` from Compute Security Group ONLY.
   - Outbound: None.

## 3. Container Configurations & Specifications

| Component | Image / Runtime | CPU Allocation | Memory Allocation | Scaling Bounds |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API** | Multi-stage Python 3.11-slim (`backend/Dockerfile`) | 1.0 vCPU | 2048 MB | Min: 2, Max: 10 tasks |
| **Web Frontend**| Multi-stage Nginx 1.27-alpine (`apps/web/Dockerfile`)| 0.25 vCPU | 512 MB | Min: 2, Max: 4 tasks |
| **PostgreSQL**  | AWS RDS db.t4g.medium (2 vCPU, 4GB RAM) Multi-AZ    | Dedicated | Dedicated | 100 GB gp3 (Auto-expand)|
| **Redis Cache** | AWS ElastiCache cache.t4g.micro                     | Dedicated | 0.5 GB | Single Primary + Replica|

## 4. Cross-Reference Links
- Infrastructure Architecture: [INFRASTRUCTURE_ARCHITECTURE.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_ARCHITECTURE.md)
- Scaling Strategy: [SCALING_STRATEGY.md](file:///d:/Arthsavora/docs/SCALING_STRATEGY.md)
- Backup Operations: [BACKUP_OPERATIONS.md](file:///d:/Arthsavora/docs/BACKUP_OPERATIONS.md)
