"""
Domain and application exceptions for document operations.
"""

from typing import Any
import uuid


class DocumentError(Exception):
    """Base exception for all document use cases."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidFileFormatError(DocumentError):
    """Raised when an uploaded file is not a valid PDF."""
    pass


class FileTooLargeError(DocumentError):
    """Raised when an uploaded file exceeds the configured size limit."""
    pass


class DuplicateDocumentError(DocumentError):
    """Raised when an uploaded file has an identical SHA-256 checksum to an existing document."""

    def __init__(
        self,
        message: str,
        existing_document_id: uuid.UUID,
        existing_filename: str,
    ) -> None:
        super().__init__(
            message=message,
            details={
                "existing_document_id": str(existing_document_id),
                "existing_filename": existing_filename,
            },
        )
        self.existing_document_id = existing_document_id
        self.existing_filename = existing_filename


class DocumentNotFoundError(DocumentError):
    """Raised when a requested document is not found."""
    pass
