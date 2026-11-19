"""
Arthsavora Business Finance Repository Layer
Scoped database queries for business profiles, clients, vendors,
invoices, line items, payments, payables, AR/AP aggregations, and activities.
Enforces multi-tenant workspace isolation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, desc, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.business import InvoiceStatus, PayableStatus
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


class BusinessRepository:
    """PostgreSQL data access layer for small business finance entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------------------------------------------------
    # Business Profile Operations
    # ---------------------------------------------------------------------------

    async def get_profile(self, workspace_id: uuid.UUID) -> Optional[BusinessProfile]:
        """Retrieves business profile for the workspace."""
        stmt = select(BusinessProfile).where(BusinessProfile.workspace_id == workspace_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_profile(
        self,
        workspace_id: uuid.UUID,
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
        """Creates or updates business profile settings."""
        profile = await self.get_profile(workspace_id)
        if not profile:
            profile = BusinessProfile(
                workspace_id=workspace_id,
                business_name=business_name,
                business_type=business_type,
                business_description=business_description,
                business_email=business_email,
                business_phone=business_phone,
                business_address=business_address or {},
                country=country,
                currency=currency,
                financial_year_start_month=financial_year_start_month,
                timezone=timezone_str,
                gstin=gstin.upper() if gstin else None,
                pan=pan.upper() if pan else None,
                tax_configuration=tax_configuration or {},
                invoice_settings=invoice_settings or {},
            )
            self.session.add(profile)
        else:
            profile.business_name = business_name
            profile.business_type = business_type
            if business_description is not None:
                profile.business_description = business_description
            if business_email is not None:
                profile.business_email = business_email
            if business_phone is not None:
                profile.business_phone = business_phone
            if business_address is not None:
                profile.business_address = business_address
            profile.country = country
            profile.currency = currency
            profile.financial_year_start_month = financial_year_start_month
            profile.timezone = timezone_str
            if gstin is not None:
                profile.gstin = gstin.upper() if gstin else None
            if pan is not None:
                profile.pan = pan.upper() if pan else None
            if tax_configuration is not None:
                profile.tax_configuration = tax_configuration
            if invoice_settings is not None:
                profile.invoice_settings = invoice_settings

        await self.session.flush()
        return profile

    # ---------------------------------------------------------------------------
    # Client Operations
    # ---------------------------------------------------------------------------

    async def list_clients(
        self,
        workspace_id: uuid.UUID,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessClient], int]:
        """Lists business clients with optional text search and status filter."""
        stmt = select(BusinessClient).where(BusinessClient.workspace_id == workspace_id)
        count_stmt = select(func.count(BusinessClient.id)).where(BusinessClient.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(BusinessClient.status == status)
            count_stmt = count_stmt.where(BusinessClient.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            filter_pred = or_(
                BusinessClient.name.ilike(pattern),
                BusinessClient.email.ilike(pattern),
                BusinessClient.gstin.ilike(pattern),
            )
            stmt = stmt.where(filter_pred)
            count_stmt = count_stmt.where(filter_pred)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(BusinessClient.name.asc()).limit(limit).offset(offset)
        clients = (await self.session.execute(stmt)).scalars().all()
        return list(clients), total

    async def get_client_by_id(
        self, workspace_id: uuid.UUID, client_id: uuid.UUID
    ) -> Optional[BusinessClient]:
        """Retrieves a client within workspace."""
        stmt = select(BusinessClient).where(
            BusinessClient.workspace_id == workspace_id,
            BusinessClient.id == client_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_client_by_name(
        self, workspace_id: uuid.UUID, name: str
    ) -> Optional[BusinessClient]:
        """Finds client with exact case-insensitive name match for duplicate detection."""
        stmt = select(BusinessClient).where(
            BusinessClient.workspace_id == workspace_id,
            func.lower(BusinessClient.name) == name.strip().lower(),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_client(
        self,
        workspace_id: uuid.UUID,
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
        """Creates a new business client."""
        client = BusinessClient(
            workspace_id=workspace_id,
            name=name.strip(),
            client_type=client_type,
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            billing_address=billing_address or {},
            gstin=gstin.strip().upper() if gstin else None,
            pan=pan.strip().upper() if pan else None,
            payment_terms_days=payment_terms_days,
            currency=currency,
            notes=notes,
            status="active",
        )
        self.session.add(client)
        await self.session.flush()
        return client

    async def update_client(
        self,
        client: BusinessClient,
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
        if name is not None:
            client.name = name.strip()
        if client_type is not None:
            client.client_type = client_type
        if email is not None:
            client.email = email.strip() if email else None
        if phone is not None:
            client.phone = phone.strip() if phone else None
        if billing_address is not None:
            client.billing_address = billing_address
        if gstin is not None:
            client.gstin = gstin.strip().upper() if gstin else None
        if pan is not None:
            client.pan = pan.strip().upper() if pan else None
        if payment_terms_days is not None:
            client.payment_terms_days = payment_terms_days
        if currency is not None:
            client.currency = currency
        if notes is not None:
            client.notes = notes
        if status is not None:
            client.status = status

        await self.session.flush()
        return client

    # ---------------------------------------------------------------------------
    # Vendor Operations
    # ---------------------------------------------------------------------------

    async def list_vendors(
        self,
        workspace_id: uuid.UUID,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessVendor], int]:
        """Lists business vendors with optional text search and status filter."""
        stmt = select(BusinessVendor).where(BusinessVendor.workspace_id == workspace_id)
        count_stmt = select(func.count(BusinessVendor.id)).where(BusinessVendor.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(BusinessVendor.status == status)
            count_stmt = count_stmt.where(BusinessVendor.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            filter_pred = or_(
                BusinessVendor.name.ilike(pattern),
                BusinessVendor.email.ilike(pattern),
                BusinessVendor.gstin.ilike(pattern),
            )
            stmt = stmt.where(filter_pred)
            count_stmt = count_stmt.where(filter_pred)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(BusinessVendor.name.asc()).limit(limit).offset(offset)
        vendors = (await self.session.execute(stmt)).scalars().all()
        return list(vendors), total

    async def get_vendor_by_id(
        self, workspace_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> Optional[BusinessVendor]:
        """Retrieves a vendor within workspace."""
        stmt = select(BusinessVendor).where(
            BusinessVendor.workspace_id == workspace_id,
            BusinessVendor.id == vendor_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_vendor_by_name(
        self, workspace_id: uuid.UUID, name: str
    ) -> Optional[BusinessVendor]:
        """Finds vendor with exact case-insensitive name match for duplicate detection."""
        stmt = select(BusinessVendor).where(
            BusinessVendor.workspace_id == workspace_id,
            func.lower(BusinessVendor.name) == name.strip().lower(),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_vendor(
        self,
        workspace_id: uuid.UUID,
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
        """Creates a new business vendor."""
        vendor = BusinessVendor(
            workspace_id=workspace_id,
            name=name.strip(),
            vendor_type=vendor_type,
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            billing_details=billing_details or {},
            gstin=gstin.strip().upper() if gstin else None,
            pan=pan.strip().upper() if pan else None,
            payment_terms_days=payment_terms_days,
            notes=notes,
            status="active",
        )
        self.session.add(vendor)
        await self.session.flush()
        return vendor

    async def update_vendor(
        self,
        vendor: BusinessVendor,
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
        if name is not None:
            vendor.name = name.strip()
        if vendor_type is not None:
            vendor.vendor_type = vendor_type
        if email is not None:
            vendor.email = email.strip() if email else None
        if phone is not None:
            vendor.phone = phone.strip() if phone else None
        if billing_details is not None:
            vendor.billing_details = billing_details
        if gstin is not None:
            vendor.gstin = gstin.strip().upper() if gstin else None
        if pan is not None:
            vendor.pan = pan.strip().upper() if pan else None
        if payment_terms_days is not None:
            vendor.payment_terms_days = payment_terms_days
        if notes is not None:
            vendor.notes = notes
        if status is not None:
            vendor.status = status

        await self.session.flush()
        return vendor

    # ---------------------------------------------------------------------------
    # Invoice Operations
    # ---------------------------------------------------------------------------

    async def list_invoices(
        self,
        workspace_id: uuid.UUID,
        client_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessInvoice], int]:
        """Lists invoices with filters."""
        stmt = (
            select(BusinessInvoice)
            .where(BusinessInvoice.workspace_id == workspace_id)
            .options(selectinload(BusinessInvoice.client), selectinload(BusinessInvoice.line_items))
        )
        count_stmt = select(func.count(BusinessInvoice.id)).where(BusinessInvoice.workspace_id == workspace_id)

        if client_id:
            stmt = stmt.where(BusinessInvoice.client_id == client_id)
            count_stmt = count_stmt.where(BusinessInvoice.client_id == client_id)
        if status:
            stmt = stmt.where(BusinessInvoice.status == status)
            count_stmt = count_stmt.where(BusinessInvoice.status == status)
        if start_date:
            stmt = stmt.where(BusinessInvoice.invoice_date >= start_date)
            count_stmt = count_stmt.where(BusinessInvoice.invoice_date >= start_date)
        if end_date:
            stmt = stmt.where(BusinessInvoice.invoice_date <= end_date)
            count_stmt = count_stmt.where(BusinessInvoice.invoice_date <= end_date)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(desc(BusinessInvoice.invoice_date), desc(BusinessInvoice.created_at)).limit(limit).offset(offset)
        invoices = (await self.session.execute(stmt)).scalars().all()
        return list(invoices), total

    async def get_invoice_by_id(
        self, workspace_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> Optional[BusinessInvoice]:
        """Retrieves invoice with line items, client, and payment history."""
        stmt = (
            select(BusinessInvoice)
            .where(
                BusinessInvoice.workspace_id == workspace_id,
                BusinessInvoice.id == invoice_id,
            )
            .options(
                selectinload(BusinessInvoice.client),
                selectinload(BusinessInvoice.line_items),
                selectinload(BusinessInvoice.payments),
                selectinload(BusinessInvoice.journal_entry),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_next_invoice_number(self, workspace_id: uuid.UUID, prefix: str = "INV") -> str:
        """Determines the next sequential invoice number for the active year."""
        current_year = date.today().year
        clean_prefix = (prefix or "INV").strip().upper()
        pattern = f"{clean_prefix}-{current_year}-%"

        stmt = select(func.count(BusinessInvoice.id)).where(
            BusinessInvoice.workspace_id == workspace_id,
            BusinessInvoice.invoice_number.like(pattern),
        )
        count = (await self.session.execute(stmt)).scalar() or 0
        next_seq = count + 1
        return f"{clean_prefix}-{current_year}-{next_seq:04d}"

    async def create_invoice(
        self,
        workspace_id: uuid.UUID,
        client_id: uuid.UUID,
        invoice_number: str,
        invoice_date: date,
        due_date: date,
        currency: str,
        subtotal_paise: int,
        discount_paise: int,
        tax_paise: int,
        total_paise: int,
        line_items_data: List[Dict[str, Any]],
        notes: Optional[str] = None,
        payment_instructions: Optional[str] = None,
        status: str = "draft",
    ) -> BusinessInvoice:
        """Creates a new invoice and its associated line items."""
        invoice = BusinessInvoice(
            workspace_id=workspace_id,
            client_id=client_id,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            currency=currency,
            subtotal_amount_paise=subtotal_paise,
            discount_amount_paise=discount_paise,
            tax_amount_paise=tax_paise,
            total_amount_paise=total_paise,
            paid_amount_paise=0,
            status=status,
            notes=notes,
            payment_instructions=payment_instructions,
            version=1,
        )
        self.session.add(invoice)
        await self.session.flush()

        for idx, item in enumerate(line_items_data):
            li = BusinessInvoiceLineItem(
                invoice_id=invoice.id,
                description=item["description"],
                hsn_sac_code=item.get("hsn_sac_code"),
                quantity=Decimal(str(item.get("quantity", 1))),
                unit_price_paise=item["unit_price_paise"],
                discount_paise=item.get("discount_paise", 0),
                tax_rate_percent=Decimal(str(item.get("tax_rate_percent", 0))),
                cgst_rate_percent=Decimal(str(item.get("cgst_rate_percent", 0))),
                sgst_rate_percent=Decimal(str(item.get("sgst_rate_percent", 0))),
                igst_rate_percent=Decimal(str(item.get("igst_rate_percent", 0))),
                tax_amount_paise=item.get("tax_amount_paise", 0),
                total_amount_paise=item["total_amount_paise"],
                line_order=item.get("line_order", idx),
            )
            self.session.add(li)

        await self.session.flush()
        return await self.get_invoice_by_id(workspace_id, invoice.id)  # type: ignore

    async def record_invoice_payment(
        self,
        workspace_id: uuid.UUID,
        invoice_id: uuid.UUID,
        payment_date: date,
        amount_paise: int,
        payment_method: str = "bank_transfer",
        reference_number: Optional[str] = None,
        financial_account_id: Optional[uuid.UUID] = None,
        transaction_id: Optional[uuid.UUID] = None,
        journal_entry_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> BusinessInvoicePayment:
        """Records payment against invoice and updates invoice balance."""
        payment = BusinessInvoicePayment(
            workspace_id=workspace_id,
            invoice_id=invoice_id,
            payment_date=payment_date,
            amount_paise=amount_paise,
            payment_method=payment_method,
            reference_number=reference_number,
            financial_account_id=financial_account_id,
            transaction_id=transaction_id,
            journal_entry_id=journal_entry_id,
            notes=notes,
            created_by_id=created_by_id,
        )
        self.session.add(payment)

        # Update invoice paid_amount_paise and status
        stmt = select(BusinessInvoice).where(BusinessInvoice.id == invoice_id).with_for_update()
        invoice = (await self.session.execute(stmt)).scalar_one()

        new_paid = invoice.paid_amount_paise + amount_paise
        invoice.paid_amount_paise = new_paid
        if new_paid >= invoice.total_amount_paise:
            invoice.status = InvoiceStatus.PAID.value
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID.value

        await self.session.flush()
        return payment

    # ---------------------------------------------------------------------------
    # Payable (Vendor Bill) Operations
    # ---------------------------------------------------------------------------

    async def list_payables(
        self,
        workspace_id: uuid.UUID,
        vendor_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BusinessPayable], int]:
        """Lists vendor bills with filters."""
        stmt = (
            select(BusinessPayable)
            .where(BusinessPayable.workspace_id == workspace_id)
            .options(selectinload(BusinessPayable.vendor))
        )
        count_stmt = select(func.count(BusinessPayable.id)).where(BusinessPayable.workspace_id == workspace_id)

        if vendor_id:
            stmt = stmt.where(BusinessPayable.vendor_id == vendor_id)
            count_stmt = count_stmt.where(BusinessPayable.vendor_id == vendor_id)
        if status:
            stmt = stmt.where(BusinessPayable.status == status)
            count_stmt = count_stmt.where(BusinessPayable.status == status)
        if start_date:
            stmt = stmt.where(BusinessPayable.bill_date >= start_date)
            count_stmt = count_stmt.where(BusinessPayable.bill_date >= start_date)
        if end_date:
            stmt = stmt.where(BusinessPayable.bill_date <= end_date)
            count_stmt = count_stmt.where(BusinessPayable.bill_date <= end_date)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(desc(BusinessPayable.bill_date), desc(BusinessPayable.created_at)).limit(limit).offset(offset)
        payables = (await self.session.execute(stmt)).scalars().all()
        return list(payables), total

    async def get_payable_by_id(
        self, workspace_id: uuid.UUID, payable_id: uuid.UUID
    ) -> Optional[BusinessPayable]:
        """Retrieves payable with vendor and payment history."""
        stmt = (
            select(BusinessPayable)
            .where(
                BusinessPayable.workspace_id == workspace_id,
                BusinessPayable.id == payable_id,
            )
            .options(
                selectinload(BusinessPayable.vendor),
                selectinload(BusinessPayable.payments),
                selectinload(BusinessPayable.journal_entry),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_payable(
        self,
        workspace_id: uuid.UUID,
        vendor_id: uuid.UUID,
        bill_date: date,
        due_date: date,
        subtotal_paise: int,
        tax_paise: int,
        total_paise: int,
        currency: str = "INR",
        bill_number: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        journal_entry_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        status: str = "recorded",
    ) -> BusinessPayable:
        """Creates a new payable record."""
        payable = BusinessPayable(
            workspace_id=workspace_id,
            vendor_id=vendor_id,
            bill_number=bill_number,
            bill_date=bill_date,
            due_date=due_date,
            currency=currency,
            subtotal_amount_paise=subtotal_paise,
            tax_amount_paise=tax_paise,
            total_amount_paise=total_paise,
            paid_amount_paise=0,
            status=status,
            category_id=category_id,
            document_id=document_id,
            journal_entry_id=journal_entry_id,
            notes=notes,
        )
        self.session.add(payable)
        await self.session.flush()
        return payable

    async def record_payable_payment(
        self,
        workspace_id: uuid.UUID,
        payable_id: uuid.UUID,
        payment_date: date,
        amount_paise: int,
        payment_method: str = "bank_transfer",
        reference_number: Optional[str] = None,
        financial_account_id: Optional[uuid.UUID] = None,
        transaction_id: Optional[uuid.UUID] = None,
        journal_entry_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> BusinessPayablePayment:
        """Records payment against vendor bill and updates bill balance."""
        payment = BusinessPayablePayment(
            workspace_id=workspace_id,
            payable_id=payable_id,
            payment_date=payment_date,
            amount_paise=amount_paise,
            payment_method=payment_method,
            reference_number=reference_number,
            financial_account_id=financial_account_id,
            transaction_id=transaction_id,
            journal_entry_id=journal_entry_id,
            notes=notes,
            created_by_id=created_by_id,
        )
        self.session.add(payment)

        # Update payable status
        stmt = select(BusinessPayable).where(BusinessPayable.id == payable_id).with_for_update()
        payable = (await self.session.execute(stmt)).scalar_one()

        new_paid = payable.paid_amount_paise + amount_paise
        payable.paid_amount_paise = new_paid
        if new_paid >= payable.total_amount_paise:
            payable.status = PayableStatus.PAID.value
        else:
            payable.status = PayableStatus.PARTIALLY_PAID.value

        await self.session.flush()
        return payment

    # ---------------------------------------------------------------------------
    # Aggregations & Analytics
    # ---------------------------------------------------------------------------

    async def get_overview_kpis(self, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """Calculates core business financial KPIs across invoices, payments, and payables."""
        # Invoiced Revenue & Collected Cash
        inv_stmt = select(
            func.coalesce(func.sum(BusinessInvoice.total_amount_paise), 0).label("invoiced"),
            func.coalesce(func.sum(BusinessInvoice.paid_amount_paise), 0).label("collected"),
            func.count(BusinessInvoice.id).label("total_invoices"),
        ).where(
            BusinessInvoice.workspace_id == workspace_id,
            BusinessInvoice.status != InvoiceStatus.CANCELLED.value,
        )
        inv_res = (await self.session.execute(inv_stmt)).one()

        invoiced_paise = int(inv_res.invoiced)
        collected_paise = int(inv_res.collected)
        total_invoices = int(inv_res.total_invoices)
        total_receivables_paise = max(0, invoiced_paise - collected_paise)

        # Payables
        pay_stmt = select(
            func.coalesce(func.sum(BusinessPayable.total_amount_paise), 0).label("total_bills"),
            func.coalesce(func.sum(BusinessPayable.paid_amount_paise), 0).label("paid_bills"),
            func.count(BusinessPayable.id).label("total_bills_count"),
        ).where(
            BusinessPayable.workspace_id == workspace_id,
            BusinessPayable.status != PayableStatus.CANCELLED.value,
        )
        pay_res = (await self.session.execute(pay_stmt)).one()

        total_bills_paise = int(pay_res.total_bills)
        paid_bills_paise = int(pay_res.paid_bills)
        total_payables_paise = max(0, total_bills_paise - paid_bills_paise)

        # Clients & Vendors Count
        c_stmt = select(func.count(BusinessClient.id)).where(BusinessClient.workspace_id == workspace_id, BusinessClient.status == "active")
        v_stmt = select(func.count(BusinessVendor.id)).where(BusinessVendor.workspace_id == workspace_id, BusinessVendor.status == "active")

        active_clients = (await self.session.execute(c_stmt)).scalar() or 0
        active_vendors = (await self.session.execute(v_stmt)).scalar() or 0

        # Overdue counts
        today = date.today()
        overdue_inv_stmt = select(func.count(BusinessInvoice.id)).where(
            BusinessInvoice.workspace_id == workspace_id,
            BusinessInvoice.due_date < today,
            BusinessInvoice.paid_amount_paise < BusinessInvoice.total_amount_paise,
            BusinessInvoice.status.in_([InvoiceStatus.ISSUED.value, InvoiceStatus.PARTIALLY_PAID.value]),
        )
        overdue_invoices_count = (await self.session.execute(overdue_inv_stmt)).scalar() or 0

        # Net Operating Result (Accrual: Invoiced - Bills; Cash: Collected - Paid)
        net_accrual_paise = invoiced_paise - total_bills_paise
        net_cash_paise = collected_paise - paid_bills_paise

        return {
            "invoiced_revenue_paise": invoiced_paise,
            "collected_revenue_paise": collected_paise,
            "total_receivables_paise": total_receivables_paise,
            "total_bills_paise": total_bills_paise,
            "paid_bills_paise": paid_bills_paise,
            "total_payables_paise": total_payables_paise,
            "net_operating_result_paise": net_accrual_paise,
            "net_cash_result_paise": net_cash_paise,
            "active_clients_count": active_clients,
            "active_vendors_count": active_vendors,
            "total_invoices_count": total_invoices,
            "overdue_invoices_count": overdue_invoices_count,
        }

    async def get_raw_invoices_for_aging(self, workspace_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieves active invoices for AR aging calculation."""
        stmt = select(
            BusinessInvoice.id,
            BusinessInvoice.invoice_number,
            BusinessInvoice.due_date,
            BusinessInvoice.total_amount_paise,
            BusinessInvoice.paid_amount_paise,
            BusinessInvoice.status,
        ).where(
            BusinessInvoice.workspace_id == workspace_id,
            BusinessInvoice.status.in_([InvoiceStatus.ISSUED.value, InvoiceStatus.PARTIALLY_PAID.value]),
        )
        res = await self.session.execute(stmt)
        return [
            {
                "id": str(r.id),
                "invoice_number": r.invoice_number,
                "due_date": r.due_date,
                "total_amount_paise": r.total_amount_paise,
                "paid_amount_paise": r.paid_amount_paise,
                "status": r.status,
            }
            for r in res.all()
        ]

    async def get_raw_payables_for_aging(self, workspace_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieves active payables for AP aging calculation."""
        stmt = select(
            BusinessPayable.id,
            BusinessPayable.bill_number,
            BusinessPayable.due_date,
            BusinessPayable.total_amount_paise,
            BusinessPayable.paid_amount_paise,
            BusinessPayable.status,
        ).where(
            BusinessPayable.workspace_id == workspace_id,
            BusinessPayable.status.in_([PayableStatus.RECORDED.value, PayableStatus.DUE.value, PayableStatus.PARTIALLY_PAID.value]),
        )
        res = await self.session.execute(stmt)
        return [
            {
                "id": str(r.id),
                "bill_number": r.bill_number,
                "due_date": r.due_date,
                "total_amount_paise": r.total_amount_paise,
                "paid_amount_paise": r.paid_amount_paise,
                "status": r.status,
            }
            for r in res.all()
        ]

    async def get_top_clients(self, workspace_id: uuid.UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top clients by invoiced revenue volume."""
        stmt = (
            select(
                BusinessClient.id,
                BusinessClient.name,
                func.coalesce(func.sum(BusinessInvoice.total_amount_paise), 0).label("total_invoiced"),
                func.count(BusinessInvoice.id).label("invoice_count"),
            )
            .join(BusinessInvoice, BusinessInvoice.client_id == BusinessClient.id)
            .where(
                BusinessClient.workspace_id == workspace_id,
                BusinessInvoice.status != InvoiceStatus.CANCELLED.value,
            )
            .group_by(BusinessClient.id, BusinessClient.name)
            .order_by(desc("total_invoiced"))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [
            {
                "client_id": str(r.id),
                "client_name": r.name,
                "total_invoiced_paise": int(r.total_invoiced),
                "invoice_count": int(r.invoice_count),
            }
            for r in res.all()
        ]

    async def get_top_vendors(self, workspace_id: uuid.UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top vendors by bill volume."""
        stmt = (
            select(
                BusinessVendor.id,
                BusinessVendor.name,
                func.coalesce(func.sum(BusinessPayable.total_amount_paise), 0).label("total_bills"),
                func.count(BusinessPayable.id).label("bill_count"),
            )
            .join(BusinessPayable, BusinessPayable.vendor_id == BusinessVendor.id)
            .where(
                BusinessVendor.workspace_id == workspace_id,
                BusinessPayable.status != PayableStatus.CANCELLED.value,
            )
            .group_by(BusinessVendor.id, BusinessVendor.name)
            .order_by(desc("total_bills"))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [
            {
                "vendor_id": str(r.id),
                "vendor_name": r.name,
                "total_bills_paise": int(r.total_bills),
                "bill_count": int(r.bill_count),
            }
            for r in res.all()
        ]

    # ---------------------------------------------------------------------------
    # Activity Logging
    # ---------------------------------------------------------------------------

    async def log_activity(
        self,
        workspace_id: uuid.UUID,
        activity_type: str,
        description: str,
        actor_user_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> BusinessActivity:
        """Appends an immutable audit event to the business activity ledger."""
        activity = BusinessActivity(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            activity_type=activity_type,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_json or {},
        )
        self.session.add(activity)
        await self.session.flush()
        return activity

    async def list_activities(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BusinessActivity]:
        """Lists recent activities chronologically."""
        stmt = (
            select(BusinessActivity)
            .where(BusinessActivity.workspace_id == workspace_id)
            .order_by(desc(BusinessActivity.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())
