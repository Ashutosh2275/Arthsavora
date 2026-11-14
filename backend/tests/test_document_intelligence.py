"""
Arthsavora Document Intelligence & Receipt Processing Comprehensive Test Suite
Verifies magic byte validation, image preprocessing, multi-provider OCR abstractions,
India-first entity parsing, GSTIN verification, mathematical reconciliation,
merchant enrichment, transaction matching, explicit user confirmation, and tenant isolation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import io
import os
import uuid
import pytest
from PIL import Image
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleViolationException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import WorkspaceContext
from app.domain.document import (
    DocumentLineItemVO,
    DocumentStatus,
    StructuredReceiptDataVO,
    TaxBreakdownVO,
    TransactionMatchStatus,
    ValidationStatus,
    is_valid_gstin,
    parse_indian_date,
    parse_monetary_amount,
    validate_receipt_math,
)
from app.infrastructure.database.models import (
    Account,
    Category,
    Transaction,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.infrastructure.database.models.document import (
    DocumentExtractionResult,
    DocumentReviewRecord,
    DocumentTransactionAssociation,
    FinancialDocument,
)
from app.services.document.document_service import DocumentService, MAX_DOCUMENT_SIZE_BYTES
from app.services.document.enrichment import DocumentEnricher
from app.services.document.field_extractor import ReceiptFieldExtractor
from app.services.document.matcher import TransactionMatcher
from app.services.document.ocr.mock_ocr import MockDeterministicOCREngine, SAMPLE_INDIAN_RECEIPTS
from app.services.document.preprocessor import ImagePreprocessor


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def create_dummy_png_bytes() -> bytes:
    """Generates valid in-memory PNG bytes with magic bytes \x89PNG\r\n\x1a\n."""
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_dummy_jpeg_bytes() -> bytes:
    """Generates valid in-memory JPEG bytes with magic bytes \xFF\xD8\xFF."""
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_dummy_pdf_bytes() -> bytes:
    """Generates minimal PDF header bytes."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


# ---------------------------------------------------------------------------
# 1. Validation & Magic Bytes Tests
# ---------------------------------------------------------------------------

def test_magic_bytes_detection_and_file_validation():
    # Valid formats
    png_bytes = create_dummy_png_bytes()
    assert DocumentService.validate_file_bytes(png_bytes, "test.png") == "image/png"

    jpeg_bytes = create_dummy_jpeg_bytes()
    assert DocumentService.validate_file_bytes(jpeg_bytes, "test.jpg") == "image/jpeg"

    pdf_bytes = create_dummy_pdf_bytes()
    assert DocumentService.validate_file_bytes(pdf_bytes, "test.pdf") == "application/pdf"

    # Empty file
    with pytest.raises(ValidationException) as exc:
        DocumentService.validate_file_bytes(b"", "empty.png")
    assert exc.value.code == "FILE_EMPTY"

    # Unsupported format / spoofed extension
    with pytest.raises(ValidationException) as exc:
        DocumentService.validate_file_bytes(b"HELLO_WORLD_TEXT_FILE", "fake.png")
    assert exc.value.code == "UNSUPPORTED_DOCUMENT_FORMAT"

    # Oversized file
    oversized = b"%PDF-" + b"0" * (MAX_DOCUMENT_SIZE_BYTES + 10)
    with pytest.raises(ValidationException) as exc:
        DocumentService.validate_file_bytes(oversized, "huge.pdf")
    assert exc.value.code == "FILE_TOO_LARGE"


# ---------------------------------------------------------------------------
# 2. Image Preprocessing Tests
# ---------------------------------------------------------------------------

def test_image_preprocessing_pipeline(tmp_path):
    raw_path = tmp_path / "original_receipt.png"
    img = Image.new("RGB", (200, 400), color=(240, 240, 240))
    img.save(raw_path, format="PNG")

    out_path, meta = ImagePreprocessor.preprocess_image(str(raw_path))

    assert os.path.exists(out_path)
    assert os.path.exists(raw_path)  # Raw file preserved
    assert meta["original_dimensions"] == [200, 400]
    assert "grayscale_conversion" in meta["operations_applied"]
    assert any("contrast_boost" in op for op in meta["operations_applied"])


# ---------------------------------------------------------------------------
# 3. India-first Entity Extraction & Math Validation
# ---------------------------------------------------------------------------

def test_indian_gstin_validation():
    assert is_valid_gstin("29AABCB2212M1Z2") is True
    assert is_valid_gstin("27AABCR4587R1ZM") is True
    assert is_valid_gstin("07AAACH1118B1ZE") is True
    assert is_valid_gstin("07AAFCB9481E1ZR") is True

    # Invalid GSTINs
    assert is_valid_gstin("INVALID_GSTIN") is False
    assert is_valid_gstin("29AABCB2212M1Z") is False  # 14 chars
    assert is_valid_gstin(None) is False
    assert is_valid_gstin("") is False


def test_indian_date_parsing():
    assert parse_indian_date("12/10/2026") == date(2026, 10, 12)
    assert parse_indian_date("15-11-2026") == date(2026, 11, 15)
    assert parse_indian_date("2026-11-10") == date(2026, 11, 10)
    assert parse_indian_date("25/11/26") == date(2026, 11, 25)
    assert parse_indian_date("invalid-date") is None


def test_indian_monetary_amount_parsing():
    # Comma notations & symbols
    dec, paise = parse_monetary_amount("₹ 1,50,000.50")
    assert dec == Decimal("150000.5000")
    assert paise == 15000050

    dec, paise = parse_monetary_amount("Rs. 567.50/-")
    assert dec == Decimal("567.5000")
    assert paise == 56750

    dec, paise = parse_monetary_amount("1476.00")
    assert dec == Decimal("1476.0000")
    assert paise == 147600


def test_receipt_field_extractor_swiggy():
    raw_text = SAMPLE_INDIAN_RECEIPTS["swiggy"]
    (
        receipt,
        field_confs,
        overall_conf,
        val_status,
        val_warnings,
    ) = ReceiptFieldExtractor.extract_structured_data(raw_text)

    assert receipt.merchant_name == "SWIGGY ORDER INVOICE" or "Swiggy" in str(receipt.merchant_name)
    assert receipt.gstin == "29AABCB2212M1Z2"
    assert receipt.invoice_number == "SWG-BLR-2026-9812"
    assert receipt.receipt_date == "2026-10-12"
    assert receipt.total_amount_paise == 56750
    assert receipt.subtotal_paise == 55000
    assert receipt.taxes.cgst_paise == 1375
    assert receipt.taxes.sgst_paise == 1375
    assert receipt.payment_method == "upi"
    assert receipt.payment_reference == "628491028472"
    assert len(receipt.line_items) >= 2
    assert overall_conf >= Decimal("0.85")


def test_receipt_field_extractor_reliance():
    raw_text = SAMPLE_INDIAN_RECEIPTS["reliance"]
    (
        receipt,
        field_confs,
        overall_conf,
        val_status,
        val_warnings,
    ) = ReceiptFieldExtractor.extract_structured_data(raw_text)

    assert "RELIANCE" in (receipt.merchant_name or "").upper()
    assert receipt.gstin == "27AABCR4587R1ZM"
    assert receipt.receipt_date == "2026-11-15"
    assert receipt.total_amount_paise == 58064
    assert receipt.subtotal_paise == 55300
    assert receipt.payment_method == "card"


def test_mathematical_validation():
    # 1. Perfectly reconciled math
    status, warnings = validate_receipt_math(
        subtotal_paise=50000,
        total_tax_paise=5000,
        discount_paise=2000,
        total_amount_paise=53000,
        line_items=[],
    )
    assert status == ValidationStatus.VALID
    assert len(warnings) == 0

    # 2. Arithmetic discrepancy (> 100 paise / ₹1)
    status, warnings = validate_receipt_math(
        subtotal_paise=50000,
        total_tax_paise=5000,
        discount_paise=0,
        total_amount_paise=60000,  # 5000 paise mismatch
        line_items=[],
    )
    assert status == ValidationStatus.INVALID_MATH
    assert any("Arithmetic mismatch" in w for w in warnings)

    # 3. Missing total
    status, warnings = validate_receipt_math(
        subtotal_paise=0,
        total_tax_paise=0,
        discount_paise=0,
        total_amount_paise=0,
        line_items=[],
    )
    assert status == ValidationStatus.INCOMPLETE


# ---------------------------------------------------------------------------
# 4. Transaction Matcher Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transaction_matcher(db_session: AsyncSession, registered_user: dict):
    ws = registered_user["workspace"]
    user = registered_user["user"]

    # Create account
    account = Account(
        workspace_id=ws.id,
        name="HDFC Test Current",
        account_type="checking",
        currency="INR",
        current_book_balance_paise=10000000,
        available_balance_paise=10000000,
        status="active",
    )
    db_session.add(account)
    await db_session.flush()

    # Create matching transaction
    tx = Transaction(
        workspace_id=ws.id,
        account_id=account.id,
        transaction_type="expense",
        direction="outflow",
        amount=Decimal("567.5000"),
        amount_paise=56750,
        currency="INR",
        transaction_date=date(2026, 10, 12),
        description="Swiggy Delivery Dinner",
        status="posted",
        created_by_id=user.id,
    )
    db_session.add(tx)
    await db_session.commit()

    matcher = TransactionMatcher(db_session)
    receipt_vo = StructuredReceiptDataVO(
        merchant_name="Swiggy",
        receipt_date="2026-10-12",
        total_amount=Decimal("567.5000"),
        total_amount_paise=56750,
    )

    candidates = await matcher.find_matches(ws.id, receipt_vo)
    assert len(candidates) >= 1
    top = candidates[0]
    assert top.transaction_id == tx.id
    assert top.match_status in (TransactionMatchStatus.EXACT, TransactionMatchStatus.CANDIDATE)
    assert top.match_score >= Decimal("0.85")


# ---------------------------------------------------------------------------
# 5. Full Document Lifecycle & Confirmation Gate Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_upload_process_and_confirm_lifecycle(
    db_session: AsyncSession,
    registered_user: dict,
):
    ws = registered_user["workspace"]
    user = registered_user["user"]
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
        status="active",
    )
    ws_context = WorkspaceContext(
        workspace=ws,
        membership=member,
        current_user=user,
        role=WorkspaceRole.OWNER,
    )

    # Create account
    account = Account(
        workspace_id=ws.id,
        name="Axis Savings Bank",
        account_type="savings",
        currency="INR",
        current_book_balance_paise=10000000,
        available_balance_paise=10000000,
        status="active",
    )
    db_session.add(account)
    await db_session.commit()

    service = DocumentService(db_session)

    # 1. Upload Document with auto-processing via Mock Engine
    png_bytes = create_dummy_png_bytes()
    doc = await service.upload_document(
        workspace_context=ws_context,
        file_bytes=png_bytes,
        original_filename="swiggy_receipt.png",
        document_type="receipt",
        auto_process=True,
        ocr_provider="mock",
    )

    assert doc.id is not None
    assert doc.status in (DocumentStatus.EXTRACTED.value, DocumentStatus.REVIEW_REQUIRED.value)
    assert len(doc.extractions) > 0

    latest_ext = doc.extractions[0]
    assert latest_ext.structured_data["total_amount_paise"] == 56750
    assert latest_ext.ocr_provider == "mock_deterministic"

    # 2. User Field Corrections
    updated_doc = await service.correct_extraction(
        workspace_context=ws_context,
        document_id=doc.id,
        corrected_data={
            "merchant_name": "Swiggy Bangalore Central",
            "total_amount": "567.50",
        },
        notes="Corrected merchant branch location.",
    )
    assert updated_doc.extractions[0].structured_data["merchant_name"] == "Swiggy Bangalore Central"

    # 3. Explicit User Confirmation Gate -> Creates Financial Transaction
    initial_balance = account.current_book_balance_paise
    tx, assoc = await service.confirm_and_create_transaction(
        workspace_context=ws_context,
        document_id=doc.id,
        account_id=account.id,
        notes="Approved dinner expense.",
    )

    assert tx.id is not None
    assert tx.amount_paise == 56750
    assert tx.source_type == "ocr"
    assert assoc.document_id == doc.id
    assert assoc.transaction_id == tx.id

    # Verify account balance was deducted
    await db_session.refresh(account)
    assert account.current_book_balance_paise == initial_balance - 56750

    # Verify document is confirmed
    await db_session.refresh(doc)
    assert doc.status == DocumentStatus.CONFIRMED.value

    # 4. Attempting to re-confirm raises BusinessRuleViolationException
    with pytest.raises(BusinessRuleViolationException):
        await service.confirm_and_create_transaction(
            workspace_context=ws_context,
            document_id=doc.id,
            account_id=account.id,
        )


# ---------------------------------------------------------------------------
# 6. Tenant Isolation & Anti-IDOR Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_isolation_anti_idor(
    db_session: AsyncSession,
    registered_user: dict,
):
    ws_a = registered_user["workspace"]
    user_a = registered_user["user"]
    member_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="owner", status="active")
    ctx_a = WorkspaceContext(workspace=ws_a, membership=member_a, current_user=user_a, role=WorkspaceRole.OWNER)

    # Workspace B
    user_b_id = uuid.uuid4()
    user_b = User(
        id=user_b_id,
        email=f"user_b_{user_b_id.hex[:6]}@example.com",
        full_name="User B",
        hashed_password="hashed_pw_test",
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.flush()

    ws_b = Workspace(
        name="Workspace B",
        slug=f"ws-b-{user_b_id.hex[:8]}",
        type="personal",
        owner_id=user_b_id,
        status="active",
    )
    db_session.add(ws_b)
    await db_session.commit()
    member_b = WorkspaceMember(workspace_id=ws_b.id, user_id=user_a.id, role="owner", status="active")
    ctx_b = WorkspaceContext(workspace=ws_b, membership=member_b, current_user=user_a, role=WorkspaceRole.OWNER)

    service = DocumentService(db_session)

    # Upload document to Workspace A
    doc = await service.upload_document(
        workspace_context=ctx_a,
        file_bytes=create_dummy_png_bytes(),
        original_filename="secret_invoice.png",
        auto_process=False,
    )

    # User in Workspace B attempting to access document in Workspace A
    scoped_res = await service.repo.get_by_id_scoped(doc.id, ws_b.id)
    assert scoped_res is None

    with pytest.raises(NotFoundException):
        await service.get_document_file_path(ctx_b, doc.id)


# ---------------------------------------------------------------------------
# 7. REST API Endpoints Integration Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_document_endpoints(client: AsyncClient, registered_user: dict):
    headers = registered_user["headers"]
    ws_id = str(registered_user["workspace"].id)
    headers["X-Workspace-ID"] = ws_id

    # 1. Upload via multipart/form-data
    png_bytes = create_dummy_png_bytes()
    files = {"file": ("swiggy_dinner.png", png_bytes, "image/png")}
    data = {"document_type": "receipt", "auto_process": "true", "ocr_provider": "mock"}

    resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_data = resp.json()
    doc_id = doc_data["id"]
    assert doc_data["original_filename"] == "swiggy_dinner.png"
    assert len(doc_data["extractions"]) > 0

    # 2. List documents
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/documents", headers=headers)
    assert resp.status_code == 200
    list_data = resp.json()
    assert list_data["total"] >= 1
    assert any(d["id"] == doc_id for d in list_data["items"])

    # 3. Get single document details
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id

    # 4. Patch extraction corrections
    patch_payload = {
        "corrected_data": {
            "merchant_name": "Swiggy Koramangala",
            "total_amount": "567.50",
        },
        "notes": "Verified by user via API",
    }
    resp = await client.patch(
        f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/extraction",
        json=patch_payload,
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["extractions"][0]["structured_data"]["merchant_name"] == "Swiggy Koramangala"

    # 5. Find matches
    resp = await client.post(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/match", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 6. Stream/Download document preview
    resp = await client.get(
        f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/download?preview=true",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"

    # 7. Delete document
    resp = await client.delete(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}", headers=headers)
    assert resp.status_code == 204
