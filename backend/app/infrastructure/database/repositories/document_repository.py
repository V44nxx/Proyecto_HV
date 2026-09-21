"""
Document repository: database operations for documents, document pages,
and processing jobs.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.document_models import (
    Document,
    DocumentExtraction,
    DocumentPage,
    ProcessingJob,
)

logger = structlog.get_logger(__name__)


class DocumentRepository:
    """Handles persistence operations for physical documents and jobs."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ---- Document queries & persistence ----

    async def create_document(self, document: Document) -> Document:
        """Persist a new Document record."""
        self._db.add(document)
        await self._db.flush()
        await self._db.refresh(document)
        logger.info(
            "document_record_created",
            document_id=str(document.id),
            checksum=document.checksum_sha256,
        )
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Fetch an active document by UUID."""
        stmt = select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_checksum(self, checksum_sha256: str) -> Document | None:
        """
        Check if an active document with the same SHA-256 hash exists.
        Used for deduplication.
        """
        stmt = select(Document).where(
            Document.checksum_sha256 == checksum_sha256,
            Document.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 20,
        document_type: str | None = None,
        person_id: uuid.UUID | None = None,
    ) -> tuple[list[Document], int]:
        """
        List documents with pagination and optional filters.
        Returns a tuple of (documents, total_count).
        """
        base_query = select(Document).where(Document.deleted_at.is_(None))
        count_query = select(func.count(Document.id)).where(Document.deleted_at.is_(None))

        if document_type:
            base_query = base_query.where(Document.document_type == document_type)
            count_query = count_query.where(Document.document_type == document_type)

        if person_id:
            base_query = base_query.where(Document.person_id == person_id)
            count_query = count_query.where(Document.person_id == person_id)

        # Count total matching records
        total_result = await self._db.execute(count_query)
        total = total_result.scalar_one() or 0

        # Fetch page
        stmt = (
            base_query
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items_result = await self._db.execute(stmt)
        items = list(items_result.scalars().all())

        return items, total

    async def soft_delete(self, document_id: uuid.UUID) -> bool:
        """Soft-delete a document by setting its deleted_at timestamp."""
        doc = await self.get_by_id(document_id)
        if not doc:
            return False

        doc.deleted_at = datetime.now(timezone.utc)
        await self._db.flush()
        logger.info("document_soft_deleted", document_id=str(document_id))
        return True

    # ---- Processing Job queries & persistence ----

    async def create_processing_job(self, job: ProcessingJob) -> ProcessingJob:
        """Persist a new ProcessingJob record."""
        self._db.add(job)
        await self._db.flush()
        await self._db.refresh(job)
        logger.info(
            "processing_job_created",
            job_id=str(job.id),
            document_id=str(job.document_id),
            status=job.status,
        )
        return job

    async def get_processing_job(self, job_id: uuid.UUID) -> ProcessingJob | None:
        """Fetch a processing job by UUID."""
        stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_job_for_document(
        self, document_id: uuid.UUID
    ) -> ProcessingJob | None:
        """Fetch the most recent processing job for a document."""
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_processing_job(
        self,
        job_id: uuid.UUID,
        status: str | None = None,
        current_step: str | None = None,
        progress_pct: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> ProcessingJob | None:
        """Update job tracking attributes."""
        job = await self.get_processing_job(job_id)
        if not job:
            return None

        if status is not None:
            job.status = status
        if current_step is not None:
            job.current_step = current_step
        if progress_pct is not None:
            job.progress_pct = progress_pct
        if error_message is not None:
            job.error_message = error_message
        if error_type is not None:
            job.error_type = error_type
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at

        await self._db.flush()
        return job

    # ---- Document Pages ----

    async def create_document_pages(
        self, pages: list[DocumentPage]
    ) -> list[DocumentPage]:
        """Bulk insert pages for a document."""
        self._db.add_all(pages)
        await self._db.flush()
        return pages

    async def list_document_pages(
        self, document_id: uuid.UUID
    ) -> list[DocumentPage]:
        """List all pages for a document ordered by page number."""
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    # ---- Document Extractions ----

    async def create_document_extraction(
        self, extraction: DocumentExtraction
    ) -> DocumentExtraction:
        """Persist a single DocumentExtraction record."""
        self._db.add(extraction)
        await self._db.flush()
        await self._db.refresh(extraction)
        return extraction

    async def create_document_extractions(
        self, extractions: list[DocumentExtraction]
    ) -> list[DocumentExtraction]:
        """Bulk insert DocumentExtraction records."""
        self._db.add_all(extractions)
        await self._db.flush()
        return extractions

    async def get_extractions_for_document(
        self, document_id: uuid.UUID
    ) -> list[DocumentExtraction]:
        """Fetch all extraction records for a document."""
        stmt = (
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == document_id)
            .order_by(DocumentExtraction.extracted_at.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
