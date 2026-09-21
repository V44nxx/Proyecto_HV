"""
Pydantic v2 schemas for Executive & Operational Dashboard.
"""

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DashboardKpiResponse(BaseModel):
    """Core executive and operational metrics."""
    total_documents: int
    total_persons: int
    total_professionals: int
    processed_documents: int
    documents_requiring_review: int
    extraction_success_rate: float


class DistributionItem(BaseModel):
    """Single category, profession, or level distribution item."""
    label: str
    count: int
    percentage: float


class DashboardDistributionsResponse(BaseModel):
    """Aggregated distributions across multiple analytical dimensions."""
    by_format: list[DistributionItem]
    by_category: list[DistributionItem]
    top_professions: list[DistributionItem]
    by_academic_level: list[DistributionItem]
    by_experience: dict[str, int]
    by_geography: list[DistributionItem]


class PendingReviewItem(BaseModel):
    """Document requiring human review intervention."""
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    filename: str
    document_type: str
    job_id: uuid.UUID
    current_step: str | None = None
    error_message: str | None = None
    created_at: datetime


class RecentActivityItem(BaseModel):
    """Recently processed document record."""
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    filename: str
    document_type: str
    candidate_name: str | None = None
    person_id: uuid.UUID | None = None
    status: str
    file_size_bytes: int
    created_at: datetime


class DashboardOverviewResponse(BaseModel):
    """Consolidated payload for initial dashboard view rendering."""
    kpis: DashboardKpiResponse
    distributions: DashboardDistributionsResponse
    pending_reviews: list[PendingReviewItem]
    recent_activity: list[RecentActivityItem]
