"""
Unit tests for PersonRepository.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.infrastructure.database.models.document_models import ExtractedField
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
)
from app.infrastructure.database.models.resume_models import (
    Education,
    ExperienceSummary,
    Language,
    WorkExperience,
)
from app.infrastructure.database.repositories.person_repository import PersonRepository


@pytest.mark.asyncio
async def test_get_by_id():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_person = Person(id=uuid.uuid4(), first_name="Ana")
    mock_result.scalar_one_or_none.return_value = mock_person
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    result = await repo.get_by_id(mock_person.id)
    assert result == mock_person
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_identification():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_person = Person(id=uuid.uuid4(), identification_type="CC", identification_number="123")
    mock_result.scalar_one_or_none.return_value = mock_person
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    # None arguments return None without querying DB
    assert await repo.get_by_identification(None, "123") is None
    assert await repo.get_by_identification("CC", None) is None

    result = await repo.get_by_identification("CC", "123")
    assert result == mock_person


@pytest.mark.asyncio
async def test_create_person_new():
    db = AsyncMock()
    db.add = MagicMock()
    # No existing person
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    new_person = Person(identification_type="CC", identification_number="987", first_name="Carlos")
    result = await repo.create_or_update_person(new_person)

    assert result == new_person
    db.add.assert_called_once_with(new_person)
    assert db.flush.await_count == 1
    assert db.refresh.await_count == 1


@pytest.mark.asyncio
async def test_update_person_existing():
    db = AsyncMock()
    db.add = MagicMock()
    existing_person = Person(id=uuid.uuid4(), identification_type="CC", identification_number="987", first_name="Old")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_person
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    updated = Person(identification_type="CC", identification_number="987", first_name="New")
    result = await repo.create_or_update_person(updated)

    assert result == existing_person
    assert existing_person.first_name == "New"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_contact_information():
    db = AsyncMock()
    db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    contact = ContactInformation(person_id=uuid.uuid4(), email="test@example.com")
    res = await repo.save_contact_information(contact)
    assert res == contact
    db.add.assert_called_once_with(contact)
    db.flush.assert_awaited_once()

    # Now existing update
    existing_contact = ContactInformation(person_id=contact.person_id, email="old@example.com")
    mock_result.scalar_one_or_none.return_value = existing_contact
    contact_update = ContactInformation(person_id=contact.person_id, email="new@example.com")
    res_updated = await repo.save_contact_information(contact_update)
    assert res_updated == existing_contact
    assert existing_contact.email == "new@example.com"


@pytest.mark.asyncio
async def test_save_bulk_entities():
    db = AsyncMock()
    db.add_all = MagicMock()
    repo = PersonRepository(db)

    # Empty lists return early
    assert await repo.save_educations([]) == []
    assert await repo.save_work_experiences([]) == []
    assert await repo.save_languages([]) == []
    assert await repo.save_extracted_fields([]) == []

    # Non empty
    p_id = uuid.uuid4()
    edus = [Education(person_id=p_id, level="HIGH_SCHOOL")]
    exps = [WorkExperience(person_id=p_id, company_name="Corp")]
    langs = [Language(person_id=p_id, language_name="EN")]
    fields = [ExtractedField(extraction_id=uuid.uuid4(), field_name="name", raw_value="Carlos")]

    await repo.save_educations(edus)
    await repo.save_work_experiences(exps)
    await repo.save_languages(langs)
    await repo.save_extracted_fields(fields)

    assert db.add_all.call_count == 4
    assert db.flush.await_count == 4


@pytest.mark.asyncio
async def test_save_experience_summary():
    db = AsyncMock()
    db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    p_id = uuid.uuid4()
    summary = ExperienceSummary(person_id=p_id, total_years=5)
    res = await repo.save_experience_summary(summary)
    assert res == summary
    db.add.assert_called_once_with(summary)

    # Existing update
    existing_summary = ExperienceSummary(person_id=p_id, total_years=3)
    mock_result.scalar_one_or_none.return_value = existing_summary
    new_summary = ExperienceSummary(person_id=p_id, total_years=8)
    res2 = await repo.save_experience_summary(new_summary)
    assert res2 == existing_summary
    assert existing_summary.total_years == 8


@pytest.mark.asyncio
async def test_get_person_with_details():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_person = Person(id=uuid.uuid4(), first_name="Carlos")
    mock_result.scalar_one_or_none.return_value = mock_person
    db.execute.return_value = mock_result

    repo = PersonRepository(db)
    res = await repo.get_person_with_details(mock_person.id)
    assert res == mock_person
