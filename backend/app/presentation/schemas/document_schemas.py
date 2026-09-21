"""
Pydantic schemas for document endpoints.
"""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Public representation of a Document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID | None = None
    storage_key: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    checksum_sha256: str
    page_count: int | None = None
    document_type: str
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProcessingJobResponse(BaseModel):
    """Status and tracking details of an asynchronous processing job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    queue_name: str | None = None
    worker_id: str | None = None
    current_step: str | None = None
    progress_pct: int = 0
    error_message: str | None = None
    error_type: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Response returned upon successful document upload."""

    message: str = "Documento subido exitosamente para procesamiento"
    document: DocumentResponse
    job: ProcessingJobResponse


class DocumentDetailResponse(BaseModel):
    """Full detail of a document including its latest processing job."""

    document: DocumentResponse
    latest_job: ProcessingJobResponse | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
