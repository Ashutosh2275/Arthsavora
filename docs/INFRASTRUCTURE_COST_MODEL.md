# ARTHSAVORA — Infrastructure Cost Model & Budget Allocation

## 1. Principles of Cost Engineering

ARTHSAVORA implements a **value-aligned cost architecture** designed for high efficiency and disciplined growth. By utilizing a modular monolith on containerized serverless compute (AWS ECS Fargate or PaaS equivalent) alongside managed open-source datastores (PostgreSQL 18 and Redis 7), the platform achieves enterprise uptime and compliance without the overhead of massive Kubernetes clusters.

## 2. Monthly Cost Projections (AWS Mumbai Region `ap-south-1`)

### 2.1 Stage 1: MVP & Seed Launch (0 - 10,000 Active Users)
| Resource | Specifications | Quantity | Monthly Cost (USD) | Monthly Cost (INR @ 85) |
| :--- | :--- | :--- | :--- | :--- |
| **Compute: ECS Fargate** | 1.0 vCPU, 2GB RAM (Backend API) | 2 tasks (24/7) | $36.00 | ₹3,060 |
| **Web Frontend (Edge)**  | Cloudflare Pages / S3+CloudFront | Serverless | $5.00 | ₹425 |
| **Database: AWS RDS**    | db.t4g.small (PostgreSQL 18, 50GB gp3) | 1 (Single-AZ dev/stg) | $32.00 | ₹2,720 |
| **Cache: ElastiCache**   | cache.t4g.micro (Redis 7) | 1 node | $13.00 | ₹1,105 |
| **Application Load Bal.**| AWS ALB (ap-south-1) | 1 ALB | $22.00 | ₹1,870 |
| **Object Storage (S3)**  | S3 Standard (Receipts/Docs, 20GB) | 20 GB + egress | $3.00 | ₹255 |
| **Edge WAF & DNS**       | Cloudflare Pro Plan | 1 domain | $25.00 | ₹2,125 |
| **Gemini AI API Calls**  | Gemini 2.5 Flash (Financial tools) | Pay-as-you-go | $20.00 | ₹1,700 |
| **Total Baseline**       |                                        |                  | **$156.00** | **₹13,260** |

### 2.2 Stage 2: Growth & Commercial Scaling (10,000 - 100,000 Active Users)
| Resource | Specifications | Quantity | Monthly Cost (USD) | Monthly Cost (INR @ 85) |
| :--- | :--- | :--- | :--- | :--- |
| **Compute: ECS Fargate** | 1.0 vCPU, 2GB RAM Auto-scaling | 4–8 tasks avg | $144.00 | ₹12,240 |
| **Database: AWS RDS**    | db.t4g.medium Multi-AZ (100GB gp3) | Primary + Standby| $115.00 | ₹9,775 |
| **Cache: ElastiCache**   | cache.t4g.small Multi-AZ (Redis 7) | Primary + Replica| $38.00 | ₹3,230 |
| **Application Load Bal.**| AWS ALB (ap-south-1) | 1 ALB (LCUs scaled) | $35.00 | ₹2,975 |
| **Object Storage & KMS** | S3 Standard + Encrypted KMS keys | 250 GB | $15.00 | ₹1,275 |
| **Edge WAF & Bot Mgmt**  | Cloudflare Business Tier | 1 domain | $200.00 | ₹17,000 |
| **Gemini AI API Calls**  | Batch caching & Gemini 2.5 Flash | Pay-as-you-go | $95.00 | ₹8,075 |
| **Total Growth Tier**    |                                        |                  | **$642.00** | **₹54,570** |

## 3. Cost Optimization Controls

1. **Auto-Pause for Non-Production**: Staging environments scale down compute during non-business hours (off-peak 20:00 - 08:00 IST), saving ~35% on staging costs.
2. **Container Right-Sizing**: Uvicorn concurrency is tuned to 4 worker threads per container with async I/O, ensuring high saturation before spinning up new Fargate tasks.
3. **S3 Intelligent Tiering**: Uploaded financial documents older than 90 days transition automatically to S3 Glacier Instant Retrieval.
4. **Cloudflare Cache Offload**: Static frontend assets (`/assets/*.js`, `/assets/*.css`, images, SVGs) are cached at edge nodes for 1 year with content hashes, offloading ~92% of frontend requests.

## 4. Cross-Reference Links
- Infrastructure Architecture: [INFRASTRUCTURE_ARCHITECTURE.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_ARCHITECTURE.md)
- Infrastructure Cost Management: [INFRASTRUCTURE_COST_MANAGEMENT.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_COST_MANAGEMENT.md)
