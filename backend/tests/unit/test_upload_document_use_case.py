"""
Unit tests for UploadDocumentUseCase.
"""

import hashlib
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import fitz  # PyMuPDF
import pytest

from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.exceptions import (
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileFormatError,
)
from app.application.use_cases.documents.upload_document import UploadDocumentUseCase
from app.config.constants import JobStatus
from app.config.settings import Settings
from app.infrastructure.database.models.document_models import (
    Document,
    DocumentPage,
    ProcessingJob,
)


def make_pdf(text: str = "Hoja de Vida de Prueba - Carlos Gomez", pages: int = 1) -> bytes:
    """Helper to generate a real PDF in memory with PyMuPDF."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 size in points
        # Insert enough text so it is recognized as text-containing page
        page.insert_text((50, 72), f"{text} - Página {i + 1} con contenido detallado de prueba")
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


class InMemoryDocumentRepo:
    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, Document] = {}
        self.pages: list[DocumentPage] = []
        self.jobs: dict[uuid.UUID, ProcessingJob] = {}

    async def create_document(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        doc = self.documents.get(document_id)
        if doc and doc.deleted_at is None:
            return doc
        return None

    async def get_by_checksum(self, checksum_sha256: str) -> Document | None:
        for doc in self.documents.values():
            if doc.checksum_sha256 == checksum_sha256 and doc.deleted_at is None:
                return doc
        return None

    async def create_document_pages(self, pages: list[DocumentPage]) -> list[DocumentPage]:
        self.pages.extend(pages)
        return pages

    async def create_processing_job(self, job: ProcessingJob) -> ProcessingJob:
        self.jobs[job.id] = job
        return job


class InMemoryStorageProvider(StorageProvider):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def save(self, file_bytes: bytes, key: str) -> str:
        self.files[key] = file_bytes
        return key

    async def get(self, key: str) -> bytes:
        return self.files[key]

    async def delete(self, key: str) -> bool:
        if key in self.files:
            del self.files[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self.files

    async def get_url(self, key: str) -> str:
        return f"/test/{key}"


@pytest.fixture
def doc_repo() -> InMemoryDocumentRepo:
    return InMemoryDocumentRepo()


@pytest.fixture
def user_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create_audit_log = AsyncMock()
    return repo


@pytest.fixture
def storage() -> InMemoryStorageProvider:
    return InMemoryStorageProvider()


@pytest.fixture
def use_case(
    doc_repo: InMemoryDocumentRepo,
    user_repo: AsyncMock,
    storage: InMemoryStorageProvider,
) -> UploadDocumentUseCase:
    test_settings = Settings(
        max_upload_size_mb=10,
        secret_key="test-secret-key-at-least-32-characters-long",
        postgres_password="test_password",
    )
    return UploadDocumentUseCase(
        document_repo=doc_repo,  # type: ignore[arg-type]
        user_repo=user_repo,
        storage_provider=storage,
        settings=test_settings,
    )


@pytest.mark.asyncio
async def test_upload_valid_pdf_success(
    use_case: UploadDocumentUseCase,
    doc_repo: InMemoryDocumentRepo,
    storage: InMemoryStorageProvider,
    user_repo: AsyncMock,
) -> None:
    pdf_bytes = make_pdf(pages=2)
    user_id = uuid.uuid4()

    doc, job = await use_case.execute(
        file_bytes=pdf_bytes,
        filename="hoja_de_vida.pdf",
        content_type="application/pdf",
        uploaded_by=user_id,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
    )

    assert doc.id is not None
    assert doc.original_filename == "hoja_de_vida.pdf"
    assert doc.file_size_bytes == len(pdf_bytes)
    assert doc.page_count == 2
    assert doc.checksum_sha256 == hashlib.sha256(pdf_bytes).hexdigest()
    assert doc.uploaded_by == user_id

    # Verify storage
    assert doc.storage_key in storage.files
    assert storage.files[doc.storage_key] == pdf_bytes

    # Verify job
    assert job.document_id == doc.id
    assert job.status == JobStatus.UPLOADED.value
    assert job.progress_pct == 0

    # Verify pages
    assert len(doc_repo.pages) == 2
    assert doc_repo.pages[0].page_number == 1
    assert doc_repo.pages[0].has_text is True
    assert doc_repo.pages[1].page_number == 2

    # Verify audit log was created
    user_repo.create_audit_log.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_empty_file_rejected(use_case: UploadDocumentUseCase) -> None:
    with pytest.raises(InvalidFileFormatError) as exc_info:
        await use_case.execute(
            file_bytes=b"",
            filename="empty.pdf",
            content_type="application/pdf",
            uploaded_by=uuid.uuid4(),
        )
    assert "vacío" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_upload_file_too_large_rejected(
    doc_repo: InMemoryDocumentRepo,
    user_repo: AsyncMock,
    storage: InMemoryStorageProvider,
) -> None:
    # Set limit to 1 MB for testing
    tiny_limit_settings = Settings(
        max_upload_size_mb=1,
        secret_key="test-secret-key-at-least-32-characters-long",
        postgres_password="test_password",
    )
    custom_use_case = UploadDocumentUseCase(
        document_repo=doc_repo,  # type: ignore[arg-type]
        user_repo=user_repo,
        storage_provider=storage,
        settings=tiny_limit_settings,
    )

    large_bytes = b"%PDF" + b"X" * (2 * 1024 * 1024)  # 2MB
    with pytest.raises(FileTooLargeError):
        await custom_use_case.execute(
            file_bytes=large_bytes,
            filename="too_large.pdf",
            content_type="application/pdf",
            uploaded_by=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_upload_invalid_magic_bytes_rejected(use_case: UploadDocumentUseCase) -> None:
    fake_pdf = b"NOT A PDF FILE AT ALL"
    with pytest.raises(InvalidFileFormatError) as exc_info:
        await use_case.execute(
            file_bytes=fake_pdf,
            filename="fake.pdf",
            content_type="application/pdf",
            uploaded_by=uuid.uuid4(),
        )
    assert "cabecera" in exc_info.value.message.lower() or "magic" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_upload_corrupt_pdf_rejected(use_case: UploadDocumentUseCase) -> None:
    # Starts with %PDF but corrupted afterwards
    corrupt_pdf = b"%PDF-1.4\ncorrupted content that cannot be parsed by PyMuPDF"
    with pytest.raises(InvalidFileFormatError):
        await use_case.execute(
            file_bytes=corrupt_pdf,
            filename="corrupt.pdf",
            content_type="application/pdf",
            uploaded_by=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_duplicate_pdf_rejected(use_case: UploadDocumentUseCase) -> None:
    pdf_bytes = make_pdf()
    user_id = uuid.uuid4()

    # First upload succeeds
    doc1, _ = await use_case.execute(
        file_bytes=pdf_bytes,
        filename="original.pdf",
        content_type="application/pdf",
        uploaded_by=user_id,
    )

    # Second upload of same content must be rejected
    with pytest.raises(DuplicateDocumentError) as exc_info:
        await use_case.execute(
            file_bytes=pdf_bytes,
            filename="duplicate_name.pdf",
            content_type="application/pdf",
            uploaded_by=user_id,
        )

    assert exc_info.value.existing_document_id == doc1.id
    assert exc_info.value.existing_filename == "original.pdf"
