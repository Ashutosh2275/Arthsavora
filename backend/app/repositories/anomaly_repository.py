"""
Arthsavora Financial Anomaly Repository
Persistence, multi-tenant workspace-isolated CRUD, paginated filters,
review auditing, rules configuration, and whitelist exception enforcement.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.anomaly import DEFAULT_SYSTEM_RULES
from app.infrastructure.database.models.anomaly import (
    AnomalyDetection,
    AnomalyReview,
    DetectionException,
    DetectionRule,
)
from app.infrastructure.database.models.merchant import Merchant
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.workspace_scoped import WorkspaceScopedRepository


class AnomalyRepository:
    """Manages transactional persistence and queries for financial anomaly intelligence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # Detections
    # -------------------------------------------------------------------------

    async def create_detection(self, detection: AnomalyDetection) -> AnomalyDetection:
        self.session.add(detection)
        await self.session.flush()
        return detection

    async def get_detection(
        self,
        detection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[AnomalyDetection]:
        stmt = (
            select(AnomalyDetection)
            .options(
                selectinload(AnomalyDetection.transaction).selectinload(Transaction.category),
                selectinload(AnomalyDetection.account),
                selectinload(AnomalyDetection.resolved_by),
                selectinload(AnomalyDetection.reviews).selectinload(AnomalyReview.reviewer),
            )
            .where(
                AnomalyDetection.id == detection_id,
                AnomalyDetection.workspace_id == workspace_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_detections(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        detection_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AnomalyDetection], int]:
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        conditions = [AnomalyDetection.workspace_id == workspace_id]
        if status:
            conditions.append(AnomalyDetection.status == status)
        if severity:
            conditions.append(AnomalyDetection.severity == severity)
        if detection_type:
            conditions.append(AnomalyDetection.detection_type == detection_type)

        count_stmt = select(func.count(AnomalyDetection.id)).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AnomalyDetection)
            .options(
                selectinload(AnomalyDetection.transaction).selectinload(Transaction.category),
                selectinload(AnomalyDetection.account),
                selectinload(AnomalyDetection.resolved_by),
            )
            .where(*conditions)
            .order_by(AnomalyDetection.detected_at.desc())
            .limit(safe_limit)
            .offset(safe_offset)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def update_status(
        self,
        detection_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        resolved_by_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> Optional[AnomalyDetection]:
        detection = await self.get_detection(detection_id, workspace_id)
        if not detection:
            return None

        detection.status = status
        if status in ("acknowledged", "expected_activity", "dismissed"):
            detection.resolved_at = datetime.utcnow()
            detection.resolved_by_id = resolved_by_id
            if notes:
                detection.resolution_notes = notes

        await self.session.flush()
        return detection

    async def get_detection_for_transaction(
        self,
        transaction_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[AnomalyDetection]:
        stmt = (
            select(AnomalyDetection)
            .where(
                AnomalyDetection.transaction_id == transaction_id,
                AnomalyDetection.workspace_id == workspace_id,
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Reviews
    # -------------------------------------------------------------------------

    async def create_review(self, review: AnomalyReview) -> AnomalyReview:
        self.session.add(review)
        await self.session.flush()
        return review

    async def list_reviews(
        self,
        anomaly_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> List[AnomalyReview]:
        stmt = (
            select(AnomalyReview)
            .options(selectinload(AnomalyReview.reviewer))
            .where(
                AnomalyReview.anomaly_id == anomaly_id,
                AnomalyReview.workspace_id == workspace_id,
            )
            .order_by(AnomalyReview.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # Rules
    # -------------------------------------------------------------------------

    async def get_rules(self, workspace_id: uuid.UUID) -> List[DetectionRule]:
        """
        Lists all active detection rules visible to workspace:
        Custom workspace overrides take precedence over system defaults (workspace_id IS NULL).
        """
        stmt = (
            select(DetectionRule)
            .where(
                or_(
                    DetectionRule.workspace_id == workspace_id,
                    DetectionRule.workspace_id.is_(None),
                )
            )
            .order_by(DetectionRule.workspace_id.desc().nullslast(), DetectionRule.rule_code.asc())
        )
        res = await self.session.execute(stmt)
        all_rules = list(res.scalars().all())

        if not all_rules:
            for r_dict in DEFAULT_SYSTEM_RULES:
                cat_val = r_dict["category"].value if hasattr(r_dict["category"], "value") else str(r_dict["category"])
                sev_val = r_dict["severity"].value if hasattr(r_dict["severity"], "value") else str(r_dict["severity"])
                rule_obj = DetectionRule(
                    workspace_id=None,
                    rule_code=r_dict["rule_code"],
                    name=r_dict["name"],
                    description=r_dict["description"],
                    detection_category=cat_val,
                    severity=sev_val,
                    threshold_config=r_dict["threshold_config"],
                    is_enabled=True,
                    version="1.0.0",
                )
                self.session.add(rule_obj)
            await self.session.flush()
            res = await self.session.execute(stmt)
            all_rules = list(res.scalars().all())

        # Deduplicate: workspace override overrides global system rule
        seen_codes = set()
        deduped = []
        for r in all_rules:
            if r.rule_code not in seen_codes:
                seen_codes.add(r.rule_code)
                deduped.append(r)
        return deduped

    async def get_rule_by_id(
        self,
        rule_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[DetectionRule]:
        stmt = select(DetectionRule).where(
            DetectionRule.id == rule_id,
            or_(
                DetectionRule.workspace_id == workspace_id,
                DetectionRule.workspace_id.is_(None),
            ),
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_or_update_rule(
        self,
        rule: DetectionRule,
    ) -> DetectionRule:
        self.session.add(rule)
        await self.session.flush()
        return rule

    # -------------------------------------------------------------------------
    # Exceptions (Whitelist)
    # -------------------------------------------------------------------------

    async def list_exceptions(
        self,
        workspace_id: uuid.UUID,
        include_expired: bool = False,
    ) -> List[DetectionException]:
        stmt = (
            select(DetectionException)
            .options(
                selectinload(DetectionException.merchant),
                selectinload(DetectionException.category),
                selectinload(DetectionException.account),
                selectinload(DetectionException.created_by),
            )
            .where(DetectionException.workspace_id == workspace_id)
        )
        if not include_expired:
            stmt = stmt.where(
                or_(
                    DetectionException.expires_at.is_(None),
                    DetectionException.expires_at >= date.today(),
                )
            )
        stmt = stmt.order_by(DetectionException.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_exception(
        self,
        exception: DetectionException,
    ) -> DetectionException:
        self.session.add(exception)
        await self.session.flush()
        return exception

    async def delete_exception(
        self,
        exception_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        stmt = select(DetectionException).where(
            DetectionException.id == exception_id,
            DetectionException.workspace_id == workspace_id,
        )
        res = await self.session.execute(stmt)
        exc = res.scalar_one_or_none()
        if not exc:
            return False
        await self.session.delete(exc)
        await self.session.flush()
        return True

    # -------------------------------------------------------------------------
    # Aggregated Analytics & Trends
    # -------------------------------------------------------------------------

    async def get_summary(self, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """Calculates security overview metrics for the workspace."""
        base_cond = (AnomalyDetection.workspace_id == workspace_id)

        # Count by status
        total_stmt = select(func.count(AnomalyDetection.id)).where(base_cond)
        open_stmt = select(func.count(AnomalyDetection.id)).where(base_cond, AnomalyDetection.status.in_(["new", "under_review"]))
        high_critical_stmt = select(func.count(AnomalyDetection.id)).where(
            base_cond,
            AnomalyDetection.status.in_(["new", "under_review"]),
            AnomalyDetection.severity.in_(["high", "critical"]),
        )
        resolved_stmt = select(func.count(AnomalyDetection.id)).where(
            base_cond,
            AnomalyDetection.status.in_(["acknowledged", "expected_activity", "dismissed"]),
        )
        avg_score_stmt = select(func.coalesce(func.avg(AnomalyDetection.risk_score), 0)).where(
            base_cond,
            AnomalyDetection.status.in_(["new", "under_review"]),
        )

        total_count = (await self.session.execute(total_stmt)).scalar() or 0
        open_count = (await self.session.execute(open_stmt)).scalar() or 0
        high_crit_count = (await self.session.execute(high_critical_stmt)).scalar() or 0
        resolved_count = (await self.session.execute(resolved_stmt)).scalar() or 0
        avg_score = float((await self.session.execute(avg_score_stmt)).scalar() or 0.0)

        return {
            "total_detections": total_count,
            "open_anomalies": open_count,
            "high_severity_anomalies": high_crit_count,
            "resolved_anomalies": resolved_count,
            "average_risk_score": round(avg_score, 1),
        }

    async def get_trends(
        self,
        workspace_id: uuid.UUID,
        lookback_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Computes daily anomaly counts broken down by severity over lookback window."""
        start_dt = datetime.utcnow() - timedelta(days=lookback_days)
        stmt = (
            select(
                func.date_trunc("day", AnomalyDetection.detected_at).label("day"),
                AnomalyDetection.severity,
                func.count(AnomalyDetection.id).label("cnt"),
            )
            .where(
                AnomalyDetection.workspace_id == workspace_id,
                AnomalyDetection.detected_at >= start_dt,
            )
            .group_by("day", AnomalyDetection.severity)
            .order_by("day")
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        daily_map: Dict[str, Dict[str, int]] = {}
        for row in rows:
            day_str = row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0])[:10]
            sev = row[1]
            cnt = int(row[2])
            if day_str not in daily_map:
                daily_map[day_str] = {"informational": 0, "low": 0, "medium": 0, "high": 0, "critical": 0, "total": 0}
            daily_map[day_str][sev] = cnt
            daily_map[day_str]["total"] += cnt

        return [{"date": d, **counts} for d, counts in sorted(daily_map.items())]
