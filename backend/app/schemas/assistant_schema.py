"""
Arthsavora AI Financial Assistant Pydantic Schemas
Strict request/response validation DTOs for conversation threads, messages,
action draft confirmations, and operational usage telemetry.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Conversation Schemas
# -----------------------------------------------------------------------------

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Optional title for new conversation")


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(active|archived|deleted)$")


class ConversationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    status: str
    model_provider: str
    model_name: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


# -----------------------------------------------------------------------------
# Action Draft Schemas
# -----------------------------------------------------------------------------

class ActionDraftResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    workspace_id: uuid.UUID
    action_type: str
    action_summary: str
    parameters: Dict[str, Any]
    status: str
    confirmation_token: str
    expires_at: datetime
    created_at: datetime


class ActionConfirmRequest(BaseModel):
    confirmation_token: str = Field(..., description="Unique confirmation token from draft proposal")


class ActionConfirmResponse(BaseModel):
    action_id: uuid.UUID
    status: str
    action_type: str
    message: str
    execution_result: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Message Schemas
# -----------------------------------------------------------------------------

class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000, description="User financial question or instruction")


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str
    content: str
    intent: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    action_draft: Optional[ActionDraftResponse] = None
    tokens_prompt: int = 0
    tokens_completion: int = 0
    latency_ms: int = 0
    created_at: datetime


# -----------------------------------------------------------------------------
# Usage & Cost Schemas
# -----------------------------------------------------------------------------

class AssistantUsageResponse(BaseModel):
    total_requests: int
    total_tokens: int
    tokens_prompt: int
    tokens_completion: int
    estimated_cost_usd: float
    avg_latency_ms: int
