"""
Unit tests for ReviewRepository.
"""

from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.config.constants import ReviewStatus
from app.infrastructure.database.models.document_models import ExtractedField
from app.infrastructure.database.models.user_models import AuditLog
from app.infrastructure.database.repositories.review_repository import ReviewRepository


@pytest.mark.asyncio
async def test_get_field_by_id():
    db = AsyncMock()
    mock_field = ExtractedField(
        id=uuid.uuid4(),
        extraction_id=uuid.uuid4(),
        field_name="identification_number",
        raw_value="12345",
        normalized_value="12345",
        page_number=1,
        confidence=0.95,
        review_status=ReviewStatus.PENDING.value,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_field
    db.execute.return_value = mock_result

    repo = ReviewRepository(db)
    result = await repo.get_field_by_id(mock_field.id)
    assert result == mock_field


@pytest.mark.asyncio
async def test_get_fields_for_document():
    db = AsyncMock()
    doc_id = uuid.uuid4()
    mock_field = ExtractedField(
        id=uuid.uuid4(),
        extraction_id=uuid.uuid4(),
        field_name="email",
        page_number=1,
        confidence=0.9,
        review_status=ReviewStatus.PENDING.value,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_field]
    db.execute.return_value = mock_result

    repo = ReviewRepository(db)
    # Test without filters
    res = await repo.get_fields_for_document(doc_id)
    assert len(res) == 1
    assert res[0] == mock_field

    # Test with status and page filter
    res_filtered = await repo.get_fields_for_document(doc_id, status_filter="PENDING", page_number=1)
    assert len(res_filtered) == 1


@pytest.mark.asyncio
async def test_update_field_status_not_found():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    repo = ReviewRepository(db)
    result = await repo.update_field_status(uuid.uuid4(), ReviewStatus.ACCEPTED.value)
    assert result is None


@pytest.mark.asyncio
async def test_update_field_status_success():
    db = AsyncMock()
    field_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()
    mock_field = ExtractedField(
        id=field_id,
        extraction_id=uuid.uuid4(),
        field_name="first_name",
        raw_value="Carlos",
        normalized_value="Carlos",
        page_number=1,
        confidence=0.9,
        review_status=ReviewStatus.PENDING.value,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_field
    db.execute.return_value = mock_result

    repo = ReviewRepository(db)
    result = await repo.update_field_status(
        field_id=field_id,
        review_status=ReviewStatus.CORRECTED.value,
        corrected_value="Carlos Alberto",
        correction_note="Agregado segundo nombre",
        reviewer_id=reviewer_id,
    )

    assert result == mock_field
    assert mock_field.review_status == ReviewStatus.CORRECTED.value
    assert mock_field.corrected_value == "Carlos Alberto"
    assert mock_field.correction_note == "Agregado segundo nombre"
    assert mock_field.corrected_by == reviewer_id
    assert mock_field.corrected_at is not None
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_update_status():
    db = AsyncMock()
    repo = ReviewRepository(db)

    # Empty list
    assert await repo.batch_update_status([], ReviewStatus.ACCEPTED.value) == 0

    # Non-empty list
    mock_result = MagicMock()
    mock_result.rowcount = 3
    db.execute.return_value = mock_result

    f_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    count = await repo.batch_update_status(f_ids, ReviewStatus.ACCEPTED.value)
    assert count == 3
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_review_summary():
    db = AsyncMock()
    doc_id = uuid.uuid4()
    mock_result = MagicMock()
    # Rows: [(status, count)]
    mock_result.all.return_value = [
        (ReviewStatus.PENDING.value, 2),
        (ReviewStatus.ACCEPTED.value, 5),
        (ReviewStatus.CORRECTED.value, 1),
        (ReviewStatus.REJECTED.value, 0),
    ]
    db.execute.return_value = mock_result

    repo = ReviewRepository(db)
    summary = await repo.get_review_summary(doc_id)

    assert summary["total_fields"] == 8
    assert summary["pending_count"] == 2
    assert summary["accepted_count"] == 5
    assert summary["corrected_count"] == 1
    assert summary["rejected_count"] == 0
    assert summary["completion_pct"] == 75.0
    assert summary["is_complete"] is False


@pytest.mark.asyncio
async def test_record_audit_log():
    db = AsyncMock()
    db.add = MagicMock()
    repo = ReviewRepository(db)

    user_id = uuid.uuid4()
    res_id = uuid.uuid4()
    log = await repo.record_audit_log(
        action="TEST_ACTION",
        resource="test_resource",
        user_id=user_id,
        resource_id=res_id,
        details={"foo": "bar"},
    )

    assert log.action == "TEST_ACTION"
    assert log.resource == "test_resource"
    assert log.user_id == user_id
    assert log.resource_id == res_id
    db.add.assert_called_once_with(log)
    db.flush.assert_awaited_once()
