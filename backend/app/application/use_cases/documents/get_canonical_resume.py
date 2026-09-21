"""
Get canonical resume use case.
Retrieves the extracted canonical data associated with a document.
"""

import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.infrastructure.database.models.person_models import Person
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.person_repository import PersonRepository

logger = structlog.get_logger(__name__)


class GetCanonicalResumeUseCase:
    """
    Retrieves candidate person and full structured profile for a document.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        person_repo: PersonRepository,
    ) -> None:
        self._doc_repo = document_repo
        self._person_repo = person_repo

    async def execute(self, document_id: uuid.UUID) -> Person | None:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        if not doc.person_id:
            return None

        return await self._person_repo.get_person_with_details(doc.person_id)
