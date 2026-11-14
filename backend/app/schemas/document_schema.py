"""
Arthsavora Document Intelligence and Receipt Schemas
Pydantic v2 data transfer models for document uploads, OCR extraction responses,
entity field corrections, transaction confirmations, and candidate matches.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DocumentLineItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    description: str = Field(..., description="Item or service description")
    hsn_sac: Optional[str] = Field(None, description="Harmonized System Nomenclature or SAC code")
    quantity: str = Field("1.0000", description="Quantity purchased")
    unit_price: str = Field("0.0000", description="Unit price before tax")
    unit_price_paise: int = Field(0, description="Unit price in paise")
    tax_rate: Optional[str] = Field(None, description="Applicable tax percentage")
    amount: str = Field("0.0000", description="Line total amount")
    amount_paise: int = Field(0, description="Line total amount in paise")


class TaxBreakdownSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cgst: str = Field("0.0000", description="Central GST amount")
    cgst_paise: int = Field(0, description="Central GST in paise")
    sgst: str = Field("0.0000", description="State GST amount")
    sgst_paise: int = Field(0, description="State GST in paise")
    igst: str = Field("0.0000", description="Integrated GST amount")
    igst_paise: int = Field(0, description="Integrated GST in paise")
    total_tax: str = Field("0.0000", description="Combined tax sum")
    total_tax_paise: int = Field(0, description="Combined tax sum in paise")
    gstin: Optional[str] = Field(None, description="15-character Indian GST identification number")


class StructuredReceiptDataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_name: Optional[str] = Field(None, description="Identified merchant or counterparty")
    gstin: Optional[str] = Field(None, description="GSTIN on document")
    receipt_date: Optional[str] = Field(None, description="Transaction date (ISO format)")
    invoice_number: Optional[str] = Field(None, description="Invoice, bill, or cash memo identifier")
    currency: str = Field("INR", description="Three-letter ISO currency code")
    subtotal: str = Field("0.0000", description="Subtotal amount")
    subtotal_paise: int = Field(0, description="Subtotal in paise")
    taxes: TaxBreakdownSchema = Field(default_factory=TaxBreakdownSchema, description="Tax breakdown components")
    discount: str = Field("0.0000", description="Discount deducted")
    discount_paise: int = Field(0, description="Discount in paise")
    total_amount: str = Field("0.0000", description="Total payable amount")
    total_amount_paise: int = Field(0, description="Total amount in paise")
    payment_method: str = Field("unknown", description="Identified payment method (upi, card, cash, netbanking)")
    payment_reference: Optional[str] = Field(None, description="UTR, UPI RRN, or card reference")
    suggested_category_id: Optional[str] = Field(None, description="Suggested category UUID")
    suggested_category_name: Optional[str] = Field(None, description="Suggested category display name")
    line_items: List[DocumentLineItemSchema] = Field(default_factory=list, description="Itemized product/service rows")


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    ocr_provider: str
    ocr_version: Optional[str] = None
    raw_text: str
    structured_data: Dict[str, Any]
    field_confidences: Dict[str, float]
    overall_confidence: Decimal
    validation_status: str
    validation_warnings: List[str]
    created_at: datetime


class DocumentReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    reviewer_id: Optional[uuid.UUID] = None
    original_data: Dict[str, Any]
    corrected_data: Dict[str, Any]
    review_action: str
    notes: Optional[str] = None
    created_at: datetime


class DocumentTransactionAssociationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    transaction_id: uuid.UUID
    workspace_id: uuid.UUID
    association_type: str
    match_score: Optional[Decimal] = None
    match_evidence: Dict[str, Any]
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime


class FinancialDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    uploaded_by_id: Optional[uuid.UUID] = None
    original_filename: str
    file_size: int
    mime_type: str
    file_checksum: str
    document_type: str
    status: str
    preprocessing_metadata: Dict[str, Any]
    retention_metadata: Dict[str, Any]
    extractions: List[DocumentExtractionResponse] = Field(default_factory=list)
    reviews: List[DocumentReviewResponse] = Field(default_factory=list)
    transaction_associations: List[DocumentTransactionAssociationResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[FinancialDocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentCorrectionRequest(BaseModel):
    corrected_data: Dict[str, Any] = Field(..., description="Corrected structured receipt entity values")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional reviewer audit notes")


class DocumentConfirmRequest(BaseModel):
    account_id: uuid.UUID = Field(..., description="Target financial account to debit")
    confirmed_data: Optional[Dict[str, Any]] = Field(None, description="Optional overrides to lock into transaction")
    notes: Optional[str] = Field(None, max_length=1000, description="Audit notes for ledger recording")


class DocumentMatchAssociateRequest(BaseModel):
    transaction_id: uuid.UUID = Field(..., description="Target existing transaction to link with receipt")
    match_score: Optional[Decimal] = Field(None, description="Match confidence score")
    notes: Optional[str] = Field(None, max_length=1000, description="Linking notes")


class TransactionMatchCandidateResponse(BaseModel):
    transaction_id: uuid.UUID
    match_status: str
    match_score: Decimal
    evidence: Dict[str, Any]
    transaction_summary: Dict[str, Any]
