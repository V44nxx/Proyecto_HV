"""
Document use cases exports.
"""

from app.application.use_cases.documents.classify_document import ClassifyDocumentUseCase
from app.application.use_cases.documents.delete_document import DeleteDocumentUseCase
from app.application.use_cases.documents.download_document import DownloadDocumentUseCase
from app.application.use_cases.documents.exceptions import (
    DocumentError,
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileFormatError,
)
from app.application.use_cases.documents.extract_formato_unico import ExtractFormatoUnicoUseCase
from app.application.use_cases.documents.get_canonical_resume import GetCanonicalResumeUseCase
from app.application.use_cases.documents.get_document import GetDocumentUseCase
from app.application.use_cases.documents.list_documents import ListDocumentsUseCase
from app.application.use_cases.documents.process_document_text import ProcessDocumentTextUseCase
from app.application.use_cases.documents.upload_document import UploadDocumentUseCase

__all__ = [
    "UploadDocumentUseCase",
    "GetDocumentUseCase",
    "ListDocumentsUseCase",
    "DeleteDocumentUseCase",
    "DownloadDocumentUseCase",
    "ProcessDocumentTextUseCase",
    "ClassifyDocumentUseCase",
    "ExtractFormatoUnicoUseCase",
    "GetCanonicalResumeUseCase",
    "DocumentError",
    "DocumentNotFoundError",
    "DuplicateDocumentError",
    "FileTooLargeError",
    "InvalidFileFormatError",
]

