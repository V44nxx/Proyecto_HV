"""
Get filter options use case.
"""

import structlog

from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.presentation.schemas.search_schemas import (
    CategoryOption,
    FilterOptionsResponse,
    ProfessionOption,
)

logger = structlog.get_logger(__name__)

# Standard Colombian Departments
COLOMBIAN_DEPARTMENTS = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá D.C.", "Bolívar",
    "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó",
    "Córdoba", "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira",
    "Magdalena", "Meta", "Nariño", "Norte de Santander", "Putumayo", "Quindío",
    "Risaralda", "San Andrés y Providencia", "Santander", "Sucre", "Tolima",
    "Valle del Cauca", "Vaupés", "Vichada",
]

# Standard Academic Levels
ACADEMIC_LEVELS = [
    "BASIC", "SECONDARY", "HIGH_SCHOOL", "TECHNICAL", "TECHNOLOGIST",
    "UNDERGRADUATE", "SPECIALIZATION", "MASTER", "DOCTORATE", "OTHER",
]


class GetFilterOptionsUseCase:
    """Retrieves available categories, professions, levels, and departments for UI filters."""

    def __init__(self, search_repo: SearchRepository) -> None:
        self._search_repo = search_repo

    async def execute(self) -> FilterOptionsResponse:
        # Seed if empty so options are never blank
        categories = await self._search_repo.list_categories_with_professions()
        if not categories:
            await self._search_repo.seed_default_taxonomy()
            categories = await self._search_repo.list_categories_with_professions()

        cat_options: list[CategoryOption] = []
        all_professions: list[ProfessionOption] = []
        for cat in categories:
            prof_options = []
            for p in cat.professions:
                if p.is_active:
                    aliases = p.aliases
                    if isinstance(aliases, str):
                        import json
                        try:
                            aliases = json.loads(aliases)
                        except Exception:
                            aliases = [aliases]
                    prof_item = ProfessionOption(
                        id=p.id,
                        name=p.name,
                        category_id=cat.id,
                        aliases=aliases,
                    )
                    prof_options.append(prof_item)
                    all_professions.append(prof_item)
            cat_options.append(
                CategoryOption(
                    id=cat.id,
                    name=cat.name,
                    code=str(cat.id),
                    description=cat.description,
                    professions=prof_options,
                )
            )

        all_professions.sort(key=lambda x: x.name)

        return FilterOptionsResponse(
            categories=cat_options,
            professions=all_professions,
            academic_levels=ACADEMIC_LEVELS,
            departments=COLOMBIAN_DEPARTMENTS,
        )
