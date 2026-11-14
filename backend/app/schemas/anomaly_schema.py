"""
Arthsavora Financial Anomaly Detection & Risk Intelligence Pydantic Schemas
Strict typed request/response contracts with exact monetary precision.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AnomalyTransactionSummary(BaseModel):
    id: uuid.UUID
    transaction_date: date
    amount_paise: int
    amount: Decimal
    currency: str
    direction: str
    description: str
    merchant_name: Optional[str] = None
    category_name: Optional[str] = None
    account_name: Optional[str] = None


class AnomalyReviewResponse(BaseModel):
    id: uuid.UUID
    anomaly_id: uuid.UUID
    workspace_id: uuid.UUID
    reviewer_id: Optional[uuid.UUID] = None
    action: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyDetectionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    transaction_id: Optional[uuid.UUID] = None
    account_id: Optional[uuid.UUID] = None
    detection_type: str
    detection_method: str
    severity: str
    risk_score: int
    status: str
    explanation: str
    evidence_metadata: Dict[str, Any] = Field(default_factory=dict)
    rule_code: Optional[str] = None
    model_version: str = "v1.0.0"
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None

    transaction: Optional[AnomalyTransactionSummary] = None
    reviews: List[AnomalyReviewResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AnomalyReviewRequest(BaseModel):
    action: str = Field(..., description="acknowledge, mark_expected, mark_suspicious, dismiss, escalate, create_exception")
    reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=2000)
    create_exception: bool = Field(default=False, description="Whether to also whitelist this entity as an exception")
    exception_expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class DetectionRuleResponse(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    rule_code: str
    name: str
    description: str
    detection_category: str
    severity: str
    threshold_config: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True
    version: str = "1.0.0"

    model_config = ConfigDict(from_attributes=True)


class DetectionRuleUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    severity: Optional[str] = None
    threshold_config: Optional[Dict[str, Any]] = None


class DetectionExceptionCreateRequest(BaseModel):
    rule_code: Optional[str] = None
    merchant_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    account_id: Optional[uuid.UUID] = None
    merchant_name_pattern: Optional[str] = None
    max_amount_paise: Optional[int] = Field(None, ge=0)
    reason: str = Field(..., min_length=3, max_length=500)
    expires_at: Optional[date] = None


class DetectionExceptionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    rule_code: Optional[str] = None
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    account_id: Optional[uuid.UUID] = None
    account_name: Optional[str] = None
    merchant_name_pattern: Optional[str] = None
    max_amount_paise: Optional[int] = None
    max_amount: Optional[Decimal] = None
    reason: str
    expires_at: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalySummaryResponse(BaseModel):
    total_detections: int
    open_anomalies: int
    high_severity_anomalies: int
    resolved_anomalies: int
    average_risk_score: float


class AnomalyTrendPoint(BaseModel):
    date: str
    informational: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    total: int = 0


class AnomalyTrendsResponse(BaseModel):
    workspace_id: uuid.UUID
    lookback_days: int
    trends: List[AnomalyTrendPoint]


class AnomalyScanRequest(BaseModel):
    lookback_days: int = Field(default=7, ge=1, le=90)
    force_recheck: bool = Field(default=False, description="Re-evaluates previously evaluated transactions")
