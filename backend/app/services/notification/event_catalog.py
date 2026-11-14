"""
Arthsavora Notification Event Catalog
Standardized domain event constructors across all 10 financial categories.
Enforces non-alarmist phrasing, explicit prediction labeling, and deterministic deduplication.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from app.domain.notification import (
    NotificationCategory,
    NotificationEventType,
    NotificationPayloadVO,
    NotificationSeverity,
    generate_deduplication_key,
)


class NotificationEventFactory:
    """Factory methods for unified notification payloads."""

    # -------------------------------------------------------------------------
    # A. Transaction Notifications
    # -------------------------------------------------------------------------
    @staticmethod
    def transaction_recorded(
        user_id: UUID,
        workspace_id: UUID,
        transaction_id: UUID,
        amount_paise: int,
        merchant_name: str,
        transaction_type: str = "DEBIT",
    ) -> NotificationPayloadVO:
        amt_str = f"₹{amount_paise / 100:.2f}"
        title = f"Transaction Recorded: {amt_str}"
        msg = f"A {transaction_type.lower()} transaction of {amt_str} at {merchant_name} has been recorded to your ledger."
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.TRANSACTION,
            event_type=NotificationEventType.TRANSACTION_RECORDED,
            title=title,
            message=msg,
            severity=NotificationSeverity.INFO,
            related_resource_type="transaction",
            related_resource_id=str(transaction_id),
            action_url=f"/transactions?id={transaction_id}",
            metadata={"amount_paise": amount_paise, "merchant": merchant_name},
            deduplication_key=generate_deduplication_key(user_id, NotificationEventType.TRANSACTION_RECORDED, str(transaction_id)),
        )

    # -------------------------------------------------------------------------
    # B. Budget Notifications
    # -------------------------------------------------------------------------
    @staticmethod
    def budget_threshold_reached(
        user_id: UUID,
        workspace_id: UUID,
        budget_id: UUID,
        category_name: str,
        percentage_spent: float,
        period_str: str,
    ) -> NotificationPayloadVO:
        severity = NotificationSeverity.CRITICAL if percentage_spent >= 100 else NotificationSeverity.WARNING
        title = f"Budget Alert: {category_name} at {percentage_spent:.0f}%"
        msg = f"Your {category_name} budget for {period_str} has reached {percentage_spent:.1f}% of its allocated limit."
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.BUDGET,
            event_type=NotificationEventType.BUDGET_THRESHOLD_REACHED,
            title=title,
            message=msg,
            severity=severity,
            related_resource_type="budget",
            related_resource_id=str(budget_id),
            action_url="/budgets",
            metadata={"percentage_spent": percentage_spent, "period": period_str},
            deduplication_key=generate_deduplication_key(
                user_id,
                NotificationEventType.BUDGET_THRESHOLD_REACHED,
                str(budget_id),
                f"{int(percentage_spent)}_{period_str}",
            ),
        )

    # -------------------------------------------------------------------------
    # C. Financial Goals
    # -------------------------------------------------------------------------
    @staticmethod
    def goal_milestone_reached(
        user_id: UUID,
        workspace_id: UUID,
        goal_id: UUID,
        goal_name: str,
        percentage_saved: float,
    ) -> NotificationPayloadVO:
        title = f"Goal Milestone: {goal_name} reached {percentage_saved:.0f}%"
        msg = f"Congratulations! You have reached {percentage_saved:.1f}% of your target for '{goal_name}'."
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.GOAL,
            event_type=NotificationEventType.GOAL_MILESTONE,
            title=title,
            message=msg,
            severity=NotificationSeverity.SUCCESS,
            related_resource_type="goal",
            related_resource_id=str(goal_id),
            action_url="/goals",
            metadata={"percentage_saved": percentage_saved},
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.GOAL_MILESTONE, str(goal_id), f"{int(percentage_saved)}"
            ),
        )

    # -------------------------------------------------------------------------
    # D. Recurring Finance & Reminders
    # -------------------------------------------------------------------------
    @staticmethod
    def recurring_payment_due(
        user_id: UUID,
        workspace_id: UUID,
        occurrence_id: UUID,
        name: str,
        amount_paise: int,
        due_date_str: str,
        days_remaining: int,
    ) -> NotificationPayloadVO:
        amt_str = f"₹{amount_paise / 100:.2f}"
        if days_remaining == 0:
            title = f"Payment Due Today: {name} ({amt_str})"
            msg = f"Expected payment of {amt_str} for {name} is scheduled for today ({due_date_str}). Note: This reminder does not confirm payment."
            sev = NotificationSeverity.WARNING
        elif days_remaining < 0:
            title = f"Payment Overdue: {name} ({amt_str})"
            msg = f"Scheduled payment of {amt_str} for {name} was expected on {due_date_str} and has not yet been matched to a ledger transaction."
            sev = NotificationSeverity.CRITICAL
        else:
            title = f"Upcoming Payment: {name} in {days_remaining} days"
            msg = f"Expected payment of {amt_str} for {name} is scheduled for {due_date_str}."
            sev = NotificationSeverity.INFO

        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.RECURRING,
            event_type=NotificationEventType.PAYMENT_DUE,
            title=title,
            message=msg,
            severity=sev,
            related_resource_type="recurring_occurrence",
            related_resource_id=str(occurrence_id),
            action_url="/recurring",
            metadata={"amount_paise": amount_paise, "due_date": due_date_str, "days_remaining": days_remaining},
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.PAYMENT_DUE, str(occurrence_id), due_date_str
            ),
        )

    # -------------------------------------------------------------------------
    # E. Forecasting & Predictive Intelligence (Strictly labeled as estimates)
    # -------------------------------------------------------------------------
    @staticmethod
    def forecast_budget_exhaustion(
        user_id: UUID,
        workspace_id: UUID,
        category_name: str,
        projected_exhaustion_date: str,
    ) -> NotificationPayloadVO:
        title = f"[Estimate] Projected Budget Exhaustion: {category_name}"
        msg = f"Based on historical spending velocity, your {category_name} budget is estimated to deplete by {projected_exhaustion_date}. This is an informational forecast, not a guaranteed outcome."
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.FORECAST,
            event_type=NotificationEventType.FORECAST_BUDGET_EXHAUSTION,
            title=title,
            message=msg,
            severity=NotificationSeverity.INFO,
            related_resource_type="forecast",
            action_url="/forecast",
            metadata={"category": category_name, "exhaustion_date": projected_exhaustion_date},
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.FORECAST_BUDGET_EXHAUSTION, category_name, projected_exhaustion_date
            ),
        )

    # -------------------------------------------------------------------------
    # F. Financial Anomaly & Risk (Non-alarmist, never labeled as confirmed fraud)
    # -------------------------------------------------------------------------
    @staticmethod
    def anomaly_detected(
        user_id: UUID,
        workspace_id: UUID,
        anomaly_id: UUID,
        merchant_or_category: str,
        amount_paise: int,
        detection_reason: str,
    ) -> NotificationPayloadVO:
        amt_str = f"₹{amount_paise / 100:.2f}"
        title = f"Unusual Activity Noted: {amt_str} at {merchant_or_category}"
        msg = f"A transaction of {amt_str} deviated from your typical spending pattern ({detection_reason}). Please review this activity. Note: Unusual activity is not automatically unauthorized."
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.ANOMALY,
            event_type=NotificationEventType.ANOMALY_UNUSUAL_TRANSACTION,
            title=title,
            message=msg,
            severity=NotificationSeverity.WARNING,
            related_resource_type="anomaly",
            related_resource_id=str(anomaly_id),
            action_url="/anomalies",
            metadata={"amount_paise": amount_paise, "reason": detection_reason},
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.ANOMALY_UNUSUAL_TRANSACTION, str(anomaly_id)
            ),
        )

    # -------------------------------------------------------------------------
    # G. Document & Receipt Processing
    # -------------------------------------------------------------------------
    @staticmethod
    def document_processed(
        user_id: UUID,
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        merchant_name: Optional[str] = None,
        total_paise: Optional[int] = None,
    ) -> NotificationPayloadVO:
        if merchant_name and total_paise:
            amt_str = f"₹{total_paise / 100:.2f}"
            title = f"Receipt Ready for Review: {merchant_name} ({amt_str})"
            msg = f"Receipt '{filename}' has been processed. Extracted {amt_str} from {merchant_name}. Please review and confirm to post to ledger."
        else:
            title = f"Document Processed: {filename}"
            msg = f"OCR scanning completed for '{filename}'. Please review extracted figures in your document center."

        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.DOCUMENT,
            event_type=NotificationEventType.DOCUMENT_PROCESSED,
            title=title,
            message=msg,
            severity=NotificationSeverity.INFO,
            related_resource_type="document",
            related_resource_id=str(document_id),
            action_url=f"/documents?id={document_id}",
            metadata={"filename": filename},
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.DOCUMENT_PROCESSED, str(document_id)
            ),
        )

    # -------------------------------------------------------------------------
    # H. AI Assistant
    # -------------------------------------------------------------------------
    @staticmethod
    def assistant_action_completed(
        user_id: UUID,
        workspace_id: UUID,
        action_id: UUID,
        action_title: str,
    ) -> NotificationPayloadVO:
        title = f"Assistant Action Completed: {action_title}"
        msg = f"The requested assistant action '{action_title}' has been successfully executed."
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            workspace_id=workspace_id,
            category=NotificationCategory.ASSISTANT,
            event_type=NotificationEventType.ASSISTANT_ACTION_COMPLETED,
            title=title,
            message=msg,
            severity=NotificationSeverity.SUCCESS,
            related_resource_type="assistant_action",
            related_resource_id=str(action_id),
            action_url="/assistant",
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.ASSISTANT_ACTION_COMPLETED, str(action_id)
            ),
        )

    # -------------------------------------------------------------------------
    # I. Security & Account Events (Zero secret exposure)
    # -------------------------------------------------------------------------
    @staticmethod
    def security_alert(
        user_id: UUID,
        title: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.CRITICAL,
    ) -> NotificationPayloadVO:
        return NotificationPayloadVO(
            recipient_user_id=user_id,
            category=NotificationCategory.SECURITY,
            event_type=NotificationEventType.SECURITY_AUTH_EVENT,
            title=title,
            message=message,
            severity=severity,
            action_url="/settings/security",
            deduplication_key=generate_deduplication_key(
                user_id, NotificationEventType.SECURITY_AUTH_EVENT, None, datetime.now(timezone.utc).strftime("%Y%m%d%H")
            ),
        )
