"""
ORM models: documents, document_pages, document_extractions,
extracted_fields, processing_jobs.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.constants import DocumentType, JobStatus, ReviewStatus
from app.infrastructure.database.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utcnow,
)


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    A physical document file uploaded to the system.

    The original file is NEVER modified after upload.
    storage_key is the UUID-based path in the storage backend.
    checksum_sha256 enables duplicate detection and integrity verification.
    """

    __tablename__ = "documents"

    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---- Storage ----
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Classification ----
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentType.UNKNOWN
    )

    # ---- Audit ----
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('FORMATO_UNICO', 'ATS', 'UNKNOWN')",
            name="chk_document_type",
        ),
    )

    # ---- Relationships ----
    person: Mapped["Person | None"] = relationship("Person", back_populates="documents")
    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    extractions: Mapped[list["DocumentExtraction"]] = relationship(
        "DocumentExtraction", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.document_type}>"


class DocumentPage(Base, UUIDPrimaryKeyMixin):
    """
    Individual pages of a document.
    Stores physical dimensions and whether native text was detected.
    """

    __tablename__ = "document_pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width_pts: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_pts: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_text: Mapped[bool] = mapped_column(
        __import__("sqlalchemy").Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        default=utcnow,
        server_default=__import__("sqlalchemy").text("NOW()"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_page"),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    extractions: Mapped[list["DocumentExtraction"]] = relationship(
        "DocumentExtraction", back_populates="page"
    )

    def __repr__(self) -> str:
        return f"<DocumentPage doc={self.document_id} page={self.page_number}>"


class DocumentExtraction(Base, UUIDPrimaryKeyMixin):
    """
    Result of an OCR/text-extraction pass on a document or page.
    Stores the raw text, provider response, and confidence.
    """

    __tablename__ = "document_extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=True,
    )

    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        default=utcnow,
        server_default=__import__("sqlalchemy").text("NOW()"),
        nullable=False,
    )

    document: Mapped["Document"] = relationship("Document", back_populates="extractions")
    page: Mapped["DocumentPage | None"] = relationship(
        "DocumentPage", back_populates="extractions"
    )
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="extraction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DocumentExtraction doc={self.document_id} provider={self.ocr_provider}>"


class ExtractedField(Base, UUIDPrimaryKeyMixin):
    """
    A single field extracted from a document, with full traceability.

    Stores:
    - The raw OCR/extractor value
    - The normalized value
    - Page number and bounding box for source navigation
    - Review status and corrected value when a human edits it
    """

    __tablename__ = "extracted_fields"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_extractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # ---- Values ----
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Source traceability ----
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bounding_box: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True  # {x, y, width, height} in points
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # ---- Human review ----
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewStatus.PENDING
    )
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    corrected_at: Mapped[datetime | None] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True), nullable=True
    )
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        default=utcnow,
        server_default=__import__("sqlalchemy").text("NOW()"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="chk_field_confidence"),
        CheckConstraint(
            "review_status IN ('PENDING', 'ACCEPTED', 'CORRECTED', 'REJECTED')",
            name="chk_field_review_status",
        ),
    )

    extraction: Mapped["DocumentExtraction"] = relationship(
        "DocumentExtraction", back_populates="extracted_fields"
    )

    @property
    def effective_value(self) -> str | None:
        """Returns corrected value if reviewed, otherwise normalized value."""
        if self.review_status == ReviewStatus.CORRECTED and self.corrected_value is not None:
            return self.corrected_value
        return self.normalized_value

    def __repr__(self) -> str:
        return f"<ExtractedField field={self.field_name} confidence={self.confidence:.2f}>"


class ProcessingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks the async processing lifecycle of a document.

    A document can have multiple processing jobs (e.g., retry after failure).
    The pipeline updates job status at each step.
    """

    __tablename__ = "processing_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=JobStatus.UPLOADED
    )

    # ---- Tracking ----
    queue_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True), nullable=True
    )

    # ---- Error handling ----
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)

    # ---- Current pipeline step (for progress display) ----
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    progress_pct: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    # ---- Audit ----
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED','QUEUED','PROCESSING','OCR_COMPLETED',"
            "'EXTRACTING','REVIEW_REQUIRED','COMPLETED','FAILED')",
            name="chk_job_status",
        ),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="processing_jobs")

    @property
    def is_terminal(self) -> bool:
        return self.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.REVIEW_REQUIRED}

    @property
    def can_retry(self) -> bool:
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries

    def __repr__(self) -> str:
        return f"<ProcessingJob doc={self.document_id} status={self.status}>"
