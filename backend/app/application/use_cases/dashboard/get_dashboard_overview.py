"""
Get consolidated dashboard overview use case.
"""

import structlog

from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
from app.presentation.schemas.dashboard_schemas import (
    DashboardDistributionsResponse,
    DashboardKpiResponse,
    DashboardOverviewResponse,
    DistributionItem,
    PendingReviewItem,
    RecentActivityItem,
)

logger = structlog.get_logger(__name__)


class GetDashboardOverviewUseCase:
    """Consolidates KPIs, distributions, attention queues, and activity feeds."""

    def __init__(self, dashboard_repo: DashboardRepository) -> None:
        self._dashboard_repo = dashboard_repo

    async def execute(self) -> DashboardOverviewResponse:
        # 1. KPIs
        kpis_data = await self._dashboard_repo.get_kpis()
        kpis = DashboardKpiResponse(**kpis_data)

        # 2. Distributions
        formats = await self._dashboard_repo.get_format_distribution()
        categories = await self._dashboard_repo.get_category_distribution()
        professions = await self._dashboard_repo.get_top_professions(limit=10)
        levels = await self._dashboard_repo.get_academic_level_distribution()
        experience = await self._dashboard_repo.get_experience_distribution()
        geography = await self._dashboard_repo.get_geographic_distribution(limit=10)

        distributions = DashboardDistributionsResponse(
            by_format=[DistributionItem(**i) for i in formats],
            by_category=[DistributionItem(**i) for i in categories],
            top_professions=[DistributionItem(**i) for i in professions],
            by_academic_level=[DistributionItem(**i) for i in levels],
            by_experience=experience,
            by_geography=[DistributionItem(**i) for i in geography],
        )

        # 3. Pending reviews
        pending_data = await self._dashboard_repo.get_documents_requiring_review(limit=10)
        pending_reviews = [PendingReviewItem(**i) for i in pending_data]

        # 4. Recent activity
        activity_data = await self._dashboard_repo.get_recent_activity(limit=10)
        recent_activity = [RecentActivityItem(**i) for i in activity_data]

        return DashboardOverviewResponse(
            kpis=kpis,
            distributions=distributions,
            pending_reviews=pending_reviews,
            recent_activity=recent_activity,
        )
