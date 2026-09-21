"""
Processing context: the data container passed through the extraction pipeline steps.
"""

from dataclasses import dataclass, field
from typing import Any
import uuid

from app.application.interfaces.ocr_provider import OCRDocumentResult
from app.config.constants import DocumentType, JobStatus


@dataclass
class ProcessingContext:
    """
    Mutable state passed sequentially through each pipeline step.
    Tracks extracted text, OCR tokens, classified type, and intermediate progress.
    """
    document_id: uuid.UUID
    pdf_bytes: bytes
    job_id: uuid.UUID | None = None

    # Step results
    current_step: str = "ingestion"
    status: JobStatus = JobStatus.PROCESSING
    ocr_result: OCRDocumentResult | None = None
    document_type: DocumentType = DocumentType.UNKNOWN
    canonical_resume: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0

    # Metadata & error tracing
    error: str | None = None
    error_type: str | None = None
    step_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_step_completed(self, step_name: str, duration_ms: int = 0) -> None:
        self.step_history.append({
            "step": step_name,
            "duration_ms": duration_ms,
        })
        self.current_step = step_name
