"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


VALID_SOURCES = {"weather", "news"}


class JobCreate(BaseModel):
    """Schema for creating a new aggregation job."""

    sources: List[str] = Field(..., min_length=1, description="Data sources to aggregate")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters for each source")


class JobResponse(BaseModel):
    """Full job response schema."""

    id: str
    status: str
    sources: List[str]
    parameters: dict[str, Any]
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    """Lightweight job status response for polling."""

    id: str
    status: str
    result_url: Optional[str] = None
    error_message: Optional[str] = None
