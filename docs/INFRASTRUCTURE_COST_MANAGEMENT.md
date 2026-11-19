# ARTHSAVORA — Infrastructure Cost Management and Budget Governance

## 1. Budget Governance Principles

ARTHSAVORA maintains strict budget governance to prevent cloud cost overruns while maintaining institutional reliability:

1. **Tagging Policy**: 100% of cloud resources MUST be tagged with `Project=Arthsavora`, `Environment=Production|Staging|Development`, and `Owner=FinOps`.
2. **Automated Anomaly Detection**: AWS Cost Anomaly Detection is configured with an alert threshold of **$25 daily variance**, sending immediate notifications to Slack `#finops-alerts`.
3. **Monthly Hard Budget**:
   - Staging: $200/month maximum limit.
   - Production: $1,000/month initial budget gate (triggers executive notification at 80% utilization).

## 2. Waste Elimination Practices

- **Ephemeral Staging Teardown**: Staging compute tasks scale down to 0 during weekends unless active testing is registered.
- **Old Snapshot Cleanup**: Automated lifecycle rule deletes non-compliance RDS snapshots older than 35 days.
- **Log Data Expiration**: CloudWatch log groups have strict retention policies (30 days for INFO, 90 days for ERROR).
- **NAT Gateway Optimization**: Internal VPC endpoints (AWS PrivateLink) are utilized for Amazon S3 and Secrets Manager, avoiding costly per-GB NAT Gateway data processing fees.

## 3. Financial Unit Economics

```
Cost Per Active User (CPAU) = Total Monthly Infrastructure Spend / Monthly Active Users (MAU)
Target: CPAU < ₹5.00 / month ($0.06 / user)
```
At 25,000 active users with $350 total monthly infrastructure expenditure:
`CPAU = $350 / 25,000 = $0.014 / user (approx. ₹1.19 / user)`
Achieving exceptional unit economics well within target margins.

## 4. Cross-Reference Links
- Infrastructure Cost Model: [INFRASTRUCTURE_COST_MODEL.md](file:///d:/Arthsavora/docs/INFRASTRUCTURE_COST_MODEL.md)
- Scaling Strategy: [SCALING_STRATEGY.md](file:///d:/Arthsavora/docs/SCALING_STRATEGY.md)
