"""
Pydantic v2 schemas for Human-in-the-loop review operations.
"""

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ReviewFieldResponse(BaseModel):
    """Details of an extracted field under review."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_id: uuid.UUID
    field_name: str
    raw_value: str | None = None
    normalized_value: str | None = None
    page_number: int
    bounding_box: dict[str, Any] | None = None
    confidence: float
    review_status: str
    corrected_value: str | None = None
    corrected_by: uuid.UUID | None = None
    corrected_at: datetime | None = None
    correction_note: str | None = None
    created_at: datetime


class CorrectFieldRequest(BaseModel):
    """Payload to correct an extracted field's value."""
    corrected_value: str = Field(..., min_length=1, max_length=1000, description="Valor corregido por el revisor")
    note: str | None = Field(None, max_length=500, description="Nota o justificación de la corrección")


class RejectFieldRequest(BaseModel):
    """Payload to reject an extracted field."""
    reason: str | None = Field(None, max_length=500, description="Motivo del rechazo del campo")


class BatchReviewRequest(BaseModel):
    """Payload to batch accept or reject extracted fields."""
    field_ids: list[uuid.UUID] = Field(..., min_length=1, description="Lista de IDs de campos a actualizar")
    action: str = Field(..., pattern="^(ACCEPT|REJECT)$", description="Acción a aplicar: ACCEPT o REJECT")


class ReviewSummaryResponse(BaseModel):
    """Statistical summary of document field review progress."""
    document_id: uuid.UUID
    total_fields: int
    pending_count: int
    accepted_count: int
    corrected_count: int
    rejected_count: int
    completion_pct: float
    is_complete: bool


class FinalizeReviewResponse(BaseModel):
    """Response returned when document review is marked complete."""
    message: str
    document_id: uuid.UUID
    status: str
    finalized_at: datetime
