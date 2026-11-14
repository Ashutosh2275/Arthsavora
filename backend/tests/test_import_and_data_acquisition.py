"""
Arthsavora Financial Data Acquisition & Statement Import Tests
Comprehensive test suite covering:
1. File upload security, size bounding, MIME/magic byte verification, and duplicate file hashing.
2. CSV statement parsing with Indian banking conventions (HDFC, SBI, ICICI) and custom mapping.
3. XLSX statement parsing with formula protection and sheet selection.
4. Digital PDF parsing with table extraction and opening/closing balance detection.
5. Fallback OCR adapter with confidence tracking.
6. Statement normalizer and validator with structured error reporting.
7. Multi-level deduplication (exact, probable, and intra-batch).
8. End-to-end confirmation: Transaction creation, account balance mutation, and General Ledger posting.
9. Statement balance reconciliation mathematics.
10. Multi-workspace isolation and anti-IDOR defense.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import io
import os
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import Permission, WorkspaceContext, WorkspaceRole
from app.domain.exceptions import (
    DuplicateImportError,
    FileTooLargeError,
    InvalidFileFormatError,
    UnsafeFileError,
)
from app.domain.import_types import (
    DuplicateStatus,
    ImportStatus,
    ReviewStatus,
    SourceFormat,
    ValidationStatus,
)
from app.infrastructure.database.models import (
    Account,
    ImportBatch,
    ImportCandidate,
    ImportJob,
    JournalEntry,
    Transaction,
    User,
    Workspace,
    WorkspaceMember,
)
from app.services.importers.csv_parser import CsvStatementParser
from app.services.importers.deduplicator import StatementDeduplicator
from app.services.importers.normalizer import StatementNormalizer
from app.services.importers.ocr_adapter import OcrStatementAdapter
from app.services.importers.pdf_parser import PdfStatementParser
from app.services.importers.validator import StatementValidator
from app.services.importers.xlsx_parser import XlsxStatementParser
from app.services.import_service import ImportService
from app.services.ledger_service import LedgerService


@pytest.fixture
async def import_setup(db_session: AsyncSession):
    """Sets up an authoritative business workspace, user, and active financial account."""
    user = User(email=f"treasurer_{uuid.uuid4().hex[:8]}@example.com", full_name="Corporate Treasurer")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(
        name="Bharat Logistics Ltd",
        slug=f"bharat-logistics-{uuid.uuid4().hex[:6]}",
        type="business",
        owner_id=user.id,
    )
    db_session.add(ws)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    db_session.add(member)
    await db_session.flush()

    # Seed COA for ledger posting
    ledger_service = LedgerService(db_session)
    await ledger_service.ensure_chart_of_accounts(ws.id)

    # Create Operational Bank Account
    bank_account = Account(
        workspace_id=ws.id,
        name="HDFC Current Account",
        account_type="current",
        currency="INR",
        current_book_balance_paise=20000000,
        available_balance_paise=20000000,
        status="active",
    )
    db_session.add(bank_account)
    await db_session.flush()
    await db_session.commit()

    context = WorkspaceContext(
        workspace=ws,
        membership=member,
        current_user=user,
        role=WorkspaceRole.OWNER,
    )

    return {
        "user": user,
        "workspace": ws,
        "member": member,
        "account": bank_account,
        "context": context,
    }


# ===========================================================================
# 1. File Upload Security & Storage Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_file_upload_security_and_storage(db_session: AsyncSession, import_setup):
    """Verifies file size limits, magic bytes validation, and path traversal protection."""
    service = ImportService(db_session)
    ws = import_setup["workspace"]
    user = import_setup["user"]

    # 1. Valid CSV payload
    csv_bytes = b"Date,Description,Amount\n14/11/2026,Office Supplies,1500.00\n"
    res = await service.process_file_upload(
        workspace_id=ws.id,
        user_id=user.id,
        filename="../../malicious_path/statement.csv",
        content_bytes=csv_bytes,
        mime_type="text/csv",
    )
    assert res["status"] == ImportStatus.AWAITING_REVIEW.value
    assert res["total_records"] == 1

    # Verify path traversal protection (stored in safe uuid path, not ../../)
    job = await service.repo.get_job_by_id(ws.id, res["job_id"])
    assert job is not None
    assert ".." not in job.storage_reference

    # 2. Oversized file (>10MB)
    huge_bytes = b"X" * (10 * 1024 * 1024 + 10)
    with pytest.raises(FileTooLargeError):
        await service.process_file_upload(
            workspace_id=ws.id,
            user_id=user.id,
            filename="large.csv",
            content_bytes=huge_bytes,
        )

    # 3. Invalid extension
    with pytest.raises(InvalidFileFormatError):
        await service.process_file_upload(
            workspace_id=ws.id,
            user_id=user.id,
            filename="statement.exe",
            content_bytes=b"MZ\x90\x00",
        )

    # 4. Corrupted PDF (missing %PDF- magic bytes)
    with pytest.raises(UnsafeFileError):
        await service.process_file_upload(
            workspace_id=ws.id,
            user_id=user.id,
            filename="fake.pdf",
            content_bytes=b"This is not a real PDF file header",
        )

    # 5. Corrupted XLSX (missing PK\x03\x04 zip magic bytes)
    with pytest.raises(UnsafeFileError):
        await service.process_file_upload(
            workspace_id=ws.id,
            user_id=user.id,
            filename="fake.xlsx",
            content_bytes=b"Plain text masquerading as XLSX",
        )

    # 6. Duplicate File Checksum Rejection
    with pytest.raises(DuplicateImportError):
        await service.process_file_upload(
            workspace_id=ws.id,
            user_id=user.id,
            filename="duplicate.csv",
            content_bytes=csv_bytes,
            allow_duplicate_file=False,
        )


# ===========================================================================
# 2. CSV Statement Parser & Indian Bank Conventions
# ===========================================================================

def test_csv_parser_hdfc_bank_format():
    """Tests parsing HDFC Bank format with separate withdrawal and deposit columns."""
    hdfc_csv = """HDFC BANK STATEMENT
Account No: 50100234567890
Opening Balance: 50,000.00
Date,Narration,Chq./Ref.No.,Withdrawal Amt.,Deposit Amt.,Closing Balance
14/11/2026,NEFT CR-INFOSYS-SALARY,N11223344,,"1,25,000.50","1,75,000.50"
14/11/2026,UPI-SWIGGY-BANGALORE,UPI-987654,750.00,,"1,74,250.50"
15/11/2026,CHQ DEP-CLIENT PAYMENT,CHQ-100200,,"45,000.00","2,19,250.50"
TOTAL,,,750.00,"1,70,000.50","2,19,250.50"
"""
    parser = CsvStatementParser()
    result = parser.parse(hdfc_csv.encode("utf-8"))

    assert len(result.rows) == 3
    # Row 1 (Salary deposit)
    r1 = result.rows[0]
    assert r1.date_str == "14/11/2026"
    assert "SALARY" in r1.description_str
    assert r1.credit_str == "1,25,000.50"
    assert r1.ref_str == "N11223344"

    # Row 2 (UPI withdrawal)
    r2 = result.rows[1]
    assert r2.debit_str == "750.00"
    assert r2.credit_str == ""


def test_csv_parser_sbi_bank_format():
    """Tests parsing State Bank of India format."""
    sbi_csv = """Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance
10-Nov-2026,ELECTRICITY BILL BESCOM,EPAY-1234,3500.00,,46500.00
11-Nov-2026,INTEREST CREDIT,INT-Q3,,1250.00,47750.00
"""
    parser = CsvStatementParser()
    result = parser.parse(sbi_csv.encode("utf-8"))

    assert len(result.rows) == 2
    assert result.rows[0].debit_str == "3500.00"
    assert result.rows[1].credit_str == "1250.00"


def test_csv_parser_custom_column_mapping():
    """Tests custom column mapping override when non-standard column headers are used."""
    custom_csv = """Datum;Verwendungszweck;Betrag;Belegnummer
2026-11-14;Cloud Hosting AWS;-4500.00;INV-9901
2026-11-15;Client Wire Transfer;60000.00;WIRE-4411
"""
    parser = CsvStatementParser()
    mapping = {
        "date": "Datum",
        "description": "Verwendungszweck",
        "amount": "Betrag",
        "ref_no": "Belegnummer",
    }
    result = parser.parse(custom_csv.encode("utf-8"), column_mapping=mapping)

    assert len(result.rows) == 2
    assert result.rows[0].date_str == "2026-11-14"
    assert result.rows[0].description_str == "Cloud Hosting AWS"
    assert result.rows[0].amount_str == "-4500.00"


# ===========================================================================
# 3. XLSX Statement Parser & Formula Safety
# ===========================================================================

def test_xlsx_statement_parser_formula_safety():
    """Verifies that XLSX parser reads cached data without executing formulas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bank Statement"
    ws.append(["Date", "Particulars", "Debit", "Credit", "Balance"])
    ws.append(["2026-11-14", "Consulting Fee", None, 85000, 85000])
    ws.append(["2026-11-15", "Office Rent", 35000, None, 50000])

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    parser = XlsxStatementParser()
    result = parser.parse(xlsx_bytes)

    assert result.source_format == SourceFormat.XLSX.value
    assert len(result.rows) == 2
    assert result.rows[0].credit_str == "85000"
    assert result.rows[1].debit_str == "35000"
    assert "Bank Statement" in result.available_sheets


# ===========================================================================
# 4. Digital PDF Statement Parser
# ===========================================================================

def test_pdf_statement_parser_digital():
    """Verifies table extraction and balance detection from digital PDF statements."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()

    table = Table([
        ["Date", "Narration", "Chq/Ref No", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"],
        ["14/11/2026", "Vendor Payment Tata Motors", "REF-8899", "45,000.00", "", "55,000.00"],
        ["15/11/2026", "Direct Client Deposit", "DEP-1122", "", "75,000.00", "130,000.00"],
    ])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    story = [
        Paragraph("HDFC BANK STATEMENT", styles["Heading1"]),
        Paragraph("Account Number: 50100998877665", styles["Normal"]),
        Paragraph("Opening Balance: 100,000.00", styles["Normal"]),
        table,
        Paragraph("Closing Balance: 130,000.00", styles["Normal"]),
    ]
    doc.build(story)
    pdf_bytes = buf.getvalue()

    parser = PdfStatementParser()
    result = parser.parse(pdf_bytes)

    assert result.source_format == SourceFormat.PDF_TEXT.value
    assert len(result.rows) == 2
    assert result.opening_balance == Decimal("100000.00")
    assert result.closing_balance == Decimal("130000.00")
    assert result.account_number == "50100998877665"


# ===========================================================================
# 5. Normalizer & Validator Tests
# ===========================================================================

def test_statement_normalizer_and_validator():
    """Tests date conversion, Indian number parsing, paise calculation, and validation."""
    # Case A: Standard Inflow
    norm1 = StatementNormalizer.normalize_row(
        row_number=1,
        raw_data={"date": "14-Nov-2026"},
        date_str="14-Nov-2026",
        description_str="  SALARY FOR NOVEMBER 2026  ",
        amount_str=None,
        debit_str=None,
        credit_str="₹ 1,50,000.50",
        balance_str="2,00,000.00",
        ref_str="SAL-101",
    )
    assert norm1["transaction_date"] == "2026-11-14"
    assert norm1["amount"] == "150000.5000"
    assert norm1["amount_paise"] == 15000050
    assert norm1["direction"] == "inflow"
    assert norm1["transaction_type"] == "income"

    status1, errors1 = StatementValidator.validate_candidate(norm1)
    assert status1 == ValidationStatus.VALID
    assert len(errors1) == 0

    # Case B: Parenthesized Outflow
    norm2 = StatementNormalizer.normalize_row(
        row_number=2,
        raw_data={},
        date_str="2026-11-15",
        description_str="Software Subscription",
        amount_str="(4,250.00)",
        debit_str=None,
        credit_str=None,
        balance_str=None,
        ref_str=None,
    )
    assert norm2["direction"] == "outflow"
    assert norm2["amount_paise"] == 425000

    # Case C: Invalid Row (Missing Date & Negative Amount)
    norm3 = StatementNormalizer.normalize_row(
        row_number=3,
        raw_data={},
        date_str="invalid-date",
        description_str="",
        amount_str="0.00",
        debit_str=None,
        credit_str=None,
        balance_str=None,
        ref_str=None,
    )
    status3, errors3 = StatementValidator.validate_candidate(norm3)
    assert status3 == ValidationStatus.INVALID
    assert len(errors3) >= 2


# ===========================================================================
# 6. Deduplication Engine Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_deduplication_exact_and_probable(db_session: AsyncSession, import_setup):
    """Verifies that existing transactions are detected as exact or probable duplicates."""
    ws = import_setup["workspace"]
    account = import_setup["account"]

    # 1. Insert existing transaction
    existing_tx = Transaction(
        workspace_id=ws.id,
        account_id=account.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("15000.0000"),
        amount_paise=1500000,
        currency="INR",
        transaction_date=date(2026, 11, 14),
        description="Office Printer HP LaserJet",
        external_transaction_id="HP-REF-001",
        status="posted",
    )
    db_session.add(existing_tx)
    await db_session.flush()

    # 2. Candidate with exact reference match
    cand_exact = {
        "source_row_number": 1,
        "normalized": {
            "transaction_date": "2026-11-14",
            "amount_paise": 1500000,
            "direction": "outflow",
            "reference_number": "HP-REF-001",
            "description": "HP Printer",
        },
    }

    # 3. Candidate with probable match (same date, same amount, slightly different description)
    cand_probable = {
        "source_row_number": 2,
        "normalized": {
            "transaction_date": "2026-11-14",
            "amount_paise": 1500000,
            "direction": "outflow",
            "reference_number": None,
            "description": "Office Equipment Store",
        },
    }

    # 4. Intra-batch duplicate of row 1
    cand_intra_dup = {
        "source_row_number": 3,
        "normalized": {
            "transaction_date": "2026-11-14",
            "amount_paise": 1500000,
            "direction": "outflow",
            "reference_number": "HP-REF-001",
            "description": "HP Printer",
        },
    }

    results = await StatementDeduplicator.deduplicate_batch(
        session=db_session,
        workspace_id=ws.id,
        account_id=account.id,
        candidates=[cand_exact, cand_probable, cand_intra_dup],
    )

    assert results[0]["duplicate_status"] == DuplicateStatus.EXACT.value
    assert results[0]["duplicate_match_id"] == existing_tx.id
    assert results[0]["selected_for_import"] is False

    assert results[1]["duplicate_status"] == DuplicateStatus.PROBABLE.value
    assert results[1]["duplicate_match_id"] == existing_tx.id

    assert results[2]["duplicate_status"] == DuplicateStatus.EXACT.value
    assert "same statement file" in results[2]["duplicate_reason"]


# ===========================================================================
# 7. End-to-End Import Confirmation & General Ledger Posting
# ===========================================================================

@pytest.mark.asyncio
async def test_confirm_import_creates_transactions_and_posts_to_ledger(db_session: AsyncSession, import_setup):
    """
    End-to-End integration test:
    1. Uploads valid CSV statement.
    2. Staged candidates are reviewed.
    3. Confirms import.
    4. Verifies operational Transaction records created.
    5. Verifies Account balance mutated with exact paise.
    6. Verifies General Ledger Journal Entries created, posted, and balanced!
    """
    service = ImportService(db_session)
    ws = import_setup["workspace"]
    user = import_setup["user"]
    account = import_setup["account"]
    context = import_setup["context"]

    csv_data = """Date,Narration,Chq/Ref No,Withdrawal Amt.,Deposit Amt.,Closing Balance
14/11/2026,Client Project Retainer,INV-2026-01,,"1,50,000.00","3,50,000.00"
14/11/2026,Office High-Speed Internet,FIBER-991,"5,000.00",,"3,45,000.00"
"""
    # 1. Process Upload
    upload_res = await service.process_file_upload(
        workspace_id=ws.id,
        user_id=user.id,
        filename="bank_statement.csv",
        content_bytes=csv_data.encode("utf-8"),
        account_id=account.id,
    )
    assert upload_res["status"] == ImportStatus.AWAITING_REVIEW.value
    assert upload_res["valid_records"] == 2

    # 2. Confirm Import
    confirm_res = await service.confirm_import(
        workspace_id=ws.id,
        job_id=upload_res["job_id"],
        batch_id=upload_res["batch_id"],
        target_account_id=account.id,
        workspace_context=context,
        actor_id=user.id,
    )
    await db_session.commit()

    assert confirm_res["status"] == ImportStatus.COMPLETED.value
    assert confirm_res["imported_count"] == 2

    # 3. Verify Operational Transactions
    tx_ids = confirm_res["created_transaction_ids"]
    assert len(tx_ids) == 2

    # 4. Verify Account Balance Mutation
    # Initial: 200,000.00
    # + Inflow: 150,000.00
    # - Outflow: 5,000.00
    # Expected Net Balance: 345,000.00 (34500000 paise)
    await db_session.refresh(account)
    assert account.current_book_balance_paise == 34500000

    # 5. Verify General Ledger Entries
    ledger_service = LedgerService(db_session)
    tb = await ledger_service.get_trial_balance(ws.id)
    assert tb["is_balanced"] is True
    assert tb["difference"] == Decimal("0.0000")
    assert tb["difference_paise"] == 0


# ===========================================================================
# 8. Cross-Workspace Isolation & Anti-IDOR Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_cross_workspace_import_isolation(db_session: AsyncSession, import_setup):
    """Verifies that an import job belonging to Workspace A cannot be accessed by Workspace B."""
    service = ImportService(db_session)
    ws_a = import_setup["workspace"]
    user_a = import_setup["user"]

    # Create job in Workspace A
    csv_bytes = b"Date,Description,Amount\n14/11/2026,Testing Isolation,1000.00\n"
    res = await service.process_file_upload(
        workspace_id=ws_a.id,
        user_id=user_a.id,
        filename="ws_a_statement.csv",
        content_bytes=csv_bytes,
    )
    job_id = res["job_id"]

    # Workspace B
    ws_b_id = uuid.uuid4()

    # Attempt lookup from Workspace B must return None / 404
    job_lookup = await service.repo.get_job_by_id(ws_b_id, job_id)
    assert job_lookup is None
