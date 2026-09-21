"""
Get dashboard KPIs use case.
"""

import structlog

from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
from app.presentation.schemas.dashboard_schemas import DashboardKpiResponse

logger = structlog.get_logger(__name__)


class GetDashboardKpisUseCase:
    """Calculates high-level executive and operational metrics."""

    def __init__(self, dashboard_repo: DashboardRepository) -> None:
        self._dashboard_repo = dashboard_repo

    async def execute(self) -> DashboardKpiResponse:
        kpis = await self._dashboard_repo.get_kpis()
        return DashboardKpiResponse(**kpis)
