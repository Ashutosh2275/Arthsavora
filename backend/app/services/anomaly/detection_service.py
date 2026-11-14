"""
Arthsavora Financial Anomaly Detection Service
Orchestrates the hybrid detection pipeline across deterministic rules,
statistical MAD/IQR models, and machine learning Isolation Forest inference.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.anomaly import (
    AnomalyEvidenceVO,
    CandidateTransactionVO,
    DEFAULT_SYSTEM_RULES,
    detect_category_spike_anomaly,
    detect_merchant_amount_anomaly,
    detect_ml_isolation_forest,
    evaluate_deterministic_rules,
    extract_ml_feature_vector,
    matches_detection_exception,
    synthesize_hybrid_anomaly,
)
from app.infrastructure.database.models.anomaly import AnomalyDetection, DetectionRule
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.anomaly_repository import AnomalyRepository
from app.schemas.anomaly_schema import AnomalyDetectionResponse, AnomalyTransactionSummary
from app.services.anomaly.feature_pipeline_service import FeaturePipelineService


class AnomalyDetectionService:
    """Core service executing hybrid financial anomaly detection and risk scoring."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnomalyRepository(db)
        self.features = FeaturePipelineService(db)

    async def evaluate_transaction(
        self,
        workspace_id: uuid.UUID,
        transaction_id: uuid.UUID,
        persist: bool = True,
        force_recheck: bool = False,
    ) -> Optional[AnomalyDetection]:
        """
        Runs the complete hybrid anomaly detection pipeline on a single transaction.
        Idempotent: prevents duplicate open alerts for the same underlying transaction.
        """
        # 1. Load candidate transaction
        tx = await self.features.get_candidate_transaction(transaction_id, workspace_id)
        if not tx:
            return None

        # Check existing anomaly record
        existing = await self.repo.get_detection_for_transaction(transaction_id, workspace_id)
        if existing and not force_recheck:
            return existing

        # 2. Check Whitelist Exceptions
        exceptions = await self.repo.list_exceptions(workspace_id, include_expired=False)
        exc_dicts = [
            {
                "id": e.id,
                "rule_code": e.rule_code,
                "merchant_id": e.merchant_id,
                "category_id": e.category_id,
                "account_id": e.account_id,
                "merchant_name_pattern": e.merchant_name_pattern,
                "max_amount_paise": e.max_amount_paise,
                "expires_at": e.expires_at,
            }
            for e in exceptions
        ]
        matched_exc = matches_detection_exception(tx, exc_dicts, as_of_date=tx.transaction_date)
        if matched_exc:
            # Explicitly whitelisted by user: do not create active alert
            return None

        evidences: List[AnomalyEvidenceVO] = []

        # 3. Load Active Rules (Workspace Custom + Global Defaults)
        rules = await self.repo.get_rules(workspace_id)
        rule_dicts = [
            {
                "rule_code": r.rule_code,
                "name": r.name,
                "severity": r.severity,
                "threshold_config": r.threshold_config,
                "is_enabled": r.is_enabled,
            }
            for r in rules
        ] if rules else DEFAULT_SYSTEM_RULES

        # 4. Contextual Data for Rules & Statistics
        recent_txs = await self.features.get_recent_transactions(workspace_id, tx.created_at, lookback_hours=48)
        recurring_info = await self.features.get_recurring_commitment_context(workspace_id, tx)

        # 5. Deterministic Rules Evaluation
        rule_evidences = evaluate_deterministic_rules(
            tx=tx,
            rules=rule_dicts,
            recent_transactions=recent_txs,
            recurring_info=recurring_info,
        )
        evidences.extend(rule_evidences)

        # 6. Statistical Outlier Detection (MAD on Merchant)
        merchant_history = await self.features.get_merchant_historical_amounts(
            workspace_id=workspace_id,
            merchant_id=tx.merchant_id,
            merchant_name=tx.merchant_name,
            exclude_transaction_id=tx.id,
            lookback_days=180,
        )
        stat_merchant_ev = detect_merchant_amount_anomaly(tx, merchant_history, min_observations=5)
        if stat_merchant_ev:
            evidences.append(stat_merchant_ev)

        # 7. Statistical Category Spike Detection
        if tx.category_id:
            cat_history, cur_month_tot = await self.features.get_category_metrics(
                workspace_id=workspace_id,
                category_id=tx.category_id,
                target_date=tx.transaction_date,
            )
            stat_cat_ev = detect_category_spike_anomaly(tx, cat_history, cur_month_tot, min_days=14)
            if stat_cat_ev:
                evidences.append(stat_cat_ev)

        # 8. Machine Learning Isolation Forest (when sufficient data >= 30 samples)
        ml_matrix = await self.features.extract_ml_training_matrix(workspace_id, lookback_days=90)
        if len(ml_matrix) >= 30:
            cand_features = extract_ml_feature_vector(tx)
            ml_ev = detect_ml_isolation_forest(tx, ml_matrix, cand_features, min_training_samples=30)
            if ml_ev:
                evidences.append(ml_ev)

        # 9. Hybrid Synthesis & Scoring
        hybrid_res = synthesize_hybrid_anomaly(evidences)
        if not hybrid_res.is_anomalous:
            return None

        # 10. Persist or Update Anomaly Record
        if not persist:
            return AnomalyDetection(
                workspace_id=workspace_id,
                transaction_id=tx.id,
                account_id=tx.account_id,
                detection_type=hybrid_res.detection_type,
                detection_method=hybrid_res.detection_method,
                severity=hybrid_res.severity.value,
                risk_score=hybrid_res.risk_score,
                status="new",
                explanation=hybrid_res.explanation,
                evidence_metadata=hybrid_res.evidence_metadata,
                rule_code=hybrid_res.rule_code,
                model_version="v1.0.0",
                detected_at=datetime.utcnow(),
            )

        if existing:
            existing.detection_type = hybrid_res.detection_type
            existing.detection_method = hybrid_res.detection_method
            existing.severity = hybrid_res.severity.value
            existing.risk_score = hybrid_res.risk_score
            existing.explanation = hybrid_res.explanation
            existing.evidence_metadata = hybrid_res.evidence_metadata
            existing.rule_code = hybrid_res.rule_code
            await self.db.flush()
            return existing

        detection = AnomalyDetection(
            workspace_id=workspace_id,
            transaction_id=tx.id,
            account_id=tx.account_id,
            detection_type=hybrid_res.detection_type,
            detection_method=hybrid_res.detection_method,
            severity=hybrid_res.severity.value,
            risk_score=hybrid_res.risk_score,
            status="new",
            explanation=hybrid_res.explanation,
            evidence_metadata=hybrid_res.evidence_metadata,
            rule_code=hybrid_res.rule_code,
            model_version="v1.0.0",
            detected_at=datetime.utcnow(),
        )
        return await self.repo.create_detection(detection)

    async def scan_recent_transactions(
        self,
        workspace_id: uuid.UUID,
        lookback_days: int = 7,
        force_recheck: bool = False,
    ) -> List[AnomalyDetection]:
        """Scans all posted transactions in the lookback window for anomalies."""
        start_date = date.today() - timedelta(days=lookback_days)
        stmt = (
            select(Transaction.id)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.is_deleted == False,
                Transaction.status == "posted",
                Transaction.transaction_date >= start_date,
            )
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(100)
        )
        res = await self.db.execute(stmt)
        tx_ids = [r[0] for r in res.all()]

        detected: List[AnomalyDetection] = []
        for tid in tx_ids:
            anom = await self.evaluate_transaction(
                workspace_id=workspace_id,
                transaction_id=tid,
                persist=True,
                force_recheck=force_recheck,
            )
            if anom:
                detected.append(anom)

        # Reload with eager associations so ORM attributes are never unloaded or expired
        reloaded: List[AnomalyDetection] = []
        for d in detected:
            item = await self.repo.get_detection(d.id, workspace_id)
            if item:
                reloaded.append(item)
        return reloaded

    @staticmethod
    def map_to_dto(d: AnomalyDetection) -> AnomalyDetectionResponse:
        """Converts ORM entity to typed Pydantic response DTO."""
        tx_summary = None
        insp = inspect(d)
        if "transaction" not in insp.unloaded and d.transaction:
            t = d.transaction
            t_insp = inspect(t)
            category_name = t.category.name if ("category" not in t_insp.unloaded and t.category) else None
            account_name = t.account.name if ("account" not in t_insp.unloaded and t.account) else None
            merchant_name = getattr(t, "merchant_name", None) or (t.merchant.name if ("merchant" not in t_insp.unloaded and getattr(t, "merchant", None)) else None)

            tx_summary = AnomalyTransactionSummary(
                id=t.id,
                transaction_date=t.transaction_date,
                amount_paise=t.amount_paise,
                amount=Decimal(t.amount_paise) / Decimal("100.0000"),
                currency=t.currency,
                direction=t.direction,
                description=t.description or "",
                merchant_name=merchant_name,
                category_name=category_name,
                account_name=account_name,
            )

        reviews_dtos = []
        if "reviews" not in insp.unloaded and d.reviews:
            for r in d.reviews:
                reviews_dtos.append(
                    {
                        "id": r.id,
                        "anomaly_id": r.anomaly_id,
                        "workspace_id": r.workspace_id,
                        "reviewer_id": r.reviewer_id,
                        "action": r.action,
                        "reason": r.reason,
                        "notes": r.notes,
                        "created_at": r.created_at,
                    }
                )

        return AnomalyDetectionResponse(
            id=d.id,
            workspace_id=d.workspace_id,
            transaction_id=d.transaction_id,
            account_id=d.account_id,
            detection_type=d.detection_type,
            detection_method=d.detection_method,
            severity=d.severity,
            risk_score=d.risk_score,
            status=d.status,
            explanation=d.explanation,
            evidence_metadata=d.evidence_metadata or {},
            rule_code=d.rule_code,
            model_version=d.model_version,
            detected_at=d.detected_at,
            resolved_at=d.resolved_at,
            resolved_by_id=d.resolved_by_id,
            resolution_notes=d.resolution_notes,
            transaction=tx_summary,
            reviews=reviews_dtos,
        )
