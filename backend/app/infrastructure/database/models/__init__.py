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
]
