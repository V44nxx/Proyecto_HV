"""
Unit tests for TextExtractionStep and ProcessDocumentTextUseCase.
"""

import uuid
import fitz
import pytest

from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.process_document_text import ProcessDocumentTextUseCase
from app.config.constants import JobStatus
from app.infrastructure.database.models.document_models import (
    Document,
    DocumentExtraction,
    DocumentPage,
    ProcessingJob,
)
from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor
from app.infrastructure.extraction.pipeline_context import ProcessingContext
from app.infrastructure.extraction.text_extraction_step import TextExtractionStep
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider


def make_pdf(pages_text: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)
        if text:
            page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_text_extraction_step_native_pdf() -> None:
    # PDF with 2 pages of sufficient text
    pdf_bytes = make_pdf([
        "Página 1: Hoja de vida con suficiente texto descriptivo para superar el umbral mínimo",
        "Página 2: Experiencia laboral en desarrollo de software y arquitectura cloud",
    ])
    doc_id = uuid.uuid4()
    context = ProcessingContext(document_id=doc_id, pdf_bytes=pdf_bytes)

    mock_ocr = MockOCRProvider()
    step = TextExtractionStep(ocr_provider=mock_ocr)

    updated_context = await step.execute(context)

    assert updated_context.status == JobStatus.OCR_COMPLETED
    assert updated_context.ocr_result is not None
    assert updated_context.ocr_result.provider == "NATIVE"
    assert updated_context.ocr_result.page_count == 2
    assert "Página 1" in updated_context.ocr_result.full_text


@pytest.mark.asyncio
async def test_text_extraction_step_hybrid_fallback() -> None:
    # Page 1: Native text, Page 2: Empty/scanned page requiring OCR
    pdf_bytes = make_pdf([
        "Página 1: Información básica de contacto Carlos Alberto Gomez Bogotá",
        "",  # Empty page -> will trigger OCR fallback
    ])
    doc_id = uuid.uuid4()
    context = ProcessingContext(document_id=doc_id, pdf_bytes=pdf_bytes)

    mock_ocr = MockOCRProvider(default_text="TEXTO OCR PAGINA ESCANEADA")
    step = TextExtractionStep(ocr_provider=mock_ocr)

    updated_context = await step.execute(context)

    assert updated_context.status == JobStatus.OCR_COMPLETED
    assert updated_context.ocr_result is not None
    assert "HYBRID" in updated_context.ocr_result.provider
    assert updated_context.ocr_result.page_count == 2

    # Page 2 has the OCR text
    assert "TEXTO OCR PAGINA ESCANEADA" in updated_context.ocr_result.pages[1].full_text


class InMemoryDocRepoForExtraction:
    def __init__(self) -> None:
        self.doc: Document | None = None
        self.job: ProcessingJob | None = None
        self.pages: list[DocumentPage] = []
        self.extractions: list[DocumentExtraction] = []

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        if self.doc and self.doc.id == document_id:
            return self.doc
        return None

    async def get_processing_job(self, job_id: uuid.UUID) -> ProcessingJob | None:
        if self.job and self.job.id == job_id:
            return self.job
        return None

    async def get_latest_job_for_document(self, document_id: uuid.UUID) -> ProcessingJob | None:
        if self.job and self.job.document_id == document_id:
            return self.job
        return None

    async def update_processing_job(self, job_id: uuid.UUID, **kwargs) -> ProcessingJob | None:
        if self.job and self.job.id == job_id:
            for k, v in kwargs.items():
                if hasattr(self.job, k) and v is not None:
                    setattr(self.job, k, v)
            return self.job
        return None

    async def list_document_pages(self, document_id: uuid.UUID) -> list[DocumentPage]:
        return self.pages

    async def create_document_extractions(
        self, extractions: list[DocumentExtraction]
    ) -> list[DocumentExtraction]:
        self.extractions.extend(extractions)
        return extractions


class InMemoryStorageForExtraction(StorageProvider):
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def save(self, file_bytes: bytes, key: str) -> str:
        return key

    async def get(self, key: str) -> bytes:
        return self.data

    async def delete(self, key: str) -> bool:
        return True

    async def exists(self, key: str) -> bool:
        return True

    async def get_url(self, key: str) -> str:
        return f"/url/{key}"


@pytest.mark.asyncio
async def test_process_document_text_use_case() -> None:
    doc_id = uuid.uuid4()
    user_id = uuid.uuid4()
    pdf_bytes = make_pdf([
        "Página 1: Hoja de vida Carlos Gomez Ingeniero de Sistemas Universidad Nacional",
    ])

    repo = InMemoryDocRepoForExtraction()
    repo.doc = Document(
        id=doc_id,
        storage_key="test/key.pdf",
        original_filename="cv.pdf",
        file_size_bytes=len(pdf_bytes),
        mime_type="application/pdf",
        checksum_sha256="abc",
        page_count=1,
        uploaded_by=user_id,
    )
    p1 = DocumentPage(id=uuid.uuid4(), document_id=doc_id, page_number=1, width_pts=595.0, height_pts=842.0)
    repo.pages = [p1]
    repo.job = ProcessingJob(id=uuid.uuid4(), document_id=doc_id, status=JobStatus.UPLOADED.value)

    storage = InMemoryStorageForExtraction(pdf_bytes)
    ocr_provider = MockOCRProvider()

    use_case = ProcessDocumentTextUseCase(
        document_repo=repo,  # type: ignore[arg-type]
        storage_provider=storage,
        ocr_provider=ocr_provider,
    )

    result = await use_case.execute(document_id=doc_id)

    assert result.page_count == 1
    assert "Carlos Gomez" in result.full_text
    assert repo.job.status == JobStatus.OCR_COMPLETED.value
    assert repo.job.progress_pct == 30
    assert len(repo.extractions) == 1
    assert repo.extractions[0].page_id == p1.id
    assert repo.extractions[0].raw_text is not None
