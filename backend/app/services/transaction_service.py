"""
Arthsavora Transaction Application Service
Orchestrates operational transaction intake, Money value object validation,
idempotent deduplication via external references, lifecycle state machine transitions,
paired transfer leg synchronization, cumulative refund bounds enforcement,
compensating reversals, and auditable history.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.domain.events import (
    create_transaction_created_event,
    create_transaction_posted_event,
    create_transaction_cancelled_event,
    create_transaction_reversed_event,
    create_transaction_refunded_event,
    create_transfer_created_event,
)
from app.domain.exceptions import BusinessRuleViolationError, DomainError
from app.domain.money import Money
from app.domain.rules import (
    validate_ai_prediction_invariants,
    validate_refund_invariants,
    validate_transfer_invariants,
)
from app.domain.transaction_types import (
    TransactionDirection,
    TransactionSourceType,
    TransactionStatus,
    TransactionType,
    resolve_transaction_direction,
    validate_transaction_lifecycle_transition,
)
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    TransactionCancelRequest,
    TransactionCreateRequest,
    TransactionHistoryEntry,
    TransactionPostRequest,
    TransactionRefundRequest,
    TransactionResponse,
    TransactionReverseRequest,
    TransactionUpdateRequest,
    TransferCreateRequest,
    TransferResponse,
)


class TransactionService:
    """Service orchestrating operational financial movements and data integrity."""

    @classmethod
    def format_transaction_response(cls, tx: Transaction) -> TransactionResponse:
        """Serializes Transaction entity into public TransactionResponse DTO."""
        amount_str = (
            Money.from_minor_units(tx.amount_paise, tx.currency).to_decimal_string()
            if tx.amount_paise is not None
            else str(tx.amount)
        )
        return TransactionResponse(
            id=tx.id,
            workspace_id=tx.workspace_id,
            account_id=tx.account_id,
            amount=amount_str,
            amount_paise=tx.amount_paise,
            currency=tx.currency,
            transaction_type=tx.transaction_type,
            direction=tx.direction,
            transaction_date=tx.transaction_date,
            settlement_date=tx.settlement_date,
            description=tx.description,
            merchant_name=tx.merchant_name,
            category_id=tx.category_id,
            status=tx.status,
            source_type=tx.source_type,
            source_reference=tx.source_reference,
            external_transaction_id=tx.external_transaction_id,
            related_transaction_id=tx.related_transaction_id,
            original_transaction_id=tx.original_transaction_id,
            transfer_id=tx.transfer_id,
            created_by_id=tx.created_by_id,
            reversal_reason=tx.reversal_reason,
            is_ai_predicted=tx.is_ai_predicted,
            ai_confidence=float(tx.ai_confidence) if tx.ai_confidence is not None else None,
            source_provenance=tx.source_provenance or {},
            metadata=tx.metadata_payload or {},
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )

    @staticmethod
    def _apply_balance_mutation(
        account: Account,
        amount_paise: int,
        direction: str,
        tx_type: Optional[str] = None,
        is_reversal: bool = False,
    ) -> None:
        """
        Applies or reverses balance updates for a posted transaction according to account type and direction.
        """
        eff_dir = direction
        if is_reversal:
            if direction == TransactionDirection.INFLOW.value:
                eff_dir = TransactionDirection.OUTFLOW.value
            elif direction == TransactionDirection.OUTFLOW.value:
                eff_dir = TransactionDirection.INFLOW.value

        acct_type = str(account.account_type).lower().strip()
        type_str = (tx_type or "").lower().strip()

        if acct_type in ("credit_card", "business_credit_card"):
            if eff_dir == TransactionDirection.OUTFLOW.value:
                account.outstanding_liability_paise = (account.outstanding_liability_paise or 0) + amount_paise
                account.current_book_balance_paise -= amount_paise
            elif eff_dir == TransactionDirection.INFLOW.value:
                account.outstanding_liability_paise = max(0, (account.outstanding_liability_paise or 0) - amount_paise)
                account.current_book_balance_paise += amount_paise

            if account.credit_limit_paise is not None:
                account.available_balance_paise = max(
                    0,
                    account.credit_limit_paise - (account.outstanding_liability_paise or 0) - (account.pending_amount_paise or 0)
                )

        elif acct_type in ("loan", "loan_account"):
            if type_str == TransactionType.LOAN_DISBURSAL.value:
                account.outstanding_liability_paise = (account.outstanding_liability_paise or 0) + amount_paise
                account.current_book_balance_paise -= amount_paise
            elif type_str in (TransactionType.LOAN_PRINCIPAL_REPAYMENT.value, TransactionType.CREDIT_CARD_PAYMENT.value) or eff_dir == TransactionDirection.INFLOW.value:
                account.outstanding_liability_paise = max(0, (account.outstanding_liability_paise or 0) - amount_paise)
                account.current_book_balance_paise += amount_paise
            else:
                account.outstanding_liability_paise = (account.outstanding_liability_paise or 0) + amount_paise
                account.current_book_balance_paise -= amount_paise

        else:
            if eff_dir == TransactionDirection.INFLOW.value:
                account.current_book_balance_paise += amount_paise
            elif eff_dir == TransactionDirection.OUTFLOW.value:
                account.current_book_balance_paise -= amount_paise
            account.available_balance_paise = account.current_book_balance_paise - (account.pending_amount_paise or 0)

    @staticmethod
    async def list_transactions(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        limit: int = 20,
        offset: int = 0,
        account_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        transaction_type: Optional[str] = None,
        direction: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Transaction], int]:
        """Retrieves paginated transactions with strict workspace scoping."""
        if not workspace_context.can(Permission.VIEW_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to view transactions.")

        min_paise = int(min_amount * 100) if min_amount is not None else None
        max_paise = int(max_amount * 100) if max_amount is not None else None

        repo = TransactionRepository(session)
        return await repo.list_transactions_paginated(
            workspace_id=workspace_context.workspace.id,
            limit=limit,
            offset=offset,
            account_id=account_id,
            category_id=category_id,
            status=status,
            transaction_type=transaction_type,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            min_amount_paise=min_paise,
            max_amount_paise=max_paise,
            search=search,
        )

    @staticmethod
    async def get_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
    ) -> Transaction:
        """
        Retrieves a single transaction by ID.
        Returns 404 anti-IDOR defense if the record belongs to another workspace.
        """
        if not workspace_context.can(Permission.VIEW_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to view transactions.")

        repo = TransactionRepository(session)
        tx = await repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        return tx

    @staticmethod
    async def intake_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        data: TransactionCreateRequest,
    ) -> Tuple[Transaction, bool]:
        """
        Processes an incoming operational transaction:
        1. Validates caller permissions.
        2. Validates target account ownership and active status.
        3. Quantizes amount and validates currency via Money value object.
        4. Validates AI prediction transparency rules.
        5. Checks external_transaction_id for idempotency deduplication.
        6. Resolves canonical direction.
        7. Mutates account balance (if posted) or increments pending hold (if pending).
        8. Emits domain events and persists audit trail.
        Returns (Transaction, is_new).
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to record transactions.")

        ws_id = workspace_context.workspace.id

        # 1. Target Account Verification
        account_repo = AccountRepository(session)
        account = await account_repo.get_by_id_scoped(data.account_id, ws_id)
        if not account:
            raise NotFoundException(message="Target account not found in current workspace.")

        if account.status in ("closed", "archived"):
            raise ValidationException(
                message=f"Cannot record transactions against a {account.status} account.",
                code="ACCOUNT_INACTIVE",
            )

        # 2. Money Value Object Validation & Quantization
        currency_clean = (data.currency or account.currency or "INR").upper().strip()
        try:
            money = Money.from_amount(data.amount, currency=currency_clean)
        except DomainError as err:
            raise ValidationException(message=str(err), code="INVALID_FINANCIAL_AMOUNT")

        if money.is_zero or not money.is_positive:
            raise ValidationException(
                message="Transaction amount must be strictly positive.",
                code="POSITIVE_AMOUNT_REQUIRED",
            )

        # 3. AI Invariant Validation
        if data.is_ai_predicted:
            try:
                validate_ai_prediction_invariants(data.is_ai_predicted, data.ai_confidence)
            except Exception as err:
                raise ValidationException(message=str(err), code="AI_INVARIANT_VIOLATION")

        # 4. Idempotency Deduplication Check
        tx_repo = TransactionRepository(session)
        if data.external_transaction_id:
            existing = await tx_repo.get_by_external_id(
                workspace_id=ws_id,
                external_id=data.external_transaction_id,
            )
            if existing:
                return existing, False

        # 5. Direction Resolution
        try:
            resolved_dir = resolve_transaction_direction(data.transaction_type, data.direction)
        except BusinessRuleViolationError as err:
            raise ValidationException(message=str(err), code=err.rule_name)

        status_clean = (data.status or TransactionStatus.POSTED.value).lower().strip()
        if status_clean not in (TransactionStatus.POSTED.value, TransactionStatus.PENDING.value):
            raise ValidationException(
                message=f"Initial transaction status must be 'posted' or 'pending', not '{status_clean}'.",
                code="INVALID_INITIAL_STATUS",
            )

        # 6. Account Balance Impact
        if status_clean == TransactionStatus.POSTED.value:
            TransactionService._apply_balance_mutation(
                account=account,
                amount_paise=money.to_minor_units(),
                direction=resolved_dir,
                tx_type=data.transaction_type,
            )
        elif status_clean == TransactionStatus.PENDING.value:
            if resolved_dir == TransactionDirection.OUTFLOW.value:
                account.pending_amount_paise = (account.pending_amount_paise or 0) + money.to_minor_units()
                if account.available_balance_paise is not None:
                    account.available_balance_paise -= money.to_minor_units()

        # 7. Persist Transaction
        tx = tx_repo.create(
            workspace_id=ws_id,
            account_id=account.id,
            amount=money.amount,
            amount_paise=money.to_minor_units(),
            currency=currency_clean,
            transaction_type=data.transaction_type,
            direction=resolved_dir,
            transaction_date=data.transaction_date,
            settlement_date=data.settlement_date or (data.transaction_date if status_clean == TransactionStatus.POSTED.value else None),
            description=data.description,
            merchant_name=data.merchant_name,
            category_id=data.category_id,
            status=status_clean,
            source_type=data.source_type or TransactionSourceType.MANUAL.value,
            source_reference=data.source_reference,
            external_transaction_id=data.external_transaction_id,
            related_transaction_id=data.related_transaction_id,
            created_by_id=workspace_context.current_user.id,
            is_ai_predicted=data.is_ai_predicted,
            ai_confidence=data.ai_confidence,
            source_provenance=data.source_provenance or {},
            metadata_payload=data.metadata or {},
        )
        await tx_repo.flush()

        # 8. Events and Audit Log
        event = create_transaction_created_event(
            workspace_id=ws_id,
            transaction_id=tx.id,
            account_id=tx.account_id,
            amount_str=money.to_decimal_string(),
            currency=currency_clean,
            transaction_type=tx.transaction_type,
            actor_id=workspace_context.current_user.id,
        )

        audit = AuditLog(
            workspace_id=ws_id,
            actor_id=workspace_context.current_user.id,
            action="transaction:create",
            entity_type="transaction",
            entity_id=tx.id,
            after_state={
                "account_id": str(tx.account_id),
                "amount_paise": tx.amount_paise,
                "currency": tx.currency,
                "transaction_type": tx.transaction_type,
                "direction": tx.direction,
                "status": tx.status,
            },
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(tx)
        return tx, True

    @staticmethod
    async def update_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
        data: TransactionUpdateRequest,
    ) -> Transaction:
        """
        Updates editable metadata on a transaction (description, merchant, category, metadata).
        Strictly prohibits mutating financial facts (amount, currency, account, date, type, status)
        on posted transactions to maintain audit integrity.
        """
        if not workspace_context.can(Permission.UPDATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to update transactions.")

        tx_repo = TransactionRepository(session)
        tx = await tx_repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        # Financial fact immutability guard for posted records
        if tx.status == TransactionStatus.POSTED.value:
            violations = []
            if data.amount is not None:
                try:
                    m = Money.from_amount(data.amount, currency=tx.currency)
                    if m.to_minor_units() != tx.amount_paise:
                        violations.append("amount")
                except Exception:
                    violations.append("amount")
            if data.currency is not None and data.currency.upper().strip() != tx.currency:
                violations.append("currency")
            if data.account_id is not None and data.account_id != tx.account_id:
                violations.append("account_id")
            if data.transaction_date is not None and data.transaction_date != tx.transaction_date:
                violations.append("transaction_date")
            if data.transaction_type is not None and data.transaction_type.lower().strip() != tx.transaction_type:
                violations.append("transaction_type")
            if data.direction is not None and data.direction.lower().strip() != tx.direction:
                violations.append("direction")
            if data.status is not None and data.status.lower().strip() != tx.status:
                violations.append("status")

            if violations:
                raise ValidationException(
                    message=(
                        f"Financial facts ({', '.join(violations)}) of a posted transaction "
                        f"are immutable. Issue a reversal instead to correct financial records."
                    ),
                    code="POSTED_TRANSACTION_IMMUTABLE",
                )

        before_state = {
            "description": tx.description,
            "merchant_name": tx.merchant_name,
            "category_id": str(tx.category_id) if tx.category_id else None,
            "metadata": dict(tx.metadata_payload or {}),
        }

        if data.description is not None:
            tx.description = data.description.strip()
        if data.merchant_name is not None:
            tx.merchant_name = data.merchant_name.strip()
        if data.category_id is not None:
            tx.category_id = data.category_id
        if data.metadata is not None:
            merged = dict(tx.metadata_payload or {})
            merged.update(data.metadata)
            tx.metadata_payload = merged

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="transaction:update",
            entity_type="transaction",
            entity_id=tx.id,
            before_state=before_state,
            after_state={
                "description": tx.description,
                "merchant_name": tx.merchant_name,
                "category_id": str(tx.category_id) if tx.category_id else None,
                "metadata": tx.metadata_payload,
            },
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(tx)
        return tx

    @staticmethod
    async def post_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
        data: Optional[TransactionPostRequest] = None,
    ) -> Transaction:
        """
        Transitions a pending transaction to posted status.
        Releases pending reservation and impacts account book balance.
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to update transaction status.")

        tx_repo = TransactionRepository(session)
        tx = await tx_repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        try:
            validate_transaction_lifecycle_transition(tx.status, TransactionStatus.POSTED.value)
        except BusinessRuleViolationError as err:
            raise ValidationException(message=str(err), code="INVALID_STATUS_TRANSITION")

        acct_repo = AccountRepository(session)
        account = await acct_repo.get_by_id_scoped(tx.account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Associated account not found.")

        # Release pending hold if it was pending outflow
        if tx.status == TransactionStatus.PENDING.value and tx.direction == TransactionDirection.OUTFLOW.value:
            account.pending_amount_paise = max(0, (account.pending_amount_paise or 0) - tx.amount_paise)

        # Apply posted balance mutation
        TransactionService._apply_balance_mutation(
            account=account,
            amount_paise=tx.amount_paise,
            direction=tx.direction,
            tx_type=tx.transaction_type,
        )

        tx.status = TransactionStatus.POSTED.value
        if data and data.settlement_date:
            tx.settlement_date = data.settlement_date
        elif not tx.settlement_date:
            tx.settlement_date = date.today()

        event = create_transaction_posted_event(
            workspace_id=workspace_context.workspace.id,
            transaction_id=tx.id,
            account_id=tx.account_id,
            amount_str=Money.from_minor_units(tx.amount_paise, tx.currency).to_decimal_string(),
            currency=tx.currency,
            actor_id=workspace_context.current_user.id,
        )

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="transaction:post",
            entity_type="transaction",
            entity_id=tx.id,
            after_state={
                "status": tx.status,
                "settlement_date": str(tx.settlement_date),
            },
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(tx)
        return tx

    @staticmethod
    async def cancel_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
        data: Optional[TransactionCancelRequest] = None,
    ) -> Transaction:
        """
        Cancels an unsettled pending transaction, restoring available balance.
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to cancel transactions.")

        tx_repo = TransactionRepository(session)
        tx = await tx_repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        try:
            validate_transaction_lifecycle_transition(tx.status, TransactionStatus.CANCELLED.value)
        except BusinessRuleViolationError as err:
            raise ValidationException(message=str(err), code="INVALID_STATUS_TRANSITION")

        acct_repo = AccountRepository(session)
        account = await acct_repo.get_by_id_scoped(tx.account_id, workspace_context.workspace.id)
        if account and tx.status == TransactionStatus.PENDING.value and tx.direction == TransactionDirection.OUTFLOW.value:
            account.pending_amount_paise = max(0, (account.pending_amount_paise or 0) - tx.amount_paise)
            if account.available_balance_paise is not None:
                account.available_balance_paise = account.current_book_balance_paise - account.pending_amount_paise

        tx.status = TransactionStatus.CANCELLED.value
        reason = data.cancellation_reason.strip() if (data and data.cancellation_reason) else None

        event = create_transaction_cancelled_event(
            workspace_id=workspace_context.workspace.id,
            transaction_id=tx.id,
            actor_id=workspace_context.current_user.id,
            reason=reason,
        )

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="transaction:cancel",
            entity_type="transaction",
            entity_id=tx.id,
            after_state={"status": tx.status, "reason": reason},
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(tx)
        return tx

    @staticmethod
    async def reverse_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
        data: TransactionReverseRequest,
    ) -> Transaction:
        """
        Performs a formal reversal of a posted transaction:
        1. Inverts the account balance mutation.
        2. Sets target status to reversed with auditable justification.
        3. Generates a compensating reversal transaction record with opposite direction.
        4. Emits domain events and persists audit record.
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to reverse transactions.")

        tx_repo = TransactionRepository(session)
        tx = await tx_repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        if tx.status != TransactionStatus.POSTED.value:
            raise ValidationException(
                message=f"Only posted transactions can be reversed. Current status is '{tx.status}'.",
                code="TRANSACTION_NOT_POSTED",
            )

        acct_repo = AccountRepository(session)
        account = await acct_repo.get_by_id_scoped(tx.account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Associated account not found.")

        # Invert account balance mutation
        TransactionService._apply_balance_mutation(
            account=account,
            amount_paise=tx.amount_paise,
            direction=tx.direction,
            tx_type=tx.transaction_type,
            is_reversal=True,
        )

        tx.status = TransactionStatus.REVERSED.value
        tx.reversal_reason = data.reason.strip()

        # Opposite direction for compensating record
        opp_dir = (
            TransactionDirection.INFLOW.value
            if tx.direction == TransactionDirection.OUTFLOW.value
            else (TransactionDirection.OUTFLOW.value if tx.direction == TransactionDirection.INFLOW.value else TransactionDirection.NEUTRAL.value)
        )

        rev_tx = tx_repo.create(
            workspace_id=workspace_context.workspace.id,
            account_id=tx.account_id,
            amount=tx.amount,
            amount_paise=tx.amount_paise,
            currency=tx.currency,
            transaction_type=TransactionType.REVERSAL.value,
            direction=opp_dir,
            transaction_date=date.today(),
            description=f"Reversal of TX-{str(tx.id)[:8]}: {data.reason.strip()}",
            status=TransactionStatus.POSTED.value,
            source_type=TransactionSourceType.SYSTEM.value,
            related_transaction_id=tx.id,
            created_by_id=workspace_context.current_user.id,
            reversal_reason=data.reason.strip(),
            source_provenance={"reversal_of_transaction_id": str(tx.id), "reason": data.reason.strip()},
        )
        await tx_repo.flush()

        event = create_transaction_reversed_event(
            workspace_id=workspace_context.workspace.id,
            original_transaction_id=tx.id,
            reversal_transaction_id=rev_tx.id,
            reason=data.reason.strip(),
            actor_id=workspace_context.current_user.id,
        )

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="transaction:reverse",
            entity_type="transaction",
            entity_id=tx.id,
            after_state={
                "status": tx.status,
                "reversal_reason": tx.reversal_reason,
                "reversal_transaction_id": str(rev_tx.id),
            },
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(rev_tx)
        return rev_tx

    @staticmethod
    async def refund_transaction(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
        data: TransactionRefundRequest,
    ) -> Transaction:
        """
        Issues a partial or full refund for a posted outflow transaction:
        1. Validates that cumulative refunds do not exceed the original amount.
        2. Creates an inflow refund transaction linked to the original.
        3. Updates account balance with the refunded capital.
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to refund transactions.")

        tx_repo = TransactionRepository(session)
        tx = await tx_repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        if tx.status != TransactionStatus.POSTED.value:
            raise ValidationException(
                message=f"Only posted transactions can be refunded. Current status is '{tx.status}'.",
                code="TRANSACTION_NOT_POSTED",
            )

        if tx.direction != TransactionDirection.OUTFLOW.value:
            raise ValidationException(
                message="Only outflow transactions can be refunded.",
                code="INVALID_REFUND_TARGET",
            )

        try:
            refund_money = Money.from_amount(data.refund_amount, currency=tx.currency)
        except DomainError as err:
            raise ValidationException(message=str(err), code="INVALID_REFUND_AMOUNT")

        # Sum existing refunds
        existing_refunds = await tx_repo.get_refunds_for_transaction(
            workspace_id=workspace_context.workspace.id,
            original_transaction_id=tx.id,
        )
        prev_refunded_paise = sum(r.amount_paise for r in existing_refunds if r.status in (TransactionStatus.POSTED.value, TransactionStatus.PENDING.value))
        prev_refunded_money = Money.from_minor_units(prev_refunded_paise, tx.currency)
        orig_money = Money.from_minor_units(tx.amount_paise, tx.currency)

        try:
            validate_refund_invariants(
                original_amount=orig_money,
                refund_amount=refund_money,
                previously_refunded=prev_refunded_money,
            )
        except BusinessRuleViolationError as err:
            raise ValidationException(message=str(err), code=err.rule_name)

        acct_repo = AccountRepository(session)
        account = await acct_repo.get_by_id_scoped(tx.account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Associated account not found.")

        acct_type = str(account.account_type).lower().strip()
        refund_type = (
            TransactionType.CREDIT_CARD_REFUND.value
            if "credit_card" in acct_type
            else TransactionType.REFUND.value
        )

        TransactionService._apply_balance_mutation(
            account=account,
            amount_paise=refund_money.to_minor_units(),
            direction=TransactionDirection.INFLOW.value,
            tx_type=refund_type,
        )

        refund_tx = tx_repo.create(
            workspace_id=workspace_context.workspace.id,
            account_id=tx.account_id,
            amount=refund_money.amount,
            amount_paise=refund_money.to_minor_units(),
            currency=tx.currency,
            transaction_type=refund_type,
            direction=TransactionDirection.INFLOW.value,
            transaction_date=data.refund_date or date.today(),
            description=data.description.strip() if data.description else f"Refund for: {tx.description}",
            status=TransactionStatus.POSTED.value,
            source_type=TransactionSourceType.MANUAL.value,
            external_transaction_id=data.external_refund_id,
            related_transaction_id=tx.id,
            original_transaction_id=tx.id,
            created_by_id=workspace_context.current_user.id,
            source_provenance={"refund_of_transaction_id": str(tx.id)},
        )
        await tx_repo.flush()

        event = create_transaction_refunded_event(
            workspace_id=workspace_context.workspace.id,
            original_transaction_id=tx.id,
            refund_transaction_id=refund_tx.id,
            refund_amount_str=refund_money.to_decimal_string(),
            currency=tx.currency,
            actor_id=workspace_context.current_user.id,
        )

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="transaction:refund",
            entity_type="transaction",
            entity_id=tx.id,
            after_state={
                "refund_transaction_id": str(refund_tx.id),
                "refund_amount_paise": refund_money.to_minor_units(),
                "currency": tx.currency,
            },
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(refund_tx)
        return refund_tx

    @staticmethod
    async def create_transfer(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        data: TransferCreateRequest,
    ) -> TransferResponse:
        """
        Executes an internal transfer between accounts in the same workspace:
        1. Validates transfer invariants (different accounts, positive amount).
        2. Verifies both source and destination accounts exist and are active.
        3. Creates paired outbound (source) and inbound (destination) transaction legs.
        4. Mutually cross-references legs via transfer_id and related_transaction_id.
        5. Updates balances without double-counting expenses (e.g. credit card debt reduction).
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to execute transfers.")

        # 1. Money validation
        try:
            money = Money.from_amount(data.amount, currency=data.currency)
        except DomainError as err:
            raise ValidationException(message=str(err), code="INVALID_TRANSFER_AMOUNT")

        # 2. Invariant verification
        try:
            validate_transfer_invariants(
                source_account_id=data.source_account_id,
                destination_account_id=data.destination_account_id,
                amount=money,
            )
        except BusinessRuleViolationError as err:
            raise ValidationException(message=str(err), code=err.rule_name)

        ws_id = workspace_context.workspace.id
        acct_repo = AccountRepository(session)
        source_account = await acct_repo.get_by_id_scoped(data.source_account_id, ws_id)
        dest_account = await acct_repo.get_by_id_scoped(data.destination_account_id, ws_id)

        if not source_account or not dest_account:
            raise NotFoundException(message="Source or destination account not found in current workspace.")

        if source_account.status in ("closed", "archived") or dest_account.status in ("closed", "archived"):
            raise ValidationException(message="Cannot transfer to or from an inactive account.", code="ACCOUNT_INACTIVE")

        dest_type = str(dest_account.account_type).lower().strip()
        is_cc_payment = "credit_card" in dest_type

        source_tx_type = TransactionType.CREDIT_CARD_PAYMENT.value if is_cc_payment else TransactionType.TRANSFER.value
        dest_tx_type = TransactionType.CREDIT_CARD_PAYMENT.value if is_cc_payment else TransactionType.TRANSFER.value

        transfer_id = uuid.uuid4()
        tx_repo = TransactionRepository(session)
        status_clean = (data.status or TransactionStatus.POSTED.value).lower().strip()

        # Outbound leg
        outbound_tx = tx_repo.create(
            workspace_id=ws_id,
            account_id=source_account.id,
            amount=money.amount,
            amount_paise=money.to_minor_units(),
            currency=data.currency,
            transaction_type=source_tx_type,
            direction=TransactionDirection.OUTFLOW.value,
            transaction_date=data.transfer_date,
            description=data.description or f"Transfer to {dest_account.name}",
            status=status_clean,
            source_type=TransactionSourceType.MANUAL.value,
            transfer_id=transfer_id,
            created_by_id=workspace_context.current_user.id,
            external_transaction_id=data.external_transaction_id,
            metadata_payload=data.metadata or {},
        )

        # Inbound leg
        inbound_tx = tx_repo.create(
            workspace_id=ws_id,
            account_id=dest_account.id,
            amount=money.amount,
            amount_paise=money.to_minor_units(),
            currency=data.currency,
            transaction_type=dest_tx_type,
            direction=TransactionDirection.INFLOW.value,
            transaction_date=data.transfer_date,
            description=data.description or f"Transfer from {source_account.name}",
            status=status_clean,
            source_type=TransactionSourceType.MANUAL.value,
            transfer_id=transfer_id,
            created_by_id=workspace_context.current_user.id,
            metadata_payload=data.metadata or {},
        )

        await tx_repo.flush()

        outbound_tx.related_transaction_id = inbound_tx.id
        inbound_tx.related_transaction_id = outbound_tx.id

        if status_clean == TransactionStatus.POSTED.value:
            TransactionService._apply_balance_mutation(
                source_account,
                money.to_minor_units(),
                direction=TransactionDirection.OUTFLOW.value,
                tx_type=source_tx_type,
            )
            TransactionService._apply_balance_mutation(
                dest_account,
                money.to_minor_units(),
                direction=TransactionDirection.INFLOW.value,
                tx_type=dest_tx_type,
            )
        elif status_clean == TransactionStatus.PENDING.value:
            source_account.pending_amount_paise = (source_account.pending_amount_paise or 0) + money.to_minor_units()
            if source_account.available_balance_paise is not None:
                source_account.available_balance_paise -= money.to_minor_units()

        event = create_transfer_created_event(
            workspace_id=ws_id,
            transfer_id=transfer_id,
            source_account_id=source_account.id,
            destination_account_id=dest_account.id,
            amount_str=money.to_decimal_string(),
            currency=data.currency,
            actor_id=workspace_context.current_user.id,
        )

        audit = AuditLog(
            workspace_id=ws_id,
            actor_id=workspace_context.current_user.id,
            action="transfer:create",
            entity_type="transfer",
            entity_id=transfer_id,
            after_state={
                "transfer_id": str(transfer_id),
                "source_transaction_id": str(outbound_tx.id),
                "destination_transaction_id": str(inbound_tx.id),
                "amount_paise": money.to_minor_units(),
                "currency": data.currency,
            },
        )
        session.add(audit)

        await session.commit()
        await tx_repo.refresh(outbound_tx)
        await tx_repo.refresh(inbound_tx)

        return TransferResponse(
            transfer_id=transfer_id,
            workspace_id=ws_id,
            source_account_id=source_account.id,
            destination_account_id=dest_account.id,
            amount=money.to_decimal_string(),
            currency=data.currency,
            transfer_date=data.transfer_date,
            status=status_clean,
            description=data.description or f"Transfer to {dest_account.name}",
            source_transaction_id=outbound_tx.id,
            destination_transaction_id=inbound_tx.id,
            created_at=outbound_tx.created_at,
        )

    @staticmethod
    async def get_transfer(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transfer_id: uuid.UUID,
    ) -> TransferResponse:
        """Retrieves details of a paired transfer by transfer_id."""
        if not workspace_context.can(Permission.VIEW_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to view transfers.")

        tx_repo = TransactionRepository(session)
        legs = await tx_repo.get_by_transfer_id(workspace_context.workspace.id, transfer_id)
        if not legs or len(legs) < 2:
            raise NotFoundException(message="Transfer not found.")

        outbound = next((t for t in legs if t.direction == TransactionDirection.OUTFLOW.value), legs[0])
        inbound = next((t for t in legs if t.direction == TransactionDirection.INFLOW.value), legs[1] if len(legs) > 1 else legs[0])

        return TransferResponse(
            transfer_id=transfer_id,
            workspace_id=workspace_context.workspace.id,
            source_account_id=outbound.account_id,
            destination_account_id=inbound.account_id,
            amount=Money.from_minor_units(outbound.amount_paise, outbound.currency).to_decimal_string(),
            currency=outbound.currency,
            transfer_date=outbound.transaction_date,
            status=outbound.status,
            description=outbound.description,
            source_transaction_id=outbound.id,
            destination_transaction_id=inbound.id,
            created_at=outbound.created_at,
        )

    @staticmethod
    async def get_transaction_history(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        transaction_id: uuid.UUID,
    ) -> List[TransactionHistoryEntry]:
        """Retrieves immutable audit history log for a transaction."""
        if not workspace_context.can(Permission.VIEW_TRANSACTIONS):
            raise InsufficientPermissionsException(message="Permission required to view transaction history.")

        tx_repo = TransactionRepository(session)
        tx = await tx_repo.get_by_id_scoped(transaction_id, workspace_context.workspace.id)
        if not tx:
            raise NotFoundException(message="Transaction not found.")

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.workspace_id == workspace_context.workspace.id,
                AuditLog.entity_type.in_(["transaction", "transfer"]),
                AuditLog.entity_id == transaction_id,
            )
            .order_by(AuditLog.timestamp.desc())
        )
        res = await session.execute(stmt)
        logs = res.scalars().all()
        return [
            TransactionHistoryEntry(
                id=l.id,
                action=l.action,
                actor_id=l.actor_id,
                timestamp=l.timestamp,
                details=l.after_state or l.before_state or {},
            )
            for l in logs
        ]
