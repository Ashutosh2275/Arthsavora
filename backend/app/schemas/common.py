"""
Arthsavora Common API Schemas
Standardized request, response, error, and pagination models.
"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Specific field or parameter validation error detail."""
    loc: List[str | int] = Field(default_factory=list, description="Location of the error in the request")
    msg: str = Field(..., description="Human-readable error explanation")
    type: str = Field(..., description="Error classification type")


class ErrorPayload(BaseModel):
    """Standardized error envelope payload."""
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable summary of the error")
    request_id: Optional[str] = Field(None, description="Correlation tracking identifier")
    details: List[Any] = Field(default_factory=list, description="List of granular error details")


class ErrorResponse(BaseModel):
    """Root error container returned across all HTTP exception responses."""
    error: ErrorPayload


class PaginationParams(BaseModel):
    """Standard pagination query parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated collection envelope."""
    items: List[T] = Field(..., description="Page items")
    total: int = Field(..., ge=0, description="Total matching items across all pages")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    """Standard success wrapper envelope for single entities or actions."""
    status: str = Field("success", description="Response status (success)")
    data: T = Field(..., description="Payload data")
    message: Optional[str] = Field(None, description="Optional informational message")

    model_config = ConfigDict(from_attributes=True)
