"""
Get dashboard distributions use case.
"""

import structlog

from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
from app.presentation.schemas.dashboard_schemas import (
    DashboardDistributionsResponse,
    DistributionItem,
)

logger = structlog.get_logger(__name__)


class GetDashboardDistributionsUseCase:
    """Aggregates all analytical distributions across documents, candidates, and experience."""

    def __init__(self, dashboard_repo: DashboardRepository) -> None:
        self._dashboard_repo = dashboard_repo

    async def execute(self) -> DashboardDistributionsResponse:
        formats = await self._dashboard_repo.get_format_distribution()
        categories = await self._dashboard_repo.get_category_distribution()
        professions = await self._dashboard_repo.get_top_professions(limit=10)
        levels = await self._dashboard_repo.get_academic_level_distribution()
        experience = await self._dashboard_repo.get_experience_distribution()
        geography = await self._dashboard_repo.get_geographic_distribution(limit=10)

        return DashboardDistributionsResponse(
            by_format=[DistributionItem(**i) for i in formats],
            by_category=[DistributionItem(**i) for i in categories],
            top_professions=[DistributionItem(**i) for i in professions],
            by_academic_level=[DistributionItem(**i) for i in levels],
            by_experience=experience,
            by_geography=[DistributionItem(**i) for i in geography],
        )
