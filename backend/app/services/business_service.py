"""
Arthsavora Small Business Finance Service Layer
Coordinates commercial operations, client/vendor management, exact minor-unit invoicing,
Accounts Receivable & Payable lifecycles, General Ledger double-entry posting,
cash flow monitoring, financial analytics, reports, and notification dispatch.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import io
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleViolationException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext, has_permission
from app.domain.business import (
    BusinessActivityType,
    BusinessType,
    InvoiceStatus,
    PayableStatus,
    PaymentMethod,
    calculate_invoice_totals,
    compute_ap_aging,
    compute_ar_aging,
    format_invoice_number,
    sanitize_csv_cell,
    validate_gstin,
    validate_pan,
)
from app.infrastructure.database.models.business import (
    BusinessActivity,
    BusinessClient,
    BusinessInvoice,
    BusinessInvoiceLineItem,
    BusinessInvoicePayment,
    BusinessPayable,
    BusinessPayablePayment,
    BusinessProfile,
    BusinessVendor,
)
from app.repositories.business_repository import BusinessRepository
from app.services.ledger_service import LedgerService
from app.services.notification.notification_service import NotificationService


class BusinessService:
    """Core domain orchestrator for small business finance workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BusinessRepository(session)
        self.ledger_service = LedgerService(session)
        self.notification_service = NotificationService(session)

    # ---------------------------------------------------------------------------
    # Business Profile Operations
    # ---------------------------------------------------------------------------

    async def get_or_create_profile(self, context: WorkspaceContext) -> BusinessProfile:
        """Retrieves or provisions the default business profile for the active workspace."""
        if context.workspace.type != "business":
            raise ValidationException("Active workspace is not a business workspace.")

        profile = await self.repo.get_profile(context.workspace.id)
        if not profile:
            profile = await self.repo.upsert_profile(
                workspace_id=context.workspace.id,
                business_name=context.workspace.name,
                business_type="freelancer",
                currency=context.workspace.default_currency,
                country=context.workspace.country,
                timezone_str=context.workspace.timezone,
            )
            await self.repo.log_activity(
                workspace_id=context.workspace.id,
                actor_user_id=context.current_user.id,
                activity_type=BusinessActivityType.PROFILE_UPDATED.value,
                description=f"Initialized default business profile for '{context.workspace.name}'",
                entity_type="business_profile",
                entity_id=profile.id,
            )
        return profile

    async def update_profile(
        self,
        context: WorkspaceContext,
        business_name: str,
        business_type: str = "freelancer",
        business_description: Optional[str] = None,
        business_email: Optional[str] = None,
        business_phone: Optional[str] = None,
        business_address: Optional[Dict[str, Any]] = None,
        country: str = "IN",
        currency: str = "INR",
        financial_year_start_month: int = 4,
        timezone_str: str = "Asia/Kolkata",
        gstin: Optional[str] = None,
        pan: Optional[str] = None,
        tax_configuration: Optional[Dict[str, Any]] = None,
        invoice_settings: Optional[Dict[str, Any]] = None,
    ) -> BusinessProfile:
        """Updates business profile metadata with tax validation."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_BUSINESS_PROFILE):
            raise ForbiddenException("Insufficient privileges to modify business profile.")

        if gstin and not validate_gstin(gstin):
            raise ValidationException(f"Invalid Indian GSTIN format: '{gstin}'. Expected 15-character format (e.g. 27AAPFU0939F1ZV).")
        if pan and not validate_pan(pan):
            raise ValidationException(f"Invalid Indian PAN format: '{pan}'. Expected 10-character format (e.g. ABCDE1234F).")

        profile = await self.repo.upsert_profile(
            workspace_id=context.workspace.id,
            business_name=business_name,
            business_type=business_type,
            business_description=business_description,
            business_email=business_email,
            business_phone=business_phone,
            business_address=business_address,
            country=country,
            currency=currency,
            financial_year_start_month=financial_year_start_month,
            timezone_str=timezone_str,
            gstin=gstin,
            pan=pan,
            tax_configuration=tax_configuration,
            invoice_settings=invoice_settings,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.PROFILE_UPDATED.value,
            description=f"Updated business profile for '{business_name}'",
            entity_type="business_profile",
            entity_id=profile.id,
        )
        return profile

    # ---------------------------------------------------------------------------
    # Client Management
    # ---------------------------------------------------------------------------

    async def list_clients(
        self,
        context: WorkspaceContext,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessClient], int]:
        """Lists clients belonging to the workspace."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges to view business clients.")
        return await self.repo.list_clients(context.workspace.id, search=search, status=status, limit=limit, offset=offset)

    async def get_client(self, context: WorkspaceContext, client_id: uuid.UUID) -> BusinessClient:
        """Retrieves single client with anti-IDOR check."""
        client = await self.repo.get_client_by_id(context.workspace.id, client_id)
        if not client:
            raise NotFoundException(f"Business client '{client_id}' not found.")
        return client

    async def create_client(
        self,
        context: WorkspaceContext,
        name: str,
        client_type: str = "business",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        billing_address: Optional[Dict[str, Any]] = None,
        gstin: Optional[str] = None,
        pan: Optional[str] = None,
        payment_terms_days: int = 30,
        currency: str = "INR",
        notes: Optional[str] = None,
    ) -> BusinessClient:
        """Creates a client with duplicate name detection and tax validation."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_CLIENTS):
            raise ForbiddenException("Insufficient privileges to create business clients.")

        if not name or not name.strip():
            raise ValidationException("Client name cannot be empty.")

        existing = await self.repo.find_client_by_name(context.workspace.id, name)
        if existing:
            raise ConflictException(f"A client with the name '{name.strip()}' already exists in this workspace.")

        if gstin and not validate_gstin(gstin):
            raise ValidationException(f"Invalid GSTIN format: '{gstin}'.")
        if pan and not validate_pan(pan):
            raise ValidationException(f"Invalid PAN format: '{pan}'.")

        client = await self.repo.create_client(
            workspace_id=context.workspace.id,
            name=name,
            client_type=client_type,
            email=email,
            phone=phone,
            billing_address=billing_address,
            gstin=gstin,
            pan=pan,
            payment_terms_days=payment_terms_days,
            currency=currency,
            notes=notes,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.CLIENT_CREATED.value,
            description=f"Added client '{client.name}' ({client.client_type})",
            entity_type="business_client",
            entity_id=client.id,
        )
        return client

    async def update_client(
        self,
        context: WorkspaceContext,
        client_id: uuid.UUID,
        name: Optional[str] = None,
        client_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        billing_address: Optional[Dict[str, Any]] = None,
        gstin: Optional[str] = None,
        pan: Optional[str] = None,
        payment_terms_days: Optional[int] = None,
        currency: Optional[str] = None,
        notes: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BusinessClient:
        """Updates client attributes."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_CLIENTS):
            raise ForbiddenException("Insufficient privileges to update business clients.")

        client = await self.get_client(context, client_id)

        if name and name.strip().lower() != client.name.lower():
            existing = await self.repo.find_client_by_name(context.workspace.id, name)
            if existing and existing.id != client.id:
                raise ConflictException(f"A client named '{name.strip()}' already exists.")

        if gstin and not validate_gstin(gstin):
            raise ValidationException(f"Invalid GSTIN format: '{gstin}'.")
        if pan and not validate_pan(pan):
            raise ValidationException(f"Invalid PAN format: '{pan}'.")

        updated = await self.repo.update_client(
            client=client,
            name=name,
            client_type=client_type,
            email=email,
            phone=phone,
            billing_address=billing_address,
            gstin=gstin,
            pan=pan,
            payment_terms_days=payment_terms_days,
            currency=currency,
            notes=notes,
            status=status,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.CLIENT_UPDATED.value,
            description=f"Updated client '{updated.name}'",
            entity_type="business_client",
            entity_id=updated.id,
        )
        return updated

    # ---------------------------------------------------------------------------
    # Vendor Management
    # ---------------------------------------------------------------------------

    async def list_vendors(
        self,
        context: WorkspaceContext,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessVendor], int]:
        """Lists vendors belonging to the workspace."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges to view vendors.")
        return await self.repo.list_vendors(context.workspace.id, search=search, status=status, limit=limit, offset=offset)

    async def get_vendor(self, context: WorkspaceContext, vendor_id: uuid.UUID) -> BusinessVendor:
        """Retrieves single vendor with anti-IDOR check."""
        vendor = await self.repo.get_vendor_by_id(context.workspace.id, vendor_id)
        if not vendor:
            raise NotFoundException(f"Business vendor '{vendor_id}' not found.")
        return vendor

    async def create_vendor(
        self,
        context: WorkspaceContext,
        name: str,
        vendor_type: str = "service_provider",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        billing_details: Optional[Dict[str, Any]] = None,
        gstin: Optional[str] = None,
        pan: Optional[str] = None,
        payment_terms_days: int = 30,
        notes: Optional[str] = None,
    ) -> BusinessVendor:
        """Creates a vendor with duplicate name detection and tax validation."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_VENDORS):
            raise ForbiddenException("Insufficient privileges to create vendors.")

        if not name or not name.strip():
            raise ValidationException("Vendor name cannot be empty.")

        existing = await self.repo.find_vendor_by_name(context.workspace.id, name)
        if existing:
            raise ConflictException(f"A vendor named '{name.strip()}' already exists in this workspace.")

        if gstin and not validate_gstin(gstin):
            raise ValidationException(f"Invalid GSTIN format: '{gstin}'.")
        if pan and not validate_pan(pan):
            raise ValidationException(f"Invalid PAN format: '{pan}'.")

        vendor = await self.repo.create_vendor(
            workspace_id=context.workspace.id,
            name=name,
            vendor_type=vendor_type,
            email=email,
            phone=phone,
            billing_details=billing_details,
            gstin=gstin,
            pan=pan,
            payment_terms_days=payment_terms_days,
            notes=notes,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.VENDOR_CREATED.value,
            description=f"Added vendor '{vendor.name}' ({vendor.vendor_type})",
            entity_type="business_vendor",
            entity_id=vendor.id,
        )
        return vendor

    async def update_vendor(
        self,
        context: WorkspaceContext,
        vendor_id: uuid.UUID,
        name: Optional[str] = None,
        vendor_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        billing_details: Optional[Dict[str, Any]] = None,
        gstin: Optional[str] = None,
        pan: Optional[str] = None,
        payment_terms_days: Optional[int] = None,
        notes: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BusinessVendor:
        """Updates vendor attributes."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_VENDORS):
            raise ForbiddenException("Insufficient privileges to update vendors.")

        vendor = await self.get_vendor(context, vendor_id)

        if name and name.strip().lower() != vendor.name.lower():
            existing = await self.repo.find_vendor_by_name(context.workspace.id, name)
            if existing and existing.id != vendor.id:
                raise ConflictException(f"A vendor named '{name.strip()}' already exists.")

        if gstin and not validate_gstin(gstin):
            raise ValidationException(f"Invalid GSTIN format: '{gstin}'.")
        if pan and not validate_pan(pan):
            raise ValidationException(f"Invalid PAN format: '{pan}'.")

        updated = await self.repo.update_vendor(
            vendor=vendor,
            name=name,
            vendor_type=vendor_type,
            email=email,
            phone=phone,
            billing_details=billing_details,
            gstin=gstin,
            pan=pan,
            payment_terms_days=payment_terms_days,
            notes=notes,
            status=status,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.VENDOR_UPDATED.value,
            description=f"Updated vendor '{updated.name}'",
            entity_type="business_vendor",
            entity_id=updated.id,
        )
        return updated

    # ---------------------------------------------------------------------------
    # Invoicing & Accounts Receivable Operations
    # ---------------------------------------------------------------------------

    async def list_invoices(
        self,
        context: WorkspaceContext,
        client_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessInvoice], int]:
        """Lists business invoices with filters."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges to view invoices.")
        return await self.repo.list_invoices(
            workspace_id=context.workspace.id,
            client_id=client_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def get_invoice(self, context: WorkspaceContext, invoice_id: uuid.UUID) -> BusinessInvoice:
        """Retrieves invoice with line items, payments, and client."""
        invoice = await self.repo.get_invoice_by_id(context.workspace.id, invoice_id)
        if not invoice:
            raise NotFoundException(f"Invoice '{invoice_id}' not found.")
        return invoice

    async def create_invoice(
        self,
        context: WorkspaceContext,
        client_id: uuid.UUID,
        invoice_date: date,
        due_date: date,
        line_items_data: List[Dict[str, Any]],
        currency: str = "INR",
        overall_discount_paise: int = 0,
        is_interstate: bool = False,
        custom_invoice_number: Optional[str] = None,
        notes: Optional[str] = None,
        payment_instructions: Optional[str] = None,
    ) -> BusinessInvoice:
        """Creates a draft invoice with exact minor unit calculations."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_INVOICES):
            raise ForbiddenException("Insufficient privileges to create invoices.")

        # Ensure client exists
        client = await self.get_client(context, client_id)

        if due_date < invoice_date:
            raise ValidationException("Invoice due date cannot be earlier than invoice date.")

        totals = calculate_invoice_totals(
            line_items_data=line_items_data,
            overall_discount_paise=overall_discount_paise,
            is_interstate=is_interstate,
        )

        # Invoice numbering
        if custom_invoice_number:
            inv_number = custom_invoice_number.strip().upper()
        else:
            profile = await self.get_or_create_profile(context)
            prefix = profile.invoice_settings.get("prefix", "INV") if profile.invoice_settings else "INV"
            inv_number = await self.repo.get_next_invoice_number(context.workspace.id, prefix=prefix)

        # Build line item payloads from calculated VO
        li_dicts = [
            {
                "description": item.description,
                "hsn_sac_code": item.hsn_sac_code,
                "quantity": item.quantity,
                "unit_price_paise": item.unit_price_paise,
                "discount_paise": item.discount_paise,
                "tax_rate_percent": item.tax_rate_percent,
                "cgst_rate_percent": item.cgst_rate_percent,
                "sgst_rate_percent": item.sgst_rate_percent,
                "igst_rate_percent": item.igst_rate_percent,
                "tax_amount_paise": item.tax_amount_paise,
                "total_amount_paise": item.total_amount_paise,
                "line_order": item.line_order,
            }
            for item in totals.line_items
        ]

        invoice = await self.repo.create_invoice(
            workspace_id=context.workspace.id,
            client_id=client.id,
            invoice_number=inv_number,
            invoice_date=invoice_date,
            due_date=due_date,
            currency=currency,
            subtotal_paise=totals.subtotal_paise,
            discount_paise=totals.discount_paise,
            tax_paise=totals.tax_paise,
            total_paise=totals.total_paise,
            line_items_data=li_dicts,
            notes=notes,
            payment_instructions=payment_instructions,
            status=InvoiceStatus.DRAFT.value,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.INVOICE_CREATED.value,
            description=f"Drafted invoice '{invoice.invoice_number}' for {client.name} (₹{invoice.total_amount_paise / 100:,.2f})",
            entity_type="business_invoice",
            entity_id=invoice.id,
        )
        return invoice

    async def issue_invoice(self, context: WorkspaceContext, invoice_id: uuid.UUID) -> BusinessInvoice:
        """
        Transitions draft invoice to immutable issued status.
        Creates an immutable snapshot and posts a double-entry journal entry to the General Ledger:
        - Debit: 1040 Accounts Receivable (Asset)
        - Credit: 4020 Business Sales & Invoicing (Revenue)
        """
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_INVOICES):
            raise ForbiddenException("Insufficient privileges to issue invoices.")

        invoice = await self.get_invoice(context, invoice_id)
        if invoice.status != InvoiceStatus.DRAFT.value:
            raise BusinessRuleViolationException(
                "INVALID_INVOICE_STATE",
                f"Only draft invoices can be issued. Current status: '{invoice.status}'.",
            )

        # 1. Capture immutable snapshot
        snapshot = {
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "client": {
                "id": str(invoice.client.id),
                "name": invoice.client.name,
                "gstin": invoice.client.gstin,
                "email": invoice.client.email,
                "billing_address": invoice.client.billing_address,
            },
            "subtotal_amount_paise": invoice.subtotal_amount_paise,
            "discount_amount_paise": invoice.discount_amount_paise,
            "tax_amount_paise": invoice.tax_amount_paise,
            "total_amount_paise": invoice.total_amount_paise,
            "line_items": [
                {
                    "description": li.description,
                    "hsn_sac_code": li.hsn_sac_code,
                    "quantity": float(li.quantity),
                    "unit_price_paise": li.unit_price_paise,
                    "tax_rate_percent": float(li.tax_rate_percent),
                    "tax_amount_paise": li.tax_amount_paise,
                    "total_amount_paise": li.total_amount_paise,
                }
                for li in invoice.line_items
            ],
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

        # 2. Double-Entry General Ledger Posting
        await self.ledger_service.ensure_chart_of_accounts(context.workspace.id)
        ar_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "1040")
        sales_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "4020")

        journal_id = None
        if ar_account and sales_account:
            lines_data = [
                {
                    "ledger_account_id": ar_account.id,
                    "entry_type": "debit",
                    "amount": Decimal(invoice.total_amount_paise) / Decimal("100.0"),
                    "amount_paise": invoice.total_amount_paise,
                    "description": f"Invoice {invoice.invoice_number} issued to {invoice.client.name}",
                },
                {
                    "ledger_account_id": sales_account.id,
                    "entry_type": "credit",
                    "amount": Decimal(invoice.total_amount_paise) / Decimal("100.0"),
                    "amount_paise": invoice.total_amount_paise,
                    "description": f"Revenue recognized from Invoice {invoice.invoice_number}",
                },
            ]
            entry_number = f"JE-INV-{invoice.invoice_number}"
            draft_je = await self.ledger_service.create_draft_journal(
                workspace_id=context.workspace.id,
                entry_number=entry_number,
                entry_date=invoice.invoice_date,
                description=f"Accrual revenue recognition for Invoice {invoice.invoice_number}",
                lines_data=lines_data,
                source_type="invoice",
                source_id=invoice.id,
                created_by=context.current_user.id,
            )
            posted_je = await self.ledger_service.post_journal_entry(
                workspace_id=context.workspace.id,
                journal_id=draft_je.id,
                actor_id=context.current_user.id,
            )
            journal_id = posted_je.id

        # 3. Update invoice state
        invoice.status = InvoiceStatus.ISSUED.value
        invoice.issued_at = datetime.now(timezone.utc)
        invoice.issued_snapshot = snapshot
        invoice.journal_entry_id = journal_id
        await self.session.flush()

        # 4. Activity Log & Notification
        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.INVOICE_ISSUED.value,
            description=f"Issued invoice '{invoice.invoice_number}' (₹{invoice.total_amount_paise / 100:,.2f})",
            entity_type="business_invoice",
            entity_id=invoice.id,
        )

        try:
            await self.notification_service.dispatch_notification(
                workspace_id=context.workspace.id,
                event_type="INVOICE_ISSUED",
                title="Invoice Issued",
                message=f"Invoice {invoice.invoice_number} for ₹{invoice.total_amount_paise / 100:,.2f} has been issued to {invoice.client.name}.",
                severity="info",
                category="business",
                source_id=invoice.id,
                metadata={"invoice_id": str(invoice.id), "invoice_number": invoice.invoice_number},
            )
        except Exception:
            pass

        return invoice

    async def cancel_invoice(
        self, context: WorkspaceContext, invoice_id: uuid.UUID, reason: str
    ) -> BusinessInvoice:
        """Cancels an invoice and reverses any posted general ledger entries."""
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_INVOICES):
            raise ForbiddenException("Insufficient privileges to cancel invoices.")

        invoice = await self.get_invoice(context, invoice_id)
        if invoice.status == InvoiceStatus.PAID.value:
            raise BusinessRuleViolationException(
                "CANNOT_CANCEL_PAID_INVOICE",
                "Fully paid invoices cannot be cancelled. Issue a credit note or recorded refund instead.",
            )
        if invoice.status == InvoiceStatus.CANCELLED.value:
            return invoice

        # Reverse journal entry if one exists
        if invoice.journal_entry_id:
            try:
                await self.ledger_service.reverse_journal_entry(
                    workspace_id=context.workspace.id,
                    journal_id=invoice.journal_entry_id,
                    reason=f"Cancellation of invoice {invoice.invoice_number}: {reason}",
                    actor_id=context.current_user.id,
                )
            except Exception:
                pass

        invoice.status = InvoiceStatus.CANCELLED.value
        invoice.cancelled_at = datetime.now(timezone.utc)
        invoice.cancellation_reason = reason
        await self.session.flush()

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.INVOICE_CANCELLED.value,
            description=f"Cancelled invoice '{invoice.invoice_number}'. Reason: {reason}",
            entity_type="business_invoice",
            entity_id=invoice.id,
        )
        return invoice

    async def record_invoice_payment(
        self,
        context: WorkspaceContext,
        invoice_id: uuid.UUID,
        payment_date: date,
        amount_paise: int,
        payment_method: str = "bank_transfer",
        reference_number: Optional[str] = None,
        financial_account_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> BusinessInvoicePayment:
        """
        Records a payment allocation against an issued invoice.
        Enforces over-allocation prevention.
        Posts double-entry General Ledger entry:
        - Debit: 1020 Bank Accounts (Asset)
        - Credit: 1040 Accounts Receivable (Asset)
        """
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_INVOICES):
            raise ForbiddenException("Insufficient privileges to record invoice payments.")

        invoice = await self.get_invoice(context, invoice_id)
        if invoice.status not in (InvoiceStatus.ISSUED.value, InvoiceStatus.PARTIALLY_PAID.value):
            raise BusinessRuleViolationException(
                "INVALID_INVOICE_STATUS",
                f"Cannot record payment for invoice in status '{invoice.status}'.",
            )

        remaining_balance = invoice.total_amount_paise - invoice.paid_amount_paise
        if amount_paise <= 0:
            raise ValidationException("Payment amount must be strictly greater than zero.")
        if amount_paise > remaining_balance:
            raise ValidationException(
                f"Payment amount (₹{amount_paise / 100:,.2f}) exceeds remaining balance of ₹{remaining_balance / 100:,.2f}."
            )

        # Double-entry ledger integration
        journal_id = None
        await self.ledger_service.ensure_chart_of_accounts(context.workspace.id)
        bank_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "1020")
        ar_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "1040")

        if bank_account and ar_account:
            lines_data = [
                {
                    "ledger_account_id": bank_account.id,
                    "entry_type": "debit",
                    "amount": Decimal(amount_paise) / Decimal("100.0"),
                    "amount_paise": amount_paise,
                    "financial_account_id": financial_account_id,
                    "description": f"Payment received for Invoice {invoice.invoice_number}",
                },
                {
                    "ledger_account_id": ar_account.id,
                    "entry_type": "credit",
                    "amount": Decimal(amount_paise) / Decimal("100.0"),
                    "amount_paise": amount_paise,
                    "description": f"AR reduction for Invoice {invoice.invoice_number}",
                },
            ]
            entry_number = f"JE-PMT-{invoice.invoice_number}-{uuid.uuid4().hex[:6].upper()}"
            draft_je = await self.ledger_service.create_draft_journal(
                workspace_id=context.workspace.id,
                entry_number=entry_number,
                entry_date=payment_date,
                description=f"Payment settlement for Invoice {invoice.invoice_number}",
                lines_data=lines_data,
                source_type="invoice_payment",
                source_id=invoice.id,
                created_by=context.current_user.id,
            )
            posted_je = await self.ledger_service.post_journal_entry(
                workspace_id=context.workspace.id,
                journal_id=draft_je.id,
                actor_id=context.current_user.id,
            )
            journal_id = posted_je.id

        payment = await self.repo.record_invoice_payment(
            workspace_id=context.workspace.id,
            invoice_id=invoice.id,
            payment_date=payment_date,
            amount_paise=amount_paise,
            payment_method=payment_method,
            reference_number=reference_number,
            financial_account_id=financial_account_id,
            journal_entry_id=journal_id,
            notes=notes,
            created_by_id=context.current_user.id,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.INVOICE_PAID.value,
            description=f"Recorded payment of ₹{amount_paise / 100:,.2f} for invoice '{invoice.invoice_number}'",
            entity_type="business_invoice",
            entity_id=invoice.id,
        )

        try:
            await self.notification_service.dispatch_notification(
                workspace_id=context.workspace.id,
                event_type="PAYMENT_RECORDED",
                title="Payment Recorded",
                message=f"Received payment of ₹{amount_paise / 100:,.2f} for Invoice {invoice.invoice_number}.",
                severity="success",
                category="business",
                source_id=invoice.id,
                metadata={"invoice_id": str(invoice.id), "amount_paise": amount_paise},
            )
        except Exception:
            pass

        return payment

    # ---------------------------------------------------------------------------
    # Payables (Vendor Bills) Operations
    # ---------------------------------------------------------------------------

    async def list_payables(
        self,
        context: WorkspaceContext,
        vendor_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessPayable], int]:
        """Lists vendor bills with filters."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges to view payables.")
        return await self.repo.list_payables(
            workspace_id=context.workspace.id,
            vendor_id=vendor_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def get_payable(self, context: WorkspaceContext, payable_id: uuid.UUID) -> BusinessPayable:
        """Retrieves single payable with anti-IDOR check."""
        payable = await self.repo.get_payable_by_id(context.workspace.id, payable_id)
        if not payable:
            raise NotFoundException(f"Vendor bill '{payable_id}' not found.")
        return payable

    async def create_payable(
        self,
        context: WorkspaceContext,
        vendor_id: uuid.UUID,
        bill_date: date,
        due_date: date,
        subtotal_paise: int,
        tax_paise: int = 0,
        currency: str = "INR",
        bill_number: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> BusinessPayable:
        """
        Records a vendor bill and posts double-entry accrual entry:
        - Debit: 5000 General & Operating Expenses
        - Credit: 2020 Accounts Payable (Liability)
        """
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_PAYABLES):
            raise ForbiddenException("Insufficient privileges to record vendor bills.")

        vendor = await self.get_vendor(context, vendor_id)
        total_paise = subtotal_paise + tax_paise

        # Double-entry ledger integration
        journal_id = None
        await self.ledger_service.ensure_chart_of_accounts(context.workspace.id)
        expense_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "5000")
        ap_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "2020")

        if expense_account and ap_account:
            lines_data = [
                {
                    "ledger_account_id": expense_account.id,
                    "entry_type": "debit",
                    "amount": Decimal(total_paise) / Decimal("100.0"),
                    "amount_paise": total_paise,
                    "description": f"Vendor bill {bill_number or ''} from {vendor.name}",
                },
                {
                    "ledger_account_id": ap_account.id,
                    "entry_type": "credit",
                    "amount": Decimal(total_paise) / Decimal("100.0"),
                    "amount_paise": total_paise,
                    "description": f"AP liability for {vendor.name}",
                },
            ]
            entry_number = f"JE-BILL-{uuid.uuid4().hex[:8].upper()}"
            draft_je = await self.ledger_service.create_draft_journal(
                workspace_id=context.workspace.id,
                entry_number=entry_number,
                entry_date=bill_date,
                description=f"Accrual bill recording for {vendor.name}",
                lines_data=lines_data,
                source_type="vendor_bill",
                created_by=context.current_user.id,
            )
            posted_je = await self.ledger_service.post_journal_entry(
                workspace_id=context.workspace.id,
                journal_id=draft_je.id,
                actor_id=context.current_user.id,
            )
            journal_id = posted_je.id

        payable = await self.repo.create_payable(
            workspace_id=context.workspace.id,
            vendor_id=vendor.id,
            bill_date=bill_date,
            due_date=due_date,
            subtotal_paise=subtotal_paise,
            tax_paise=tax_paise,
            total_paise=total_paise,
            currency=currency,
            bill_number=bill_number,
            category_id=category_id,
            document_id=document_id,
            journal_entry_id=journal_id,
            notes=notes,
            status=PayableStatus.RECORDED.value,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.PAYABLE_RECORDED.value,
            description=f"Recorded vendor bill from '{vendor.name}' (₹{total_paise / 100:,.2f})",
            entity_type="business_payable",
            entity_id=payable.id,
        )
        return payable

    async def record_payable_payment(
        self,
        context: WorkspaceContext,
        payable_id: uuid.UUID,
        payment_date: date,
        amount_paise: int,
        payment_method: str = "bank_transfer",
        reference_number: Optional[str] = None,
        financial_account_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> BusinessPayablePayment:
        """
        Records payment of vendor bill.
        Posts double-entry General Ledger entry:
        - Debit: 2020 Accounts Payable (Liability reduction)
        - Credit: 1020 Bank Accounts (Asset reduction)
        """
        if not has_permission(context.workspace.type, context.role, Permission.MANAGE_PAYABLES):
            raise ForbiddenException("Insufficient privileges to record vendor payments.")

        payable = await self.get_payable(context, payable_id)
        remaining = payable.total_amount_paise - payable.paid_amount_paise
        if amount_paise <= 0:
            raise ValidationException("Payment amount must be strictly positive.")
        if amount_paise > remaining:
            raise ValidationException(
                f"Payment amount (₹{amount_paise / 100:,.2f}) exceeds outstanding bill balance of ₹{remaining / 100:,.2f}."
            )

        # Double-entry ledger integration
        journal_id = None
        await self.ledger_service.ensure_chart_of_accounts(context.workspace.id)
        ap_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "2020")
        bank_account = await self.ledger_service.account_repo.get_by_code(context.workspace.id, "1020")

        if ap_account and bank_account:
            lines_data = [
                {
                    "ledger_account_id": ap_account.id,
                    "entry_type": "debit",
                    "amount": Decimal(amount_paise) / Decimal("100.0"),
                    "amount_paise": amount_paise,
                    "description": f"AP settlement for vendor bill {payable.bill_number or ''}",
                },
                {
                    "ledger_account_id": bank_account.id,
                    "entry_type": "credit",
                    "amount": Decimal(amount_paise) / Decimal("100.0"),
                    "amount_paise": amount_paise,
                    "financial_account_id": financial_account_id,
                    "description": f"Cash outflow for vendor bill {payable.bill_number or ''}",
                },
            ]
            entry_number = f"JE-BILL-PMT-{uuid.uuid4().hex[:6].upper()}"
            draft_je = await self.ledger_service.create_draft_journal(
                workspace_id=context.workspace.id,
                entry_number=entry_number,
                entry_date=payment_date,
                description=f"Vendor payment for bill {payable.bill_number or ''}",
                lines_data=lines_data,
                source_type="payable_payment",
                source_id=payable.id,
                created_by=context.current_user.id,
            )
            posted_je = await self.ledger_service.post_journal_entry(
                workspace_id=context.workspace.id,
                journal_id=draft_je.id,
                actor_id=context.current_user.id,
            )
            journal_id = posted_je.id

        payment = await self.repo.record_payable_payment(
            workspace_id=context.workspace.id,
            payable_id=payable.id,
            payment_date=payment_date,
            amount_paise=amount_paise,
            payment_method=payment_method,
            reference_number=reference_number,
            financial_account_id=financial_account_id,
            journal_entry_id=journal_id,
            notes=notes,
            created_by_id=context.current_user.id,
        )

        await self.repo.log_activity(
            workspace_id=context.workspace.id,
            actor_user_id=context.current_user.id,
            activity_type=BusinessActivityType.PAYABLE_PAID.value,
            description=f"Paid ₹{amount_paise / 100:,.2f} against vendor bill '{payable.bill_number or payable.id}'",
            entity_type="business_payable",
            entity_id=payable.id,
        )
        return payment

    # ---------------------------------------------------------------------------
    # Analytics & Reports
    # ---------------------------------------------------------------------------

    async def get_overview(self, context: WorkspaceContext) -> Dict[str, Any]:
        """Provides high-level business financial KPIs."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges to view business dashboard.")
        return await self.repo.get_overview_kpis(context.workspace.id)

    async def get_receivables_aging(self, context: WorkspaceContext, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Calculates AR aging schedule."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges.")
        invoices = await self.repo.get_raw_invoices_for_aging(context.workspace.id)
        vo = compute_ar_aging(invoices, as_of_date=as_of_date)
        return {
            "current_paise": vo.current_paise,
            "days_1_30_paise": vo.days_1_30_paise,
            "days_31_60_paise": vo.days_31_60_paise,
            "days_61_90_paise": vo.days_61_90_paise,
            "days_91_plus_paise": vo.days_91_plus_paise,
            "total_outstanding_paise": vo.total_outstanding_paise,
        }

    async def get_payables_aging(self, context: WorkspaceContext, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Calculates AP aging schedule."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges.")
        payables = await self.repo.get_raw_payables_for_aging(context.workspace.id)
        vo = compute_ap_aging(payables, as_of_date=as_of_date)
        return {
            "current_paise": vo.current_paise,
            "days_1_30_paise": vo.days_1_30_paise,
            "days_31_60_paise": vo.days_31_60_paise,
            "days_61_90_paise": vo.days_61_90_paise,
            "days_91_plus_paise": vo.days_91_plus_paise,
            "total_outstanding_paise": vo.total_outstanding_paise,
        }

    async def get_analytics_summary(self, context: WorkspaceContext) -> Dict[str, Any]:
        """Aggregates business intelligence, top clients, top vendors, and aging."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges.")

        kpis = await self.repo.get_overview_kpis(context.workspace.id)
        ar_aging = await self.get_receivables_aging(context)
        ap_aging = await self.get_payables_aging(context)
        top_clients = await self.repo.get_top_clients(context.workspace.id, limit=5)
        top_vendors = await self.repo.get_top_vendors(context.workspace.id, limit=5)

        return {
            "kpis": kpis,
            "ar_aging": ar_aging,
            "ap_aging": ap_aging,
            "top_clients": top_clients,
            "top_vendors": top_vendors,
        }

    async def export_invoices_csv(self, context: WorkspaceContext) -> str:
        """Exports invoices to CSV with formula injection defense."""
        if not has_permission(context.workspace.type, context.role, Permission.EXPORT_ANALYTICS):
            raise ForbiddenException("Insufficient privileges to export financial reports.")

        invoices, _ = await self.repo.list_invoices(context.workspace.id, limit=1000)
        output = io.StringIO()
        output.write("Invoice Number,Date,Due Date,Client,Status,Subtotal (INR),Tax (INR),Total (INR),Paid (INR),Balance (INR)\n")

        for inv in invoices:
            balance = max(0, inv.total_amount_paise - inv.paid_amount_paise)
            row = [
                sanitize_csv_cell(inv.invoice_number),
                sanitize_csv_cell(inv.invoice_date.isoformat()),
                sanitize_csv_cell(inv.due_date.isoformat()),
                sanitize_csv_cell(inv.client.name if inv.client else ""),
                sanitize_csv_cell(inv.status),
                f"{inv.subtotal_amount_paise / 100:.2f}",
                f"{inv.tax_amount_paise / 100:.2f}",
                f"{inv.total_amount_paise / 100:.2f}",
                f"{inv.paid_amount_paise / 100:.2f}",
                f"{balance / 100:.2f}",
            ]
            output.write(",".join(f'"{c}"' for c in row) + "\n")

        return output.getvalue()

    async def generate_invoice_html(self, context: WorkspaceContext, invoice_id: uuid.UUID) -> str:
        """Renders professional HTML document for invoice viewing and printing."""
        invoice = await self.get_invoice(context, invoice_id)
        profile = await self.get_or_create_profile(context)

        items_rows = ""
        for item in invoice.line_items:
            items_rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item.description}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item.hsn_sac_code or '-'}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">{float(item.quantity):.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">₹{item.unit_price_paise / 100:,.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">{float(item.tax_rate_percent):.1f}%</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: bold;">₹{item.total_amount_paise / 100:,.2f}</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invoice {invoice.invoice_number}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1f2937; margin: 40px; }}
                .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #2563eb; padding-bottom: 20px; }}
                .company-title {{ font-size: 24px; font-weight: bold; color: #1e3a8a; }}
                .inv-title {{ font-size: 28px; font-weight: bold; color: #111827; text-align: right; }}
                .meta-table td {{ padding: 4px 8px; font-size: 14px; }}
                table.items {{ width: 100%; border-collapse: collapse; margin-top: 30px; }}
                table.items th {{ background: #f3f4f6; padding: 10px; text-align: left; font-size: 13px; text-transform: uppercase; }}
                .totals {{ margin-top: 20px; float: right; width: 300px; }}
                .totals-row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }}
                .total-due {{ font-size: 18px; font-weight: bold; border-top: 2px solid #111827; border-bottom: 2px solid #111827; padding: 10px 0; color: #1e40af; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <div class="company-title">{profile.business_name}</div>
                    <div style="font-size: 14px; color: #4b5563; margin-top: 4px;">{profile.business_type.replace('_', ' ').title()}</div>
                    {f'<div style="font-size: 14px; color: #4b5563;">GSTIN: {profile.gstin}</div>' if profile.gstin else ''}
                    {f'<div style="font-size: 14px; color: #4b5563;">PAN: {profile.pan}</div>' if profile.pan else ''}
                    {f'<div style="font-size: 14px; color: #4b5563;">{profile.business_email}</div>' if profile.business_email else ''}
                </div>
                <div>
                    <div class="inv-title">TAX INVOICE</div>
                    <table class="meta-table" style="margin-top: 8px;">
                        <tr><td><strong>Invoice #:</strong></td><td>{invoice.invoice_number}</td></tr>
                        <tr><td><strong>Date:</strong></td><td>{invoice.invoice_date.strftime('%d-%b-%Y')}</td></tr>
                        <tr><td><strong>Due Date:</strong></td><td>{invoice.due_date.strftime('%d-%b-%Y')}</td></tr>
                        <tr><td><strong>Status:</strong></td><td style="text-transform: uppercase; font-weight: bold;">{invoice.status}</td></tr>
                    </table>
                </div>
            </div>

            <div style="margin-top: 30px; display: flex; justify-content: space-between;">
                <div>
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; color: #6b7280;">Billed To:</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">{invoice.client.name}</div>
                    {f'<div style="font-size: 14px; color: #4b5563;">GSTIN: {invoice.client.gstin}</div>' if invoice.client.gstin else ''}
                    {f'<div style="font-size: 14px; color: #4b5563;">{invoice.client.email}</div>' if invoice.client.email else ''}
                    {f'<div style="font-size: 14px; color: #4b5563;">{invoice.client.phone}</div>' if invoice.client.phone else ''}
                </div>
            </div>

            <table class="items">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th style="text-align: center;">HSN/SAC</th>
                        <th style="text-align: right;">Qty</th>
                        <th style="text-align: right;">Unit Price</th>
                        <th style="text-align: right;">GST Rate</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {items_rows}
                </tbody>
            </table>

            <div class="totals">
                <div class="totals-row"><span>Subtotal:</span><span>₹{invoice.subtotal_amount_paise / 100:,.2f}</span></div>
                {f'<div class="totals-row"><span>Discount:</span><span>-₹{invoice.discount_amount_paise / 100:,.2f}</span></div>' if invoice.discount_amount_paise > 0 else ''}
                <div class="totals-row"><span>Total GST:</span><span>₹{invoice.tax_amount_paise / 100:,.2f}</span></div>
                <div class="totals-row total-due"><span>Total Amount:</span><span>₹{invoice.total_amount_paise / 100:,.2f}</span></div>
                <div class="totals-row" style="margin-top: 6px;"><span>Amount Paid:</span><span>₹{invoice.paid_amount_paise / 100:,.2f}</span></div>
                <div class="totals-row" style="font-weight: bold; color: #b91c1c;"><span>Balance Due:</span><span>₹{max(0, invoice.total_amount_paise - invoice.paid_amount_paise) / 100:,.2f}</span></div>
            </div>

            <div style="clear: both; margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                {f'<div style="font-size: 14px;"><strong>Payment Instructions:</strong><p style="color: #4b5563; margin-top: 4px;">{invoice.payment_instructions}</p></div>' if invoice.payment_instructions else ''}
                {f'<div style="font-size: 14px; margin-top: 10px;"><strong>Notes:</strong><p style="color: #4b5563; margin-top: 4px;">{invoice.notes}</p></div>' if invoice.notes else ''}
            </div>
        </body>
        </html>
        """
        return html

    async def list_activities(self, context: WorkspaceContext, limit: int = 50, offset: int = 0) -> List[BusinessActivity]:
        """Lists chronological audit log events."""
        if not has_permission(context.workspace.type, context.role, Permission.VIEW_BUSINESS_FINANCE):
            raise ForbiddenException("Insufficient privileges.")
        return await self.repo.list_activities(context.workspace.id, limit=limit, offset=offset)
