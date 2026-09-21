"""
Unit tests for SearchRepository.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.infrastructure.database.models.person_models import (
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.repositories.search_repository import SearchRepository


@pytest.mark.asyncio
async def test_seed_default_taxonomy():
    db = AsyncMock()
    db.add = MagicMock()
    # Mock category execute: first None, so it creates categories and professions
    mock_cat_result = MagicMock()
    mock_cat_result.scalar_one_or_none.return_value = None

    mock_prof_result = MagicMock()
    mock_prof_result.scalar_one_or_none.return_value = None

    db.execute.side_effect = [mock_cat_result, mock_prof_result] * 50

    repo = SearchRepository(db)
    count = await repo.seed_default_taxonomy()
    assert count > 0
    assert db.add.called
    assert db.flush.called


@pytest.mark.asyncio
async def test_list_categories_with_professions():
    db = AsyncMock()
    mock_cat = ProfessionalCategory(
        id=uuid.uuid4(),
        name="Ingeniería y Tecnología",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_cat]
    db.execute.return_value = mock_result

    repo = SearchRepository(db)
    res = await repo.list_categories_with_professions()
    assert len(res) == 1
    assert res[0].name == "Ingeniería y Tecnología"


@pytest.mark.asyncio
async def test_get_candidate_detail():
    db = AsyncMock()
    person_id = uuid.uuid4()
    mock_person = Person(
        id=person_id,
        first_name="Carlos",
        first_surname="Ramirez",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_person
    db.execute.return_value = mock_result

    repo = SearchRepository(db)
    res = await repo.get_candidate_detail(person_id)
    assert res == mock_person
    assert res.first_name == "Carlos"


@pytest.mark.asyncio
async def test_search_candidates():
    db = AsyncMock()
    person_id = uuid.uuid4()
    mock_person = Person(
        id=person_id,
        first_name="Sofia",
        first_surname="Castro",
    )

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [mock_person]

    db.execute.side_effect = [count_result, items_result]

    repo = SearchRepository(db)

    # Test with complex filters
    filters = {
        "q": "Sofia",
        "identification_number": "12345",
        "name": "Sofia Castro",
        "category_id": uuid.uuid4(),
        "profession_id": uuid.uuid4(),
        "profession_name": "Ingeniería",
        "academic_level": "UNDERGRADUATE",
        "institution": "Universidad Nacional",
        "company": "Tech Corp",
        "position": "Backend Developer",
        "department": "Antioquia",
        "municipality": "Medellín",
        "min_years_experience": 3,
        "max_years_experience": 10,
        "language": "INGLES",
        "skills": "Python",
        "certification": "AWS",
        "document_type": "ATS",
        "created_from": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "created_to": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    candidates, total = await repo.search_candidates(
        filters=filters,
        page=1,
        page_size=10,
        sort_by="name",
        sort_order="asc",
    )

    assert total == 1
    assert len(candidates) == 1
    assert candidates[0].first_name == "Sofia"


@pytest.mark.asyncio
async def test_get_search_facets():
    db = AsyncMock()

    total_res = MagicMock()
    total_res.scalar.return_value = 42

    level_res = MagicMock()
    level_res.all.return_value = [("UNDERGRADUATE", 30), ("MASTER", 12)]

    dep_res = MagicMock()
    dep_res.all.return_value = [("Antioquia", 25), ("Bogotá D.C.", 17)]

    prof_res = MagicMock()
    prof_res.all.return_value = [("Ingeniería de Sistemas", 20)]

    cat_res = MagicMock()
    cat_res.all.return_value = [("Ingeniería y Tecnología", 25)]

    db.execute.side_effect = [total_res, level_res, dep_res, prof_res, cat_res]

    repo = SearchRepository(db)
    facets = await repo.get_search_facets()

    assert facets["total_candidates"] == 42
    assert facets["by_academic_level"]["UNDERGRADUATE"] == 30
    assert facets["by_department"]["Antioquia"] == 25
    assert facets["by_profession"]["Ingeniería de Sistemas"] == 20
    assert facets["by_category"]["Ingeniería y Tecnología"] == 25
