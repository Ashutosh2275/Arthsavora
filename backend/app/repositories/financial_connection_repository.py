"""
Arthsavora Financial Connection Repository
PostgreSQL tenant-isolated data access layer for providers, connections, consents,
external accounts, sync checkpoints, reconciliation records, and audit events.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.financial_connection import (
    AccountLinkStatus,
    ConnectionStatus,
    ConsentStatus,
    ReconciliationStatus,
    SyncJobStatus,
)
from app.infrastructure.database.models.financial_connection import (
    ConnectionAuditEvent,
    ExternalAccountReference,
    FinancialConnection,
    FinancialConsent,
    FinancialProvider,
    ReconciliationRecord,
    SyncCheckpoint,
    SyncJob,
)
from app.services.financial_providers.registry import REGISTERED_PROVIDERS_CATALOG


class FinancialConnectionRepository:
    """Repository handling all persistence for financial aggregation and connectivity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # 1. Provider Catalog
    # -------------------------------------------------------------------------
    async def ensure_provider_catalog_seeded(self) -> List[FinancialProvider]:
        """Ensures all standard catalog providers exist in the database."""
        result = await self.session.execute(select(FinancialProvider))
        existing_providers = {p.provider_code: p for p in result.scalars().all()}

        for cat in REGISTERED_PROVIDERS_CATALOG:
            code = cat["provider_code"]
            if code not in existing_providers:
                new_prov = FinancialProvider(
                    id=uuid4(),
                    provider_code=code,
                    name=cat["name"],
                    category=cat["category"],
                    country=cat["country"],
                    supported_institutions=cat["supported_institutions"],
                    supported_account_types=cat["supported_account_types"],
                    auth_method=cat["auth_method"],
                    consent_capabilities=cat["consent_capabilities"],
                    data_capabilities=cat["data_capabilities"],
                    historical_days_limit=cat["historical_days_limit"],
                    sync_capabilities=cat["sync_capabilities"],
                    status=cat["status"],
                    is_sandbox=cat["is_sandbox"],
                    docs_reference=cat.get("docs_reference"),
                    config_status=cat["config_status"],
                    provider_metadata=cat.get("provider_metadata", {}),
                )
                self.session.add(new_prov)
                existing_providers[code] = new_prov

        await self.session.flush()
        return list(existing_providers.values())

    async def list_providers(self) -> List[FinancialProvider]:
        """Retrieves all registered providers."""
        await self.ensure_provider_catalog_seeded()
        stmt = select(FinancialProvider).order_by(FinancialProvider.name)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_provider_by_code(self, provider_code: str) -> Optional[FinancialProvider]:
        """Retrieves provider record by code."""
        await self.ensure_provider_catalog_seeded()
        stmt = select(FinancialProvider).where(FinancialProvider.provider_code == provider_code.upper())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_provider_by_id(self, provider_id: UUID) -> Optional[FinancialProvider]:
        """Retrieves provider record by primary key."""
        stmt = select(FinancialProvider).where(FinancialProvider.id == provider_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # 2. Financial Connections
    # -------------------------------------------------------------------------
    async def create_connection(
        self,
        workspace_id: UUID,
        user_id: UUID,
        provider_id: UUID,
        institution_id: str,
        institution_name: str,
        authorization_url: Optional[str] = None,
        sync_schedule: str = "manual",
        connection_metadata: Optional[Dict[str, Any]] = None,
    ) -> FinancialConnection:
        """Creates a new financial connection in initiated state."""
        connection = FinancialConnection(
            id=uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            provider_id=provider_id,
            institution_id=institution_id,
            institution_name=institution_name,
            status=ConnectionStatus.INITIATED.value,
            authorization_url=authorization_url,
            sync_schedule=sync_schedule,
            connection_metadata=connection_metadata or {},
        )
        self.session.add(connection)
        await self.session.flush()
        return connection

    async def get_connection(self, workspace_id: UUID, connection_id: UUID) -> Optional[FinancialConnection]:
        """Retrieves connection by ID within tenant workspace."""
        stmt = (
            select(FinancialConnection)
            .options(
                selectinload(FinancialConnection.provider),
                selectinload(FinancialConnection.consents),
                selectinload(FinancialConnection.account_references),
            )
            .where(
                FinancialConnection.workspace_id == workspace_id,
                FinancialConnection.id == connection_id,
                FinancialConnection.is_deleted.is_(False),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_connections(
        self,
        workspace_id: UUID,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[FinancialConnection]:
        """Lists active connections for a workspace with optional filters."""
        stmt = (
            select(FinancialConnection)
            .options(
                selectinload(FinancialConnection.provider),
                selectinload(FinancialConnection.account_references),
            )
            .where(
                FinancialConnection.workspace_id == workspace_id,
                FinancialConnection.is_deleted.is_(False),
            )
        )
        if user_id:
            stmt = stmt.where(FinancialConnection.user_id == user_id)
        if status:
            stmt = stmt.where(FinancialConnection.status == status)

        stmt = stmt.order_by(desc(FinancialConnection.created_at))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # 3. Consents
    # -------------------------------------------------------------------------
    async def create_consent(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        provider_consent_handle: str,
        purpose: str,
        purpose_code: str,
        data_categories: List[str],
        account_types: List[str],
        valid_from: datetime,
        valid_to: datetime,
        consent_artefact_json: Optional[Dict[str, Any]] = None,
    ) -> FinancialConsent:
        """Stores a new consent record."""
        consent = FinancialConsent(
            id=uuid4(),
            connection_id=connection_id,
            workspace_id=workspace_id,
            user_id=user_id,
            provider_consent_handle=provider_consent_handle,
            purpose=purpose,
            purpose_code=purpose_code,
            data_categories=data_categories,
            account_types=account_types,
            status=ConsentStatus.INITIATED.value,
            valid_from=valid_from,
            valid_to=valid_to,
            consent_artefact_json=consent_artefact_json or {},
        )
        self.session.add(consent)
        await self.session.flush()
        return consent

    async def get_active_consent_by_connection(self, connection_id: UUID) -> Optional[FinancialConsent]:
        """Retrieves current active consent for a connection."""
        stmt = (
            select(FinancialConsent)
            .where(
                FinancialConsent.connection_id == connection_id,
                FinancialConsent.status.in_([ConsentStatus.ACTIVE.value, ConsentStatus.INITIATED.value]),
            )
            .order_by(desc(FinancialConsent.created_at))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_consent_by_handle(self, provider_consent_handle: str) -> Optional[FinancialConsent]:
        """Retrieves consent by provider handle."""
        stmt = select(FinancialConsent).where(FinancialConsent.provider_consent_handle == provider_consent_handle)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # 4. External Account References
    # -------------------------------------------------------------------------
    async def upsert_account_reference(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        provider_account_id: str,
        fip_id: str,
        institution_name: str,
        masked_account_number: str,
        account_type: str,
        currency: str = "INR",
        account_holder_name: Optional[str] = None,
        current_balance_paise: Optional[int] = None,
        available_balance_paise: Optional[int] = None,
        balance_as_of: Optional[datetime] = None,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExternalAccountReference:
        """Upserts discovered account from provider."""
        stmt = select(ExternalAccountReference).where(
            ExternalAccountReference.connection_id == connection_id,
            ExternalAccountReference.provider_account_id == provider_account_id,
        )
        res = await self.session.execute(stmt)
        acc_ref = res.scalar_one_or_none()

        if acc_ref:
            acc_ref.masked_account_number = masked_account_number
            acc_ref.account_type = account_type
            if current_balance_paise is not None:
                acc_ref.current_balance_paise = current_balance_paise
            if available_balance_paise is not None:
                acc_ref.available_balance_paise = available_balance_paise
            if balance_as_of is not None:
                acc_ref.balance_as_of = balance_as_of
            if raw_metadata:
                acc_ref.raw_metadata = raw_metadata
        else:
            acc_ref = ExternalAccountReference(
                id=uuid4(),
                connection_id=connection_id,
                workspace_id=workspace_id,
                provider_account_id=provider_account_id,
                fip_id=fip_id,
                institution_name=institution_name,
                masked_account_number=masked_account_number,
                account_type=account_type,
                currency=currency,
                status=AccountLinkStatus.DISCOVERED.value,
                account_holder_name=account_holder_name,
                current_balance_paise=current_balance_paise,
                available_balance_paise=available_balance_paise,
                balance_as_of=balance_as_of,
                raw_metadata=raw_metadata or {},
            )
            self.session.add(acc_ref)

        await self.session.flush()
        return acc_ref

    async def list_account_references(self, connection_id: UUID) -> List[ExternalAccountReference]:
        """Lists all external account references for a connection."""
        stmt = (
            select(ExternalAccountReference)
            .where(ExternalAccountReference.connection_id == connection_id)
            .order_by(ExternalAccountReference.created_at)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_account_reference(self, connection_id: UUID, ref_id: UUID) -> Optional[ExternalAccountReference]:
        """Retrieves a single external account reference."""
        stmt = select(ExternalAccountReference).where(
            ExternalAccountReference.connection_id == connection_id,
            ExternalAccountReference.id == ref_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # 5. Sync Jobs & Checkpoints
    # -------------------------------------------------------------------------
    async def create_sync_job(
        self,
        connection_id: UUID,
        workspace_id: UUID,
        job_type: str = "manual_sync",
    ) -> SyncJob:
        """Creates a new sync job in queued state."""
        job = SyncJob(
            id=uuid4(),
            connection_id=connection_id,
            workspace_id=workspace_id,
            job_type=job_type,
            status=SyncJobStatus.QUEUED.value,
            started_at=datetime.now(timezone.utc),
            execution_metadata={},
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def list_sync_jobs(self, connection_id: UUID, limit: int = 20) -> List[SyncJob]:
        """Lists recent sync jobs for a connection."""
        stmt = (
            select(SyncJob)
            .where(SyncJob.connection_id == connection_id)
            .order_by(desc(SyncJob.created_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_or_create_checkpoint(
        self,
        connection_id: UUID,
        external_account_ref_id: UUID,
    ) -> SyncCheckpoint:
        """Retrieves or creates incremental sync checkpoint."""
        stmt = select(SyncCheckpoint).where(
            SyncCheckpoint.connection_id == connection_id,
            SyncCheckpoint.external_account_ref_id == external_account_ref_id,
        )
        res = await self.session.execute(stmt)
        chk = res.scalar_one_or_none()
        if not chk:
            chk = SyncCheckpoint(
                id=uuid4(),
                connection_id=connection_id,
                external_account_ref_id=external_account_ref_id,
                last_sync_timestamp=datetime.now(timezone.utc),
                checkpoint_metadata={},
            )
            self.session.add(chk)
            await self.session.flush()
        return chk

    # -------------------------------------------------------------------------
    # 6. Reconciliation Records
    # -------------------------------------------------------------------------
    async def create_reconciliation_record(
        self,
        workspace_id: UUID,
        account_id: UUID,
        connection_id: UUID,
        reconciliation_date: date,
        provider_reported_balance_paise: int,
        calculated_book_balance_paise: int,
        difference_paise: int,
        status: str,
        unmatched_transactions_count: int = 0,
        explanation: Optional[str] = None,
    ) -> ReconciliationRecord:
        """Records a new reconciliation snapshot."""
        rec = ReconciliationRecord(
            id=uuid4(),
            workspace_id=workspace_id,
            account_id=account_id,
            connection_id=connection_id,
            reconciliation_date=reconciliation_date,
            provider_reported_balance_paise=provider_reported_balance_paise,
            calculated_book_balance_paise=calculated_book_balance_paise,
            difference_paise=difference_paise,
            status=status,
            unmatched_transactions_count=unmatched_transactions_count,
            explanation=explanation,
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def list_reconciliation_records(
        self,
        workspace_id: UUID,
        account_id: Optional[UUID] = None,
        connection_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[ReconciliationRecord]:
        """Lists reconciliation records."""
        stmt = select(ReconciliationRecord).where(ReconciliationRecord.workspace_id == workspace_id)
        if account_id:
            stmt = stmt.where(ReconciliationRecord.account_id == account_id)
        if connection_id:
            stmt = stmt.where(ReconciliationRecord.connection_id == connection_id)
        stmt = stmt.order_by(desc(ReconciliationRecord.reconciliation_date), desc(ReconciliationRecord.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # 7. Audit Events
    # -------------------------------------------------------------------------
    async def log_audit_event(
        self,
        workspace_id: UUID,
        user_id: UUID,
        event_type: str,
        connection_id: Optional[UUID] = None,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConnectionAuditEvent:
        """Appends an immutable audit event."""
        event = ConnectionAuditEvent(
            id=uuid4(),
            workspace_id=workspace_id,
            connection_id=connection_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            event_metadata=metadata or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event
