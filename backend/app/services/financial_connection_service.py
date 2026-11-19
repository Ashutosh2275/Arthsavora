"""
Arthsavora Financial Connection, Aggregation & Reconciliation Service
Orchestrates Account Aggregator (AA) consent flows, account discovery, deterministic
synchronization, balance reconciliation, and health monitoring.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleViolationException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import logger
from app.domain.financial_connection import (
    AccountLinkStatus,
    ConnectionHealthStatus,
    ConnectionStatus,
    ConsentStatus,
    ReconciliationStatus,
    SyncJobStatus,
    calculate_reconciliation_variance,
    compute_connection_health,
    evaluate_consent_validity,
    mask_account_identifier,
    normalize_transaction_direction,
)
from app.domain.notification import (
    NotificationCategory,
    NotificationEventType,
    NotificationPayloadVO,
    NotificationSeverity,
)
from app.infrastructure.database.models.account import Account, AccountBalanceSnapshot
from app.infrastructure.database.models.financial_connection import (
    ExternalAccountReference,
    FinancialConnection,
    FinancialConsent,
    FinancialProvider,
    ReconciliationRecord,
    SyncJob,
)
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.financial_connection_repository import FinancialConnectionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.financial_providers.registry import FinancialProviderRegistry
from app.services.notification.notification_service import NotificationService


class FinancialConnectionService:
    """Core service for financial provider connectivity and data synchronization."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FinancialConnectionRepository(session)
        self.account_repo = AccountRepository(session)
        self.tx_repo = TransactionRepository(session)
        self.notification_service = NotificationService(session)

    # -------------------------------------------------------------------------
    # 1. Provider Catalog Operations
    # -------------------------------------------------------------------------
    async def list_providers(self) -> List[FinancialProvider]:
        """Returns all registered providers in the ecosystem."""
        return await self.repo.list_providers()

    async def get_provider_by_code(self, provider_code: str) -> FinancialProvider:
        """Retrieves provider or raises 404."""
        prov = await self.repo.get_provider_by_code(provider_code)
        if not prov:
            raise NotFoundException(f"Financial provider '{provider_code}' is not registered.")
        return prov

    # -------------------------------------------------------------------------
    # 2. Connection Initiation & Authorization Lifecycle
    # -------------------------------------------------------------------------
    async def initiate_connection(
        self,
        workspace_id: UUID,
        user_id: UUID,
        provider_code: str,
        institution_id: str,
        institution_name: Optional[str] = None,
        purpose: str = "Personal Financial Management & Automated Reconciliation",
        purpose_code: str = "101",
        data_categories: Optional[List[str]] = None,
        account_types: Optional[List[str]] = None,
        valid_days: int = 180,
        sync_schedule: str = "manual",
    ) -> Tuple[FinancialConnection, FinancialConsent]:
        """
        Initiates a new financial connection and registers consent handle with provider.
        """
        provider = await self.get_provider_by_code(provider_code)
        adapter = FinancialProviderRegistry.get_adapter(provider.provider_code)

        # Resolve institution name
        inst_name = institution_name
        if not inst_name:
            for inst in provider.supported_institutions:
                if inst.get("id") == institution_id or inst.get("code") == institution_id:
                    inst_name = inst.get("name")
                    break
        inst_name = inst_name or f"{institution_id} Institution"

        # 1. Request consent handle from provider adapter
        consent_resp = await adapter.initiate_consent(
            workspace_id=workspace_id,
            user_id=user_id,
            institution_id=institution_id,
            purpose=purpose,
            data_categories=data_categories or ["TRANSACTIONS", "BALANCES", "PROFILE"],
            account_types=account_types or ["savings", "current", "credit_card"],
            valid_days=valid_days,
        )

        handle = consent_resp["provider_consent_handle"]
        auth_url = consent_resp.get("authorization_url")
        valid_from = consent_resp["valid_from"]
        valid_to = consent_resp["valid_to"]

        # 2. Persist FinancialConnection
        connection = await self.repo.create_connection(
            workspace_id=workspace_id,
            user_id=user_id,
            provider_id=provider.id,
            institution_id=institution_id,
            institution_name=inst_name,
            authorization_url=auth_url,
            sync_schedule=sync_schedule,
            connection_metadata={"adapter_code": provider.provider_code},
        )
        connection.provider = provider

        # 3. Persist FinancialConsent
        consent = await self.repo.create_consent(
            connection_id=connection.id,
            workspace_id=workspace_id,
            user_id=user_id,
            provider_consent_handle=handle,
            purpose=purpose,
            purpose_code=purpose_code,
            data_categories=data_categories or ["TRANSACTIONS", "BALANCES", "PROFILE"],
            account_types=account_types or ["savings", "current", "credit_card"],
            valid_from=valid_from,
            valid_to=valid_to,
            consent_artefact_json=consent_resp.get("raw_response", {}),
        )

        # 4. Audit Log
        await self.repo.log_audit_event(
            workspace_id=workspace_id,
            user_id=user_id,
            connection_id=connection.id,
            event_type="connection_initiated",
            severity="info",
            metadata={"provider": provider.provider_code, "institution": inst_name, "handle": handle},
        )

        return connection, consent

    async def authorize_connection(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        provider_consent_handle: Optional[str] = None,
    ) -> FinancialConnection:
        """
        Validates user authorization with provider, transitions connection to ACTIVE,
        and automatically discovers linked accounts from FIPs.
        """
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        consent = await self.repo.get_active_consent_by_connection(connection.id)
        if not consent:
            raise BusinessRuleViolationException("No active consent associated with this connection.")

        handle = provider_consent_handle or consent.provider_consent_handle
        if not handle:
            raise ValidationException("Missing consent handle for authorization confirmation.")

        adapter = FinancialProviderRegistry.get_adapter(connection.provider.provider_code)
        status_check = await adapter.check_consent_status(handle)

        if status_check.get("status") == ConsentStatus.ACTIVE.value:
            now = datetime.now(timezone.utc)
            consent.status = ConsentStatus.ACTIVE.value
            consent.consent_artefact_json = status_check.get("raw_artefact", {})

            connection.status = ConnectionStatus.ACTIVE.value
            connection.health_status = ConnectionHealthStatus.HEALTHY.value
            connection.authorized_at = now
            connection.expires_at = consent.valid_to

            # Auto-discover accounts
            await self.discover_accounts(connection.id, workspace_id, user_id)

            # Audit log
            await self.repo.log_audit_event(
                workspace_id=workspace_id,
                user_id=user_id,
                connection_id=connection.id,
                event_type="connection_authorized",
                severity="info",
                metadata={"handle": handle, "institution": connection.institution_name},
            )

            # Emit notification
            try:
                await self.notification_service.dispatch_notification(
                    NotificationPayloadVO(
                        recipient_user_id=user_id,
                        workspace_id=workspace_id,
                        category=NotificationCategory.SYSTEM,
                        event_type=NotificationEventType.TRANSACTION_CONFIRMED,
                        title=f"Account Connected: {connection.institution_name}",
                        message=f"Your account at {connection.institution_name} has been successfully authorized for synchronization.",
                        severity=NotificationSeverity.SUCCESS,
                        related_resource_type="financial_connection",
                        related_resource_id=str(connection.id),
                        action_url="/connections",
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to dispatch connection notification: {e}")

            await self.session.commit()
            return connection
        else:
            connection.status = ConnectionStatus.FAILED.value
            connection.health_status = ConnectionHealthStatus.NEEDS_AUTHORIZATION.value
            connection.last_error_message = f"Provider authorization returned status: {status_check.get('status')}"
            await self.session.commit()
            raise BusinessRuleViolationException(f"Provider authorization failed with status: {status_check.get('status')}")

    # -------------------------------------------------------------------------
    # 3. Account Discovery & Linking
    # -------------------------------------------------------------------------
    async def discover_accounts(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> List[ExternalAccountReference]:
        """Queries provider for accounts under authorized consent."""
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        consent = await self.repo.get_active_consent_by_connection(connection.id)
        if not consent or consent.status != ConsentStatus.ACTIVE.value:
            raise BusinessRuleViolationException("Cannot discover accounts without active user consent.")

        adapter = FinancialProviderRegistry.get_adapter(connection.provider.provider_code)
        discovered_accounts = await adapter.discover_accounts(
            provider_consent_handle=consent.provider_consent_handle or "",
            institution_id=connection.institution_id,
        )

        saved_refs: List[ExternalAccountReference] = []
        for acc_vo in discovered_accounts:
            ref = await self.repo.upsert_account_reference(
                connection_id=connection.id,
                workspace_id=workspace_id,
                provider_account_id=acc_vo.provider_account_id,
                fip_id=acc_vo.fip_id,
                institution_name=acc_vo.institution_name,
                masked_account_number=mask_account_identifier(acc_vo.masked_account_number),
                account_type=acc_vo.account_type,
                currency=acc_vo.currency,
                account_holder_name=acc_vo.account_holder_name,
                current_balance_paise=acc_vo.current_balance_paise,
                available_balance_paise=acc_vo.available_balance_paise,
                balance_as_of=acc_vo.balance_as_of,
                raw_metadata=acc_vo.metadata,
            )
            saved_refs.append(ref)

        await self.session.commit()
        return saved_refs

    async def link_account(
        self,
        connection_id: UUID,
        external_ref_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        existing_account_id: Optional[UUID] = None,
        create_new: bool = False,
        account_name: Optional[str] = None,
    ) -> ExternalAccountReference:
        """
        Links a discovered external account reference to an internal Arthsavora account,
        or creates a new Account automatically if create_new is True.
        """
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        acc_ref = await self.repo.get_account_reference(connection.id, external_ref_id)
        if not acc_ref:
            raise NotFoundException("Discovered account reference not found.")

        target_account: Optional[Account] = None

        if create_new:
            # Create new Account entity in Arthsavora
            name = account_name or f"{acc_ref.institution_name} {acc_ref.account_type.capitalize()} ({acc_ref.masked_account_number})"
            init_balance = acc_ref.current_balance_paise or 0
            target_account = Account(
                id=uuid4(),
                workspace_id=workspace_id,
                name=name,
                account_type=acc_ref.account_type,
                currency=acc_ref.currency,
                institution_name=acc_ref.institution_name,
                masked_identifier=acc_ref.masked_account_number,
                status="active",
                opening_balance_paise=init_balance,
                current_book_balance_paise=init_balance,
                available_balance_paise=acc_ref.available_balance_paise or init_balance,
                provider_reported_balance_paise=init_balance,
                provider_reported_at=acc_ref.balance_as_of or datetime.now(timezone.utc),
                provider_name=connection.provider.provider_code,
                provider_account_id=acc_ref.provider_account_id,
                connection_id=str(connection.id),
                connection_status="connected",
                last_synced_at=datetime.now(timezone.utc),
                created_by_id=user_id,
            )
            self.session.add(target_account)
            await self.session.flush()

            # Create initial balance snapshot
            snapshot = AccountBalanceSnapshot(
                id=uuid4(),
                account_id=target_account.id,
                workspace_id=workspace_id,
                balance_type="provider_reported",
                balance_amount=Decimal(init_balance) / Decimal(100),
                balance_paise=init_balance,
                currency=target_account.currency,
                effective_at=datetime.now(timezone.utc),
                source="account_aggregator",
                source_reference=connection.provider.provider_code,
                reconciliation_status="reconciled",
            )
            self.session.add(snapshot)

        elif existing_account_id:
            # Link to existing account
            target_account = await self.account_repo.get_by_id_scoped(existing_account_id, workspace_id)
            if not target_account:
                raise NotFoundException("Specified Arthsavora account not found in active workspace.")

            target_account.provider_name = connection.provider.provider_code
            target_account.provider_account_id = acc_ref.provider_account_id
            target_account.connection_id = str(connection.id)
            target_account.connection_status = "connected"
            if acc_ref.current_balance_paise is not None:
                target_account.provider_reported_balance_paise = acc_ref.current_balance_paise
                target_account.provider_reported_at = acc_ref.balance_as_of or datetime.now(timezone.utc)
        else:
            raise ValidationException("Must either provide existing_account_id or set create_new=True.")

        acc_ref.account_id = target_account.id
        acc_ref.status = AccountLinkStatus.LINKED.value

        # Initialize checkpoint
        await self.repo.get_or_create_checkpoint(connection.id, acc_ref.id)

        # Audit log
        await self.repo.log_audit_event(
            workspace_id=workspace_id,
            user_id=user_id,
            connection_id=connection.id,
            event_type="account_linked",
            severity="info",
            metadata={"account_id": str(target_account.id), "mask": acc_ref.masked_account_number},
        )

        await self.session.commit()
        return acc_ref

    async def unlink_account(
        self,
        connection_id: UUID,
        external_ref_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ExternalAccountReference:
        """Unlinks a linked account reference."""
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        acc_ref = await self.repo.get_account_reference(connection.id, external_ref_id)
        if not acc_ref:
            raise NotFoundException("Discovered account reference not found.")

        if acc_ref.account_id:
            account = await self.account_repo.get_by_id_scoped(acc_ref.account_id, workspace_id)
            if account:
                account.connection_status = "disconnected"

        acc_ref.account_id = None
        acc_ref.status = AccountLinkStatus.UNLINKED.value

        await self.repo.log_audit_event(
            workspace_id=workspace_id,
            user_id=user_id,
            connection_id=connection.id,
            event_type="account_unlinked",
            severity="info",
            metadata={"external_ref_id": str(acc_ref.id)},
        )

        await self.session.commit()
        return acc_ref

    # -------------------------------------------------------------------------
    # 4. Synchronization Engine & Reconciliation
    # -------------------------------------------------------------------------
    async def sync_connection(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        job_type: str = "manual_sync",
    ) -> SyncJob:
        """
        Executes idempotent incremental transaction ingestion, balance synchronization,
        and reconciliation discrepancy calculation across all linked accounts.
        """
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        consent = await self.repo.get_active_consent_by_connection(connection.id)
        now = datetime.now(timezone.utc)

        if not consent or not evaluate_consent_validity(consent.status, consent.valid_from, consent.valid_to, consent.revoked_at, now):
            connection.health_status = ConnectionHealthStatus.CONNECTION_EXPIRED.value
            await self.session.commit()
            raise BusinessRuleViolationException("Cannot synchronize connection: Consent has expired or been revoked.")

        connection.status = ConnectionStatus.SYNCHRONIZING.value
        connection.last_attempted_sync_at = now
        sync_job = await self.repo.create_sync_job(connection.id, workspace_id, job_type)
        sync_job.status = SyncJobStatus.IN_PROGRESS.value

        adapter = FinancialProviderRegistry.get_adapter(connection.provider.provider_code)
        all_refs = await self.repo.list_account_references(connection.id)
        linked_refs = [ref for ref in all_refs if ref.status == AccountLinkStatus.LINKED.value and ref.account_id]

        total_retrieved = 0
        total_imported = 0
        total_duplicates = 0
        errors_count = 0

        today = date.today()
        from_date = today - timedelta(days=90)

        try:
            for acc_ref in linked_refs:
                checkpoint = await self.repo.get_or_create_checkpoint(connection.id, acc_ref.id)
                fetch_from = checkpoint.last_transaction_date or from_date

                # 1. Fetch Transactions from Provider
                txs, next_cursor = await adapter.fetch_transactions(
                    provider_consent_handle=consent.provider_consent_handle or "",
                    provider_account_id=acc_ref.provider_account_id,
                    from_date=fetch_from,
                    to_date=today,
                    cursor=checkpoint.sync_cursor,
                )
                total_retrieved += len(txs)

                for tx_vo in txs:
                    # Check if external_transaction_id already exists in this workspace
                    stmt = select(Transaction).where(
                        Transaction.workspace_id == workspace_id,
                        Transaction.external_transaction_id == tx_vo.external_transaction_id,
                    )
                    existing = (await self.session.execute(stmt)).scalar_one_or_none()
                    if existing:
                        total_duplicates += 1
                        continue

                    # Create authoritative transaction
                    direction, amount_paise = normalize_transaction_direction(
                        tx_vo.direction, amount_paise=tx_vo.amount_paise
                    )
                    tx_type = "income" if direction == "inflow" else "expense"
                    amt_decimal = Decimal(amount_paise) / Decimal(100)

                    new_tx = Transaction(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        account_id=acc_ref.account_id,
                        transaction_type=tx_type,
                        direction=direction,
                        amount=amt_decimal,
                        amount_paise=amount_paise,
                        currency=tx_vo.currency,
                        transaction_date=tx_vo.transaction_date,
                        settlement_date=tx_vo.transaction_date,
                        description=tx_vo.description,
                        merchant_name=tx_vo.merchant_name,
                        status="posted",
                        source_type="account_aggregator",
                        external_transaction_id=tx_vo.external_transaction_id,
                        source_reference=tx_vo.reference_number,
                        source_provenance={
                            "provider": connection.provider.provider_code,
                            "connection_id": str(connection.id),
                            "provider_account_id": acc_ref.provider_account_id,
                            "fip_id": acc_ref.fip_id,
                            "synced_at": now.isoformat(),
                        },
                    )
                    self.session.add(new_tx)
                    total_imported += 1

                    # Update checkpoint with latest transaction date
                    if not checkpoint.last_transaction_date or tx_vo.transaction_date > checkpoint.last_transaction_date:
                        checkpoint.last_transaction_date = tx_vo.transaction_date
                        checkpoint.last_transaction_external_id = tx_vo.external_transaction_id

                # 2. Fetch and Update Balances
                balances = await adapter.fetch_balances(
                    provider_consent_handle=consent.provider_consent_handle or "",
                    provider_account_ids=[acc_ref.provider_account_id],
                )
                if acc_ref.provider_account_id in balances:
                    b_data = balances[acc_ref.provider_account_id]
                    rep_balance = b_data["current_balance_paise"]
                    avail_balance = b_data.get("available_balance_paise", rep_balance)

                    acc_ref.current_balance_paise = rep_balance
                    acc_ref.available_balance_paise = avail_balance
                    acc_ref.balance_as_of = b_data.get("balance_as_of", now)

                    # Update Arthsavora account reported balance
                    account = await self.account_repo.get_by_id_scoped(acc_ref.account_id, workspace_id)
                    if account:
                        account.provider_reported_balance_paise = rep_balance
                        account.provider_reported_at = now
                        account.last_synced_at = now

                        # Record Balance Snapshot
                        snap = AccountBalanceSnapshot(
                            id=uuid4(),
                            account_id=account.id,
                            workspace_id=workspace_id,
                            balance_type="provider_reported",
                            balance_amount=Decimal(rep_balance) / Decimal(100),
                            balance_paise=rep_balance,
                            currency=account.currency,
                            effective_at=now,
                            source="account_aggregator",
                            source_reference=str(connection.id),
                            reconciliation_status="reconciled",
                        )
                        self.session.add(snap)

                        # 3. Compute Reconciliation Discrepancy
                        rec_variance = calculate_reconciliation_variance(
                            provider_reported_balance_paise=rep_balance,
                            calculated_book_balance_paise=account.current_book_balance_paise,
                            unmatched_transactions_count=0,
                        )
                        await self.repo.create_reconciliation_record(
                            workspace_id=workspace_id,
                            account_id=account.id,
                            connection_id=connection.id,
                            reconciliation_date=today,
                            provider_reported_balance_paise=rep_balance,
                            calculated_book_balance_paise=account.current_book_balance_paise,
                            difference_paise=rec_variance.difference_paise,
                            status=rec_variance.status.value,
                            unmatched_transactions_count=rec_variance.unmatched_transactions_count,
                            explanation=rec_variance.explanation,
                        )

                checkpoint.last_sync_timestamp = now
                checkpoint.sync_cursor = next_cursor

            # Complete sync job successfully
            sync_job.status = SyncJobStatus.COMPLETED.value
            sync_job.completed_at = datetime.now(timezone.utc)
            sync_job.records_retrieved = total_retrieved
            sync_job.records_imported = total_imported
            sync_job.duplicates_detected = total_duplicates
            sync_job.errors_count = errors_count

            connection.status = ConnectionStatus.ACTIVE.value
            connection.health_status = ConnectionHealthStatus.HEALTHY.value
            connection.last_successful_sync_at = now
            connection.sync_failure_count = 0
            connection.last_error_code = None
            connection.last_error_message = None

            await self.repo.log_audit_event(
                workspace_id=workspace_id,
                user_id=user_id,
                connection_id=connection.id,
                event_type="sync_completed",
                severity="info",
                metadata={
                    "retrieved": total_retrieved,
                    "imported": total_imported,
                    "duplicates": total_duplicates,
                },
            )

            await self.session.commit()
            return sync_job

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Synchronization failed for connection {connection_id}: {e}")
            sync_job.status = SyncJobStatus.FAILED.value
            sync_job.completed_at = datetime.now(timezone.utc)
            sync_job.error_summary = str(e)

            connection.status = ConnectionStatus.FAILED.value
            connection.health_status = ConnectionHealthStatus.PROVIDER_UNAVAILABLE.value
            connection.sync_failure_count += 1
            connection.last_error_message = str(e)

            await self.repo.log_audit_event(
                workspace_id=workspace_id,
                user_id=user_id,
                connection_id=connection.id,
                event_type="sync_failed",
                severity="error",
                metadata={"error": str(e)},
            )
            await self.session.commit()
            raise BusinessRuleViolationException(f"Synchronization failed: {e}")

    # -------------------------------------------------------------------------
    # 5. Revocation, Disconnection & Reconciliation
    # -------------------------------------------------------------------------
    async def revoke_consent(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None,
    ) -> FinancialConnection:
        """Revokes consent with provider and freezes synchronization."""
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        consent = await self.repo.get_active_consent_by_connection(connection.id)
        now = datetime.now(timezone.utc)

        if consent:
            adapter = FinancialProviderRegistry.get_adapter(connection.provider.provider_code)
            await adapter.revoke_consent(consent.provider_consent_handle or "", reason)
            consent.status = ConsentStatus.REVOKED.value
            consent.revoked_at = now
            consent.revocation_reason = reason or "User requested revocation"

        connection.status = ConnectionStatus.REVOKED.value
        connection.health_status = ConnectionHealthStatus.CONNECTION_EXPIRED.value

        await self.repo.log_audit_event(
            workspace_id=workspace_id,
            user_id=user_id,
            connection_id=connection.id,
            event_type="consent_revoked",
            severity="warning",
            metadata={"reason": reason},
        )

        await self.session.commit()
        return connection

    async def disconnect_connection(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Completely disconnects external provider and unlinks all accounts."""
        connection = await self.repo.get_connection(workspace_id, connection_id)
        if not connection:
            raise NotFoundException("Financial connection not found.")

        # Unlink all accounts
        refs = await self.repo.list_account_references(connection.id)
        for acc_ref in refs:
            if acc_ref.account_id:
                account = await self.account_repo.get_by_id_scoped(acc_ref.account_id, workspace_id)
                if account:
                    account.connection_status = "disconnected"
            acc_ref.account_id = None
            acc_ref.status = AccountLinkStatus.UNLINKED.value

        # Revoke consent
        consent = await self.repo.get_active_consent_by_connection(connection.id)
        if consent:
            consent.status = ConsentStatus.REVOKED.value
            consent.revoked_at = datetime.now(timezone.utc)
            consent.revocation_reason = "Connection disconnected by user"

        connection.status = ConnectionStatus.DISCONNECTED.value
        connection.health_status = ConnectionHealthStatus.DISCONNECTED.value
        connection.is_deleted = True

        await self.repo.log_audit_event(
            workspace_id=workspace_id,
            user_id=user_id,
            connection_id=connection.id,
            event_type="connection_disconnected",
            severity="warning",
            metadata={"institution": connection.institution_name},
        )

        await self.session.commit()
        return True

    async def get_reconciliation_records(
        self,
        workspace_id: UUID,
        connection_id: Optional[UUID] = None,
        account_id: Optional[UUID] = None,
    ) -> List[ReconciliationRecord]:
        """Retrieves reconciliation discrepancy records."""
        return await self.repo.list_reconciliation_records(
            workspace_id=workspace_id,
            connection_id=connection_id,
            account_id=account_id,
        )

    async def resolve_reconciliation(
        self,
        reconciliation_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        explanation: str,
    ) -> ReconciliationRecord:
        """Marks a reconciliation variance as reviewed and explained."""
        stmt = select(ReconciliationRecord).where(
            ReconciliationRecord.workspace_id == workspace_id,
            ReconciliationRecord.id == reconciliation_id,
        )
        rec = (await self.session.execute(stmt)).scalar_one_or_none()
        if not rec:
            raise NotFoundException("Reconciliation record not found.")

        rec.status = ReconciliationStatus.RESOLVED.value
        rec.explanation = explanation
        rec.resolved_at = datetime.now(timezone.utc)
        rec.resolved_by_id = user_id

        await self.session.commit()
        return rec
