"""
Get search facets use case.
"""

from typing import Any
import structlog

from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.presentation.schemas.search_schemas import SearchFacetsResponse

logger = structlog.get_logger(__name__)


class GetSearchFacetsUseCase:
    """Computes high-level aggregated search facets across all candidates."""

    def __init__(self, search_repo: SearchRepository) -> None:
        self._search_repo = search_repo

    async def execute(self) -> SearchFacetsResponse:
        facets = await self._search_repo.get_search_facets()
        return SearchFacetsResponse(**facets)
