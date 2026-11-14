"""
Arthsavora Financial Account Application Service
Orchestrates account creation, workspace isolation, lifecycle state transitions,
exact monetary balance representations, and historical balance snapshots.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.domain.events import create_account_created_event
from app.domain.exceptions import DomainError
from app.domain.money import Money
from app.infrastructure.database.models.account import Account, AccountBalanceSnapshot
from app.infrastructure.database.models.audit import AuditLog
from app.repositories.account_repository import AccountRepository
from app.schemas.account import (
    AccountBalanceSnapshotCreateRequest,
    AccountBalanceSnapshotResponse,
    AccountCloseRequest,
    AccountCreateRequest,
    AccountResponse,
    AccountTypeEnum,
    AccountUpdateRequest,
    BalanceBreakdown,
)


# Allowed account types per workspace tenancy model
ALLOWED_ACCOUNT_TYPES = {
    "personal": {
        "cash", "savings", "current", "salary", "fixed_deposit",
        "recurring_deposit", "credit_card", "loan", "investment",
        "digital_wallet", "wallet", "bank", "other",
    },
    "family": {
        "cash", "savings", "current", "salary", "fixed_deposit",
        "recurring_deposit", "credit_card", "loan", "investment",
        "digital_wallet", "wallet", "bank", "other",
    },
    "business": {
        "business_cash", "business_bank", "business_current",
        "business_credit_card", "petty_cash", "loan_account",
        "other_business", "cash", "bank", "current", "savings",
        "credit_card", "loan", "wallet", "digital_wallet",
        "investment", "other",
    },
}


class AccountService:
    """Service orchestrating financial account domain logic, lifecycle, and balance histories."""

    @classmethod
    def format_account_response(cls, account: Account) -> AccountResponse:
        """Converts Account ORM entity into a serialized AccountResponse with formatted balances."""
        currency = account.currency

        # Formatted balances using exact Money value object
        book_bal = Money.from_minor_units(account.current_book_balance_paise, currency)
        avail_bal = (
            Money.from_minor_units(account.available_balance_paise, currency)
            if account.available_balance_paise is not None
            else None
        )
        prov_bal = (
            Money.from_minor_units(account.provider_reported_balance_paise, currency)
            if account.provider_reported_balance_paise is not None
            else None
        )
        liab_bal = (
            Money.from_minor_units(account.outstanding_liability_paise, currency)
            if account.outstanding_liability_paise is not None
            else None
        )
        pend_bal = Money.from_minor_units(account.pending_amount_paise, currency)
        open_bal = Money.from_minor_units(account.opening_balance_paise, currency)

        # Credit card & loan formatted amounts
        cred_lim = (
            Money.from_minor_units(account.credit_limit_paise, currency).to_decimal_string()
            if account.credit_limit_paise is not None
            else None
        )
        avail_cred = None
        if account.credit_limit_paise is not None:
            avail_paise = max(0, account.credit_limit_paise - (account.outstanding_liability_paise or 0))
            avail_cred = Money.from_minor_units(avail_paise, currency).to_decimal_string()

        stmt_bal = (
            Money.from_minor_units(account.statement_balance_paise, currency).to_decimal_string()
            if account.statement_balance_paise is not None
            else None
        )
        min_due = (
            Money.from_minor_units(account.minimum_due_paise, currency).to_decimal_string()
            if account.minimum_due_paise is not None
            else None
        )
        repay_amt = (
            Money.from_minor_units(account.repayment_amount_paise, currency).to_decimal_string()
            if account.repayment_amount_paise is not None
            else None
        )

        metadata = account.source_metadata or {}
        orig_principal_paise = metadata.get("original_principal_paise")
        if orig_principal_paise is None and account.account_type in ["loan", "loan_account"]:
            orig_principal_paise = account.opening_balance_paise if account.opening_balance_paise else None
        orig_principal = (
            Money.from_minor_units(orig_principal_paise, currency).to_decimal_string()
            if orig_principal_paise is not None
            else None
        )

        out_principal_paise = None
        out_principal = None
        if account.account_type in ["loan", "loan_account"]:
            out_principal_paise = account.outstanding_liability_paise
            if out_principal_paise is not None:
                out_principal = Money.from_minor_units(out_principal_paise, currency).to_decimal_string()

        breakdown = BalanceBreakdown(
            currency=currency,
            book_balance=book_bal.to_decimal_string(),
            book_balance_paise=book_bal.to_minor_units(),
            available_balance=avail_bal.to_decimal_string() if avail_bal else None,
            available_balance_paise=avail_bal.to_minor_units() if avail_bal else None,
            provider_reported_balance=prov_bal.to_decimal_string() if prov_bal else None,
            provider_reported_balance_paise=prov_bal.to_minor_units() if prov_bal else None,
            provider_reported_at=account.provider_reported_at,
            outstanding_liability=liab_bal.to_decimal_string() if liab_bal else None,
            outstanding_liability_paise=liab_bal.to_minor_units() if liab_bal else None,
            pending_amount=pend_bal.to_decimal_string(),
            pending_amount_paise=pend_bal.to_minor_units(),
            opening_balance=open_bal.to_decimal_string(),
            opening_balance_paise=open_bal.to_minor_units(),
            opening_balance_date=account.opening_balance_date,
            opening_balance_source=account.opening_balance_source,
            credit_limit=cred_lim,
            credit_limit_paise=account.credit_limit_paise,
            available_credit=avail_cred,
            available_credit_paise=(
                max(0, account.credit_limit_paise - (account.outstanding_liability_paise or 0))
                if account.credit_limit_paise is not None
                else None
            ),
            statement_balance=stmt_bal,
            statement_balance_paise=account.statement_balance_paise,
            minimum_due=min_due,
            minimum_due_paise=account.minimum_due_paise,
            due_date=account.due_date,
            original_principal=orig_principal,
            original_principal_paise=orig_principal_paise,
            outstanding_principal=out_principal,
            outstanding_principal_paise=out_principal_paise,
            interest_rate=float(account.interest_rate) if account.interest_rate is not None else None,
            repayment_amount=repay_amt,
            repayment_amount_paise=account.repayment_amount_paise,
        )

        return AccountResponse(
            id=account.id,
            workspace_id=account.workspace_id,
            name=account.name,
            account_type=account.account_type,
            account_subtype=account.account_subtype,
            description=account.description,
            currency=account.currency,
            institution_name=account.institution_name,
            masked_identifier=account.masked_identifier,
            status=account.status,
            opening_date=account.opening_date,
            closing_date=account.closing_date,
            created_at=account.created_at,
            updated_at=account.updated_at,
            current_book_balance=book_bal.to_decimal_string(),
            current_book_balance_paise=book_bal.to_minor_units(),
            available_balance=avail_bal.to_decimal_string() if avail_bal else None,
            available_balance_paise=avail_bal.to_minor_units() if avail_bal else None,
            provider_reported_balance=prov_bal.to_decimal_string() if prov_bal else None,
            provider_reported_balance_paise=prov_bal.to_minor_units() if prov_bal else None,
            provider_reported_at=account.provider_reported_at,
            outstanding_liability=liab_bal.to_decimal_string() if liab_bal else None,
            outstanding_liability_paise=liab_bal.to_minor_units() if liab_bal else None,
            pending_amount=pend_bal.to_decimal_string(),
            pending_amount_paise=pend_bal.to_minor_units(),
            credit_limit=cred_lim,
            available_credit=avail_cred,
            due_date=account.due_date,
            interest_rate=float(account.interest_rate) if account.interest_rate is not None else None,
            repayment_amount=repay_amt,
            provider_name=account.provider_name,
            connection_status=account.connection_status,
            last_synced_at=account.last_synced_at,
            source_metadata=account.source_metadata or {},
            balances=breakdown,
        )

    @staticmethod
    async def list_accounts(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_type: Optional[str] = None,
        status: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AccountResponse]:
        """Lists accounts strictly within the caller's authorized workspace context."""
        if not workspace_context.can(Permission.VIEW_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to view financial accounts.")

        repo = AccountRepository(session)
        accounts = await repo.list_by_workspace(
            workspace_id=workspace_context.workspace.id,
            account_type=account_type,
            status=status,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )
        return [AccountService.format_account_response(a) for a in accounts]

    @staticmethod
    async def get_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
    ) -> AccountResponse:
        """
        Retrieves a single financial account by ID.
        Returns 404 if the account belongs to another workspace (anti-IDOR defense).
        """
        if not workspace_context.can(Permission.VIEW_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to view financial accounts.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(
            entity_id=account_id,
            workspace_id=workspace_context.workspace.id,
        )
        if not account:
            raise NotFoundException(message="Financial account not found.")

        return AccountService.format_account_response(account)

    @staticmethod
    async def get_account_balances(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
    ) -> BalanceBreakdown:
        """Retrieves structured balance breakdown for an authorized account."""
        resp = await AccountService.get_account(session, workspace_context, account_id)
        return resp.balances or BalanceBreakdown(currency=resp.currency)

    @staticmethod
    async def create_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        data: AccountCreateRequest,
    ) -> AccountResponse:
        """
        Provisions a new financial account atomically:
        - Validates workspace-type-appropriate account type.
        - Validates currency using Money domain value object.
        - Enforces duplicate external connection prevention.
        - Quantizes opening balance, credit limits, and liabilities to integer paise.
        - Seeds initial AccountBalanceSnapshot for opening balance.
        - Emits AuditLog and account.created domain event.
        """
        if not workspace_context.can(Permission.MANAGE_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to manage financial accounts.")

        ws_type = str(workspace_context.workspace.type).lower().strip()
        account_type_clean = data.account_type.lower().strip()

        # 1. Validate account type allowed for this workspace tenancy model
        allowed_types = ALLOWED_ACCOUNT_TYPES.get(ws_type, set())
        if account_type_clean not in allowed_types:
            raise ValidationException(
                message=f"Account type '{account_type_clean}' is not supported in a {ws_type} workspace. Supported: {', '.join(sorted(allowed_types))}.",
                field="account_type",
                code="INVALID_ACCOUNT_TYPE",
            )

        # 2. Validate currency code using Money value object
        try:
            Money.from_amount("0", currency=data.currency)
        except DomainError as err:
            raise ValidationException(message=str(err), code="INVALID_CURRENCY", field="currency")

        repo = AccountRepository(session)

        # 3. Check duplicate external provider reference
        if data.provider_name and data.provider_account_id:
            existing_linked = await repo.get_by_provider_account_id(
                workspace_id=workspace_context.workspace.id,
                provider_name=data.provider_name,
                provider_account_id=data.provider_account_id,
            )
            if existing_linked:
                raise ConflictException(
                    message=f"An account linked to {data.provider_name} with account ID '{data.provider_account_id}' already exists in this workspace.",
                    code="DUPLICATE_EXTERNAL_ACCOUNT",
                )

        # 4. Quantize monetary values to integer minor units (paise)
        currency_str = data.currency.upper().strip()
        opening_paise = 0
        if data.opening_balance:
            try:
                opening_paise = Money.from_amount(data.opening_balance, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid opening balance: {err}", field="opening_balance")

        credit_limit_paise = None
        if data.credit_limit:
            try:
                credit_limit_paise = Money.from_amount(data.credit_limit, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid credit limit: {err}", field="credit_limit")

        statement_bal_paise = None
        if data.statement_balance:
            try:
                statement_bal_paise = Money.from_amount(data.statement_balance, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid statement balance: {err}", field="statement_balance")

        minimum_due_paise = None
        if data.minimum_due:
            try:
                minimum_due_paise = Money.from_amount(data.minimum_due, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid minimum due: {err}", field="minimum_due")

        initial_liability_str = data.outstanding_liability or data.initial_liability or data.outstanding_principal
        initial_liability_paise = None
        if initial_liability_str:
            try:
                initial_liability_paise = Money.from_amount(initial_liability_str, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid liability amount: {err}", field="outstanding_liability")

        original_principal_paise = None
        if data.original_principal:
            try:
                original_principal_paise = Money.from_amount(data.original_principal, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid principal: {err}", field="original_principal")

        repayment_paise = None
        if data.repayment_amount:
            try:
                repayment_paise = Money.from_amount(data.repayment_amount, currency=currency_str).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid repayment amount: {err}", field="repayment_amount")

        interest_rate_dec = None
        if data.interest_rate is not None:
            if data.interest_rate < 0 or data.interest_rate > 100:
                raise ValidationException(message="Interest rate must be between 0 and 100%.", field="interest_rate")
            interest_rate_dec = Decimal(str(data.interest_rate))

        source_meta = dict(data.metadata or {})
        if original_principal_paise is not None:
            source_meta["original_principal_paise"] = original_principal_paise
            source_meta["original_principal"] = data.original_principal

        # 5. Create Account Entity
        account = repo.create(
            workspace_id=workspace_context.workspace.id,
            name=data.name,
            account_type=account_type_clean,
            currency=currency_str,
            account_subtype=data.account_subtype,
            description=data.description,
            institution_name=data.institution_name,
            masked_identifier=data.masked_identifier,
            opening_date=data.opening_date,
            created_by_id=workspace_context.current_user.id,
            opening_balance_paise=opening_paise,
            opening_balance_date=data.opening_date or date.today(),
            opening_balance_source=data.opening_balance_source or "manual",
            credit_limit_paise=credit_limit_paise,
            statement_balance_paise=statement_bal_paise,
            minimum_due_paise=minimum_due_paise,
            due_date=data.due_date,
            initial_liability_paise=initial_liability_paise,
            original_principal_paise=original_principal_paise,
            interest_rate=interest_rate_dec,
            repayment_amount_paise=repayment_paise,
            loan_due_date=data.loan_due_date,
            provider_name=data.provider_name,
            provider_account_id=data.provider_account_id,
            connection_id=data.connection_id,
            source_metadata=source_meta,
        )
        await repo.flush()

        # 6. Seed Opening Balance Snapshot if specified
        if opening_paise != 0 or data.opening_balance:
            open_money = Money.from_minor_units(opening_paise, currency=currency_str)
            repo.create_snapshot(
                account_id=account.id,
                workspace_id=workspace_context.workspace.id,
                balance_type="opening",
                balance_amount=open_money.amount,
                balance_paise=opening_paise,
                currency=currency_str,
                effective_at=datetime.combine(account.opening_date or date.today(), datetime.min.time(), tzinfo=timezone.utc),
                source=data.opening_balance_source or "manual",
                source_reference="opening_balance",
                reconciliation_status="reconciled",
                created_by_id=workspace_context.current_user.id,
            )

        # 7. Audit log & Domain event
        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="account:create",
            entity_type="account",
            entity_id=account.id,
            after_state={
                "name": account.name,
                "account_type": account.account_type,
                "currency": account.currency,
                "opening_balance_paise": opening_paise,
                "institution_name": account.institution_name,
            },
        )
        session.add(audit)

        event = create_account_created_event(
            workspace_id=workspace_context.workspace.id,
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            currency=account.currency,
            actor_id=workspace_context.current_user.id,
        )

        await session.commit()
        await repo.refresh(account)
        return AccountService.format_account_response(account)

    @staticmethod
    async def update_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
        data: AccountUpdateRequest,
    ) -> AccountResponse:
        """Updates account details and metadata. Prohibits updating closed or archived accounts."""
        if not workspace_context.can(Permission.MANAGE_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to update financial accounts.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Financial account not found.")

        if account.status in ["archived", "closed"]:
            raise ValidationException(
                message=f"Cannot modify account in '{account.status}' status. Restore account first.",
                code="ACCOUNT_INACTIVE_MUTATION",
            )

        before_state = {
            "name": account.name,
            "account_subtype": account.account_subtype,
            "institution_name": account.institution_name,
            "masked_identifier": account.masked_identifier,
        }

        if data.name is not None:
            clean_name = data.name.strip()
            if not clean_name:
                raise ValidationException(message="Account name cannot be empty.", field="name")
            account.name = clean_name

        if data.account_subtype is not None:
            account.account_subtype = data.account_subtype.lower().strip() or None

        if data.description is not None:
            account.description = data.description.strip() or None

        if data.institution_name is not None:
            account.institution_name = data.institution_name.strip() or None

        if data.masked_identifier is not None:
            account.masked_identifier = data.masked_identifier.strip() or None

        if data.opening_date is not None:
            account.opening_date = data.opening_date

        if data.credit_limit is not None:
            try:
                account.credit_limit_paise = Money.from_amount(data.credit_limit, account.currency).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid credit limit: {err}", field="credit_limit")

        if data.due_date is not None:
            account.due_date = data.due_date

        if data.interest_rate is not None:
            account.interest_rate = Decimal(str(data.interest_rate))

        if data.repayment_amount is not None:
            try:
                account.repayment_amount_paise = Money.from_amount(data.repayment_amount, account.currency).to_minor_units()
            except DomainError as err:
                raise ValidationException(message=f"Invalid repayment amount: {err}", field="repayment_amount")

        if data.metadata is not None:
            existing = dict(account.source_metadata or {})
            existing.update(data.metadata)
            account.source_metadata = existing

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="account:update",
            entity_type="account",
            entity_id=account.id,
            before_state=before_state,
            after_state={"name": account.name, "institution_name": account.institution_name},
        )
        session.add(audit)
        await session.commit()
        await repo.refresh(account)
        return AccountService.format_account_response(account)

    @staticmethod
    async def archive_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
    ) -> AccountResponse:
        """Transitions active account into read-only ARCHIVED state."""
        if not workspace_context.can(Permission.MANAGE_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to archive financial accounts.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Financial account not found.")

        if account.status == "archived":
            raise ValidationException(
                message="Account is already archived.",
                code="INVALID_STATE_TRANSITION",
            )
        if account.status == "closed":
            raise ValidationException(
                message="Cannot archive a closed account.",
                code="INVALID_STATE_TRANSITION",
            )

        account.status = "archived"

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="account:archive",
            entity_type="account",
            entity_id=account.id,
            before_state={"status": "active"},
            after_state={"status": "archived"},
        )
        session.add(audit)
        await session.commit()
        await repo.refresh(account)
        return AccountService.format_account_response(account)

    @staticmethod
    async def restore_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
    ) -> AccountResponse:
        """Restores an ARCHIVED account back to ACTIVE status."""
        if not workspace_context.can(Permission.MANAGE_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to restore financial accounts.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Financial account not found.")

        if account.status != "archived":
            raise ValidationException(
                message=f"Only ARCHIVED accounts can be restored. Current status is '{account.status}'.",
                code="INVALID_STATE_TRANSITION",
            )

        account.status = "active"

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="account:restore",
            entity_type="account",
            entity_id=account.id,
            before_state={"status": "archived"},
            after_state={"status": "active"},
        )
        session.add(audit)
        await session.commit()
        await repo.refresh(account)
        return AccountService.format_account_response(account)

    @staticmethod
    async def close_account(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
        data: AccountCloseRequest,
    ) -> AccountResponse:
        """
        Formally closes an account while preserving all historical relationships.
        Validates closing_date >= opening_date.
        """
        if not workspace_context.can(Permission.MANAGE_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to close financial accounts.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Financial account not found.")

        if account.status == "closed":
            raise ValidationException(
                message="Account is already closed.",
                code="INVALID_STATE_TRANSITION",
            )

        closing_dt = data.closing_date or date.today()
        if account.opening_date and closing_dt < account.opening_date:
            raise ValidationException(
                message=f"Closing date ({closing_dt}) cannot precede opening date ({account.opening_date}).",
                field="closing_date",
                code="INVALID_CLOSING_DATE",
            )

        account.status = "closed"
        account.closing_date = closing_dt

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="account:close",
            entity_type="account",
            entity_id=account.id,
            before_state={"status": account.status},
            after_state={"status": "closed", "closing_date": str(closing_dt), "reason": data.reason},
        )
        session.add(audit)
        await session.commit()
        await repo.refresh(account)
        return AccountService.format_account_response(account)

    @staticmethod
    async def record_balance_snapshot(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
        data: AccountBalanceSnapshotCreateRequest,
    ) -> AccountBalanceSnapshotResponse:
        """
        Records an immutable point-in-time balance snapshot for an account.
        Updates fast cached balance pointers on the Account entity.
        """
        if not workspace_context.can(Permission.MANAGE_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to record balance snapshots.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Financial account not found.")

        valid_types = {"book", "available", "provider_reported", "liability", "opening"}
        balance_type_clean = data.balance_type.lower().strip()
        if balance_type_clean not in valid_types:
            raise ValidationException(
                message=f"Invalid balance type '{balance_type_clean}'. Supported: {', '.join(sorted(valid_types))}.",
                field="balance_type",
                code="INVALID_BALANCE_TYPE",
            )

        try:
            money_val = Money.from_amount(data.balance_amount, currency=account.currency)
        except DomainError as err:
            raise ValidationException(message=f"Invalid balance amount: {err}", field="balance_amount")

        effective_dt = data.effective_at or datetime.now(timezone.utc)
        paise_val = money_val.to_minor_units()

        # Update fast pointers on Account entity depending on snapshot type
        if balance_type_clean == "provider_reported":
            account.provider_reported_balance_paise = paise_val
            account.provider_reported_at = effective_dt
        elif balance_type_clean == "available":
            account.available_balance_paise = paise_val
        elif balance_type_clean == "liability":
            account.outstanding_liability_paise = paise_val
        elif balance_type_clean == "book":
            account.current_book_balance_paise = paise_val

        snapshot = repo.create_snapshot(
            account_id=account.id,
            workspace_id=workspace_context.workspace.id,
            balance_type=balance_type_clean,
            balance_amount=money_val.amount,
            balance_paise=paise_val,
            currency=account.currency,
            effective_at=effective_dt,
            source=data.source,
            source_reference=data.source_reference,
            reconciliation_status=data.reconciliation_status,
            created_by_id=workspace_context.current_user.id,
        )

        audit = AuditLog(
            workspace_id=workspace_context.workspace.id,
            actor_id=workspace_context.current_user.id,
            action="account:record_snapshot",
            entity_type="account_balance_snapshot",
            entity_id=snapshot.id,
            after_state={
                "account_id": str(account.id),
                "balance_type": balance_type_clean,
                "amount": str(money_val.amount),
                "currency": account.currency,
                "source": data.source,
            },
        )
        session.add(audit)
        await session.commit()
        await repo.refresh(snapshot)

        return AccountBalanceSnapshotResponse(
            id=snapshot.id,
            account_id=snapshot.account_id,
            workspace_id=snapshot.workspace_id,
            balance_type=snapshot.balance_type,
            balance_amount=Money.from_minor_units(snapshot.balance_paise, snapshot.currency).to_decimal_string(),
            balance_paise=snapshot.balance_paise,
            currency=snapshot.currency,
            effective_at=snapshot.effective_at,
            source=snapshot.source,
            source_reference=snapshot.source_reference,
            reconciliation_status=snapshot.reconciliation_status,
            created_at=snapshot.created_at,
        )

    @staticmethod
    async def list_balance_history(
        session: AsyncSession,
        workspace_context: WorkspaceContext,
        account_id: uuid.UUID,
        balance_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AccountBalanceSnapshotResponse]:
        """Retrieves point-in-time balance snapshot history in reverse chronological order."""
        if not workspace_context.can(Permission.VIEW_ACCOUNTS):
            raise InsufficientPermissionsException(message="Permission required to view balance history.")

        repo = AccountRepository(session)
        account = await repo.get_by_id_scoped(account_id, workspace_context.workspace.id)
        if not account:
            raise NotFoundException(message="Financial account not found.")

        snapshots = await repo.list_snapshots(
            account_id=account.id,
            workspace_id=workspace_context.workspace.id,
            balance_type=balance_type,
            limit=limit,
            offset=offset,
        )

        return [
            AccountBalanceSnapshotResponse(
                id=s.id,
                account_id=s.account_id,
                workspace_id=s.workspace_id,
                balance_type=s.balance_type,
                balance_amount=Money.from_minor_units(s.balance_paise, s.currency).to_decimal_string(),
                balance_paise=s.balance_paise,
                currency=s.currency,
                effective_at=s.effective_at,
                source=s.source,
                source_reference=s.source_reference,
                reconciliation_status=s.reconciliation_status,
                created_at=s.created_at,
            )
            for s in snapshots
        ]
