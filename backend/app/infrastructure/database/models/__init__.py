"""
Arthsavora Relational Models Aggregation
Exports all SQLAlchemy models for Alembic schema discovery and database operations.
"""

from app.infrastructure.database.models.user import User, UserProfile
from app.infrastructure.database.models.workspace import (
    Workspace,
    WorkspaceMember,
    WorkspaceInvitation,
    WorkspaceType,
    WorkspaceStatus,
    WorkspaceRole,
)
from app.infrastructure.database.models.account import Account, AccountBalanceSnapshot
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.accounting import (
    LedgerAccount,
    JournalEntry,
    JournalLine,
    AccountingPeriod,
)
from app.infrastructure.database.models.acquisition import (
    DataSource,
    ConsentRecord,
    ImportJob,
    ImportFile,
    ImportBatch,
    ImportCandidate,
)
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.merchant import Merchant, MerchantAlias
from app.infrastructure.database.models.rule import ClassificationRule
from app.infrastructure.database.models.intelligence import (
    TransactionClassification,
    UserClassificationFeedback,
)
from app.infrastructure.database.models.budget import (
    Budget,
    BudgetAllocation,
    BudgetRevision,
    BudgetAlert,
)
from app.infrastructure.database.models.goal import (
    FinancialGoal,
    GoalActivity,
)
from app.infrastructure.database.models.recurring import (
    RecurringDefinition,
    RecurringOccurrence,
    Subscription,
    RecurringReminder,
    RecurringSuggestion,
)
from app.infrastructure.database.models.forecast import (
    ForecastRun,
    ForecastPoint,
    FinancialScenario,
    ForecastEvaluation,
)
from app.infrastructure.database.models.anomaly import (
    AnomalyDetection,
    AnomalyReview,
    DetectionRule,
    DetectionException,
)
from app.infrastructure.database.models.assistant import (
    AssistantConversation,
    AssistantMessage,
    AssistantActionDraft,
    AssistantUsageLog,
)
from app.infrastructure.database.models.document import (
    FinancialDocument,
    DocumentExtractionResult,
    DocumentReviewRecord,
    DocumentTransactionAssociation,
)
from app.infrastructure.database.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    PushSubscription,
)
from app.infrastructure.database.models.family import (
    FamilyProfile,
    FamilyExpenseAllocation,
    FamilyExpenseAllocationItem,
    FamilyMemberContribution,
    FamilyAccountShare,
    FamilyActivity,
)

__all__ = [
    "User",
    "UserProfile",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvitation",
    "WorkspaceType",
    "WorkspaceStatus",
    "WorkspaceRole",
    "Account",
    "AccountBalanceSnapshot",
    "Category",
    "Transaction",
    "LedgerAccount",
    "JournalEntry",
    "JournalLine",
    "AccountingPeriod",
    "DataSource",
    "ConsentRecord",
    "ImportJob",
    "ImportFile",
    "ImportBatch",
    "ImportCandidate",
    "AuditLog",
    "Merchant",
    "MerchantAlias",
    "ClassificationRule",
    "TransactionClassification",
    "UserClassificationFeedback",
    "Budget",
    "BudgetAllocation",
    "BudgetRevision",
    "BudgetAlert",
    "FinancialGoal",
    "GoalActivity",
    "RecurringDefinition",
    "RecurringOccurrence",
    "Subscription",
    "RecurringReminder",
    "RecurringSuggestion",
    "ForecastRun",
    "ForecastPoint",
    "FinancialScenario",
    "ForecastEvaluation",
    "AnomalyDetection",
    "AnomalyReview",
    "DetectionRule",
    "DetectionException",
    "AssistantConversation",
    "AssistantMessage",
    "AssistantActionDraft",
    "AssistantUsageLog",
    "FinancialDocument",
    "DocumentExtractionResult",
    "DocumentReviewRecord",
    "DocumentTransactionAssociation",
    "Notification",
    "NotificationDelivery",
    "NotificationPreference",
    "NotificationTemplate",
    "PushSubscription",
    "FamilyProfile",
    "FamilyExpenseAllocation",
    "FamilyExpenseAllocationItem",
    "FamilyMemberContribution",
    "FamilyAccountShare",
    "FamilyActivity",
]
