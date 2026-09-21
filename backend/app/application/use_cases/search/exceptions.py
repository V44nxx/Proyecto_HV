"""
Search and candidate query exceptions.
"""

from typing import Any
import uuid


class SearchError(Exception):
    """Base exception for search operations."""
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CandidateNotFoundError(SearchError):
    """Raised when a candidate person record is not found."""
    def __init__(self, person_id: uuid.UUID) -> None:
        super().__init__(
            message=f"Candidato con ID {person_id} no encontrado.",
            details={"person_id": str(person_id)},
        )
        self.person_id = person_id
