"""
Unit tests for Human-in-the-Loop review use cases:
- ListReviewFieldsUseCase
- ReviewFieldUseCase (accept, correct, reject, canonical propagation)
- BatchReviewFieldsUseCase
- GetReviewSummaryUseCase
- FinalizeDocumentReviewUseCase
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.application.use_cases.reviews import (
    BatchReviewFieldsUseCase,
    FinalizeDocumentReviewUseCase,
    GetReviewSummaryUseCase,
    ListReviewFieldsUseCase,
    ReviewFieldUseCase,
)
from app.config.constants import JobStatus, ReviewStatus
from app.infrastructure.database.models.document_models import (
    Document,
    ExtractedField,
    ProcessingJob,
)
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
)


@pytest.mark.asyncio
async def test_list_review_fields_document_not_found():
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = None
    review_repo = AsyncMock()

    use_case = ListReviewFieldsUseCase(
        document_repo=doc_repo,
        review_repo=review_repo,
    )

    with pytest.raises(DocumentNotFoundError):
        await use_case.execute(document_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_list_review_fields_success():
    doc_id = uuid.uuid4()
    mock_doc = Document(id=doc_id)
    mock_field = ExtractedField(
        id=uuid.uuid4(),
        extraction_id=uuid.uuid4(),
        field_name="first_name",
        raw_value="Juan",
        confidence=0.95,
        review_status=ReviewStatus.PENDING.value,
        page_number=1,
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    review_repo = AsyncMock()
    review_repo.get_fields_for_document.return_value = [mock_field]

    use_case = ListReviewFieldsUseCase(
        document_repo=doc_repo,
        review_repo=review_repo,
    )

    fields = await use_case.execute(
        document_id=doc_id,
        status_filter="PENDING",
        page_number=1,
    )

    assert len(fields) == 1
    assert fields[0].field_name == "first_name"
    review_repo.get_fields_for_document.assert_awaited_once_with(
        document_id=doc_id,
        status_filter="PENDING",
        page_number=1,
    )


@pytest.mark.asyncio
async def test_accept_field_document_not_found():
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = None
    person_repo = AsyncMock()
    review_repo = AsyncMock()

    use_case = ReviewFieldUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )

    with pytest.raises(DocumentNotFoundError):
        await use_case.accept_field(
            document_id=uuid.uuid4(),
            field_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_accept_field_field_not_found():
    doc_id = uuid.uuid4()
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = Document(id=doc_id)
    person_repo = AsyncMock()
    review_repo = AsyncMock()
    review_repo.get_field_by_id.return_value = None

    use_case = ReviewFieldUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )

    with pytest.raises(DocumentNotFoundError):
        await use_case.accept_field(
            document_id=doc_id,
            field_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_accept_field_success():
    doc_id = uuid.uuid4()
    field_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    mock_doc = Document(id=doc_id)
    mock_field = ExtractedField(
        id=field_id,
        extraction_id=uuid.uuid4(),
        field_name="email",
        raw_value="carlos@example.com",
        normalized_value="carlos@example.com",
        confidence=0.99,
        review_status=ReviewStatus.PENDING.value,
        page_number=1,
    )
    accepted_field = ExtractedField(
        id=field_id,
        extraction_id=mock_field.extraction_id,
        field_name="email",
        raw_value="carlos@example.com",
        confidence=0.99,
        review_status=ReviewStatus.ACCEPTED.value,
        page_number=1,
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    person_repo = AsyncMock()
    review_repo = AsyncMock()
    review_repo.get_field_by_id.return_value = mock_field
    review_repo.update_field_status.return_value = accepted_field

    use_case = ReviewFieldUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )

    result = await use_case.accept_field(
        document_id=doc_id,
        field_id=field_id,
        reviewer_id=reviewer_id,
    )

    assert result.review_status == ReviewStatus.ACCEPTED.value
    review_repo.update_field_status.assert_awaited_once_with(
        field_id=field_id,
        review_status=ReviewStatus.ACCEPTED.value,
        reviewer_id=reviewer_id,
    )
    review_repo.record_audit_log.assert_awaited_once_with(
        action="FIELD_ACCEPTED",
        resource="extracted_fields",
        user_id=reviewer_id,
        resource_id=field_id,
        details={
            "document_id": str(doc_id),
            "field_name": "email",
            "value": "carlos@example.com",
        },
    )


@pytest.mark.asyncio
async def test_correct_field_propagates_to_person():
    doc_id = uuid.uuid4()
    person_id = uuid.uuid4()
    field_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    mock_doc = Document(id=doc_id, person_id=person_id)
    mock_field = ExtractedField(
        id=field_id,
        extraction_id=uuid.uuid4(),
        field_name="first_name",
        raw_value="JON",
        confidence=0.75,
        review_status=ReviewStatus.PENDING.value,
        page_number=1,
    )
    corrected_field = ExtractedField(
        id=field_id,
        extraction_id=mock_field.extraction_id,
        field_name="first_name",
        raw_value="JON",
        corrected_value="JOHN",
        confidence=0.75,
        review_status=ReviewStatus.CORRECTED.value,
        page_number=1,
    )

    mock_person = Person(
        id=person_id,
        identification_type="CC",
        identification_number="12345",
        first_surname="DOE",
        first_name="JON",
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    person_repo = AsyncMock()
    person_repo.get_person_with_details.return_value = mock_person
    review_repo = AsyncMock()
    review_repo.get_field_by_id.return_value = mock_field
    review_repo.update_field_status.return_value = corrected_field

    use_case = ReviewFieldUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )

    result = await use_case.correct_field(
        document_id=doc_id,
        field_id=field_id,
        corrected_value="JOHN",
        note="Typo correction in first name",
        reviewer_id=reviewer_id,
    )

    assert result.review_status == ReviewStatus.CORRECTED.value
    assert result.corrected_value == "JOHN"
    # Verify entity mutation
    assert mock_person.first_name == "JOHN"
    review_repo.record_audit_log.assert_awaited_once_with(
        action="FIELD_CORRECTED",
        resource="extracted_fields",
        user_id=reviewer_id,
        resource_id=field_id,
        details={
            "document_id": str(doc_id),
            "field_name": "first_name",
            "original_value": "JON",
            "corrected_value": "JOHN",
            "note": "Typo correction in first name",
        },
    )


@pytest.mark.asyncio
async def test_correct_field_propagates_to_contact():
    doc_id = uuid.uuid4()
    person_id = uuid.uuid4()
    field_id = uuid.uuid4()

    mock_doc = Document(id=doc_id, person_id=person_id)
    mock_field = ExtractedField(
        id=field_id,
        extraction_id=uuid.uuid4(),
        field_name="email",
        raw_value="wrong@old.com",
        review_status=ReviewStatus.PENDING.value,
        page_number=1,
    )

    mock_contact = ContactInformation(
        id=uuid.uuid4(),
        person_id=person_id,
        email="wrong@old.com",
    )
    mock_person = Person(
        id=person_id,
        identification_type="CC",
        identification_number="12345",
        first_surname="DOE",
        first_name="JOHN",
        contact_information=mock_contact,
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    person_repo = AsyncMock()
    person_repo.get_person_with_details.return_value = mock_person
    review_repo = AsyncMock()
    review_repo.get_field_by_id.return_value = mock_field
    review_repo.update_field_status.return_value = mock_field

    use_case = ReviewFieldUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )

    await use_case.correct_field(
        document_id=doc_id,
        field_id=field_id,
        corrected_value="corrected@new.com",
    )

    assert mock_contact.email == "corrected@new.com"


@pytest.mark.asyncio
async def test_reject_field_success():
    doc_id = uuid.uuid4()
    field_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    mock_doc = Document(id=doc_id)
    mock_field = ExtractedField(
        id=field_id,
        extraction_id=uuid.uuid4(),
        field_name="unknown_text",
        raw_value="rubbish",
        review_status=ReviewStatus.PENDING.value,
        page_number=1,
    )
    rejected_field = ExtractedField(
        id=field_id,
        extraction_id=mock_field.extraction_id,
        field_name="unknown_text",
        raw_value="rubbish",
        review_status=ReviewStatus.REJECTED.value,
        page_number=1,
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    person_repo = AsyncMock()
    review_repo = AsyncMock()
    review_repo.get_field_by_id.return_value = mock_field
    review_repo.update_field_status.return_value = rejected_field

    use_case = ReviewFieldUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )

    result = await use_case.reject_field(
        document_id=doc_id,
        field_id=field_id,
        reason="No corresponde a un campo válido del candidato",
        reviewer_id=reviewer_id,
    )

    assert result.review_status == ReviewStatus.REJECTED.value
    review_repo.update_field_status.assert_awaited_once_with(
        field_id=field_id,
        review_status=ReviewStatus.REJECTED.value,
        correction_note="No corresponde a un campo válido del candidato",
        reviewer_id=reviewer_id,
    )
    review_repo.record_audit_log.assert_awaited_once_with(
        action="FIELD_REJECTED",
        resource="extracted_fields",
        user_id=reviewer_id,
        resource_id=field_id,
        details={
            "document_id": str(doc_id),
            "field_name": "unknown_text",
            "reason": "No corresponde a un campo válido del candidato",
        },
    )


@pytest.mark.asyncio
async def test_batch_review_fields_success():
    doc_id = uuid.uuid4()
    f1 = uuid.uuid4()
    f2 = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = Document(id=doc_id)
    review_repo = AsyncMock()
    review_repo.batch_update_status.return_value = 2

    use_case = BatchReviewFieldsUseCase(
        document_repo=doc_repo,
        review_repo=review_repo,
    )

    count = await use_case.execute(
        document_id=doc_id,
        field_ids=[f1, f2],
        action="ACCEPT",
        reviewer_id=reviewer_id,
    )

    assert count == 2
    review_repo.batch_update_status.assert_awaited_once_with(
        field_ids=[f1, f2],
        review_status=ReviewStatus.ACCEPTED.value,
        reviewer_id=reviewer_id,
    )
    review_repo.record_audit_log.assert_awaited_once_with(
        action="BATCH_FIELDS_REVIEWED",
        resource="extracted_fields",
        user_id=reviewer_id,
        resource_id=doc_id,
        details={
            "action": "ACCEPT",
            "fields_count": 2,
            "field_ids": [str(f1), str(f2)],
        },
    )


@pytest.mark.asyncio
async def test_get_review_summary_success():
    doc_id = uuid.uuid4()
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = Document(id=doc_id)
    review_repo = AsyncMock()
    review_repo.get_review_summary.return_value = {
        "total_fields": 10,
        "pending_count": 2,
        "accepted_count": 6,
        "corrected_count": 2,
        "rejected_count": 0,
        "completion_pct": 80.0,
        "is_complete": False,
    }

    use_case = GetReviewSummaryUseCase(
        document_repo=doc_repo,
        review_repo=review_repo,
    )

    res = await use_case.execute(document_id=doc_id)
    assert res["document_id"] == doc_id
    assert res["completion_pct"] == 80.0
    assert res["is_complete"] is False


@pytest.mark.asyncio
async def test_finalize_review_with_job():
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    mock_doc = Document(id=doc_id)
    mock_job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        status=JobStatus.PROCESSING.value,
        progress_pct=80,
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    doc_repo.get_latest_job_for_document.return_value = mock_job
    review_repo = AsyncMock()

    use_case = FinalizeDocumentReviewUseCase(
        document_repo=doc_repo,
        review_repo=review_repo,
    )

    result = await use_case.execute(
        document_id=doc_id,
        reviewer_id=reviewer_id,
    )

    assert result["document_id"] == doc_id
    assert result["status"] == JobStatus.COMPLETED.value
    doc_repo.update_processing_job.assert_awaited_once_with(
        job_id=job_id,
        status=JobStatus.COMPLETED.value,
        current_step="review_completed",
        progress_pct=100,
    )
    review_repo.record_audit_log.assert_awaited_once()
