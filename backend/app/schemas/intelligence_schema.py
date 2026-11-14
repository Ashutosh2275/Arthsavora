"""
Arthsavora Transaction Intelligence, Category & Merchant Schemas
Pydantic contracts for categories, rules, classifications, predictions, and user feedback.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# Category Schemas
# ===========================================================================

class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Category name")
    category_type: str = Field(..., description="income, expense, transfer, or system")
    parent_id: Optional[uuid.UUID] = Field(None, description="Parent category UUID for hierarchical grouping")
    slug: Optional[str] = Field(None, description="Optional custom URL slug")
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    workspace_type: str = Field("all", description="personal, family, business, or all")
    display_order: int = Field(0)


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    parent_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    workspace_type: Optional[str] = None
    display_order: Optional[int] = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    name: str
    slug: str
    category_type: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_system: bool
    status: str
    workspace_type: str
    display_order: int
    created_at: datetime
    updated_at: datetime


class CategoryTreeResponse(CategoryResponse):
    children: List["CategoryTreeResponse"] = []


# ===========================================================================
# Merchant Schemas
# ===========================================================================

class MerchantAliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alias: str
    normalized_alias: str
    match_type: str
    confidence: float


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    canonical_name: str
    slug: str
    default_category_id: Optional[uuid.UUID] = None
    merchant_type: str
    website: Optional[str] = None
    logo_url: Optional[str] = None
    is_verified: bool
    status: str
    aliases: List[MerchantAliasResponse] = []


# ===========================================================================
# Classification Rule Schemas
# ===========================================================================

class RuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    conditions: Dict[str, Any] = Field(..., description="Condition dictionary: merchant_pattern, description_contains, direction, etc.")
    suggested_category_id: uuid.UUID
    suggested_merchant_id: Optional[uuid.UUID] = None
    priority: int = Field(100, description="Higher number = higher precedence")
    is_enabled: bool = True
    rule_scope: str = "workspace"


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    suggested_category_id: Optional[uuid.UUID] = None
    suggested_merchant_id: Optional[uuid.UUID] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    name: str
    priority: int
    is_enabled: bool
    rule_scope: str
    conditions: Dict[str, Any]
    suggested_category_id: uuid.UUID
    suggested_category_name: Optional[str] = None
    suggested_merchant_id: Optional[uuid.UUID] = None
    suggested_merchant_name: Optional[str] = None
    created_at: datetime


# ===========================================================================
# Classification & Intelligence Schemas
# ===========================================================================

class ClassificationResponse(BaseModel):
    classification_id: str
    workspace_id: str
    transaction_id: str
    original_description: str
    normalized_description: Optional[str] = None
    merchant_name: Optional[str] = None
    suggested_category_id: str
    suggested_category_name: str
    confidence_score: float
    confidence_band: str
    method: str
    model_version: str
    explanation: str
    status: str
    created_at: Optional[str] = None


class BatchCategorizeRequest(BaseModel):
    transaction_ids: List[uuid.UUID]
    force_reclassify: bool = False


class BatchCategorizeResponse(BaseModel):
    total_requested: int
    categorized_count: int
    results: List[ClassificationResponse]


class PreviewSuggestRequest(BaseModel):
    description: str
    direction: str = "outflow"
    amount_paise: Optional[int] = None


class PreviewSuggestResponse(BaseModel):
    normalized_description: str
    merchant_candidate: Optional[str] = None
    payment_channel: str
    suggested_category_id: Optional[str] = None
    suggested_category_name: str
    confidence_score: float
    confidence_band: str
    method: str
    explanation: str


# ===========================================================================
# Feedback Schemas
# ===========================================================================

class FeedbackSubmitRequest(BaseModel):
    action: str = Field(..., description="accept, correct_category, correct_merchant, mark_unknown, or create_rule")
    confirmed_category_id: Optional[uuid.UUID] = None
    confirmed_merchant_name: Optional[str] = None
    feedback_reason: Optional[str] = None
    create_rule: bool = False
    rule_name: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    workspace_id: str
    transaction_id: str
    action: str
    confirmed_category_id: Optional[str] = None
    confirmed_merchant_name: Optional[str] = None
    created_rule_id: Optional[str] = None
    status: str
