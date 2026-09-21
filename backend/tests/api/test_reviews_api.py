"""
API integration tests for Human-in-the-Loop review endpoints:
- GET  /api/v1/documents/{id}/review-fields
- GET  /api/v1/documents/{id}/review-summary
- POST /api/v1/documents/{id}/review-fields/{field_id}/accept
- POST /api/v1/documents/{id}/review-fields/{field_id}/correct
- POST /api/v1/documents/{id}/review-fields/{field_id}/reject
- POST /api/v1/documents/{id}/review-fields/batch
- POST /api/v1/documents/{id}/finalize-review
"""

import io
import uuid
import fitz
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db_session
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_application
from app.presentation.dependencies.auth import (
    AuthenticatedUser,
    get_current_user,
)
from app.presentation.dependencies.document_dependencies import (
    get_ocr,
    get_storage,
)

SAMPLE_CV_TEXT = """
FERNANDO JOSE GOMEZ PEREZ
Senior Software Architect
Email: fernando.gomez@enterprisearch.com | Tel: +57 311 987 6543
Bogotá, Colombia
C.C. 80123456

PERFIL PROFESIONAL
Arquitecto de software empresarial con 10 años de experiencia diseñando plataformas escalables y seguras en la nube.

EXPERIENCIA LABORAL
Global Consulting SAS - Principal Cloud Architect
2019 - Presente
- Liderazgo de equipos de arquitectura en AWS y GCP.

EDUCACIÓN
Ingeniero de Sistemas
Universidad Nacional de Colombia
Año: 2013

HABILIDADES TÉCNICAS
Python, Go, FastAPI, Kubernetes, Docker, PostgreSQL
"""


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture
async def review_api_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    app.dependency_overrides[get_db_session] = lambda: test_db

    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    reviewer_uuid = str(uuid.uuid4())
    test_user = AuthenticatedUser(
        user_id=reviewer_uuid,
        role="GESTOR",
        permissions=["documents:read", "documents:write"],
        jti="review-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_full_human_review_workflow(review_api_client: AsyncClient) -> None:
    # 1. Upload document and extract ATS fields
    pdf_bytes = make_pdf(SAMPLE_CV_TEXT)
    upload_resp = await review_api_client.post(
        "/api/v1/documents",
        files={"file": ("cv_fernando_gomez.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    extract_resp = await review_api_client.post(f"/api/v1/documents/{doc_id}/extract-ats")
    assert extract_resp.status_code == 200

    # 2. GET /documents/{doc_id}/review-fields
    fields_resp = await review_api_client.get(f"/api/v1/documents/{doc_id}/review-fields")
    assert fields_resp.status_code == 200
    fields = fields_resp.json()
    assert len(fields) > 0
    assert all(f["review_status"] == "PENDING" for f in fields)

    # 3. GET /documents/{doc_id}/review-summary initially
    summary_resp = await review_api_client.get(f"/api/v1/documents/{doc_id}/review-summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["document_id"] == doc_id
    assert summary["total_fields"] == len(fields)
    assert summary["pending_count"] == len(fields)
    assert summary["accepted_count"] == 0
    assert summary["corrected_count"] == 0
    assert summary["rejected_count"] == 0
    assert summary["completion_pct"] == 0.0
    assert summary["is_complete"] is False

    # 4. Accept the first field
    field_to_accept = fields[0]
    accept_resp = await review_api_client.post(
        f"/api/v1/documents/{doc_id}/review-fields/{field_to_accept['id']}/accept"
    )
    assert accept_resp.status_code == 200
    acc_data = accept_resp.json()
    assert acc_data["id"] == field_to_accept["id"]
    assert acc_data["review_status"] == "ACCEPTED"
    assert acc_data["corrected_by"] is not None

    # 5. Correct the second field (e.g. first_name)
    field_to_correct = fields[1]
    correct_resp = await review_api_client.post(
        f"/api/v1/documents/{doc_id}/review-fields/{field_to_correct['id']}/correct",
        json={"corrected_value": "FERNANDO CORREGIDO", "note": "Validado con documento oficial"},
    )
    assert correct_resp.status_code == 200
    corr_data = correct_resp.json()
    assert corr_data["id"] == field_to_correct["id"]
    assert corr_data["review_status"] == "CORRECTED"
    assert corr_data["corrected_value"] == "FERNANDO CORREGIDO"
    assert corr_data["correction_note"] == "Validado con documento oficial"

    # 6. Reject the third field (if available)
    if len(fields) > 2:
        field_to_reject = fields[2]
        reject_resp = await review_api_client.post(
            f"/api/v1/documents/{doc_id}/review-fields/{field_to_reject['id']}/reject",
            json={"reason": "Dato no relevante o mal interpretado por OCR"},
        )
        assert reject_resp.status_code == 200
        rej_data = reject_resp.json()
        assert rej_data["id"] == field_to_reject["id"]
        assert rej_data["review_status"] == "REJECTED"
        assert rej_data["correction_note"] == "Dato no relevante o mal interpretado por OCR"

    # 7. Batch accept remaining pending fields
    remaining_fields = fields[3:]
    if remaining_fields:
        rem_ids = [f["id"] for f in remaining_fields]
        batch_resp = await review_api_client.post(
            f"/api/v1/documents/{doc_id}/review-fields/batch",
            json={"field_ids": rem_ids, "action": "ACCEPT"},
        )
        assert batch_resp.status_code == 200
        assert batch_resp.json()["updated_count"] == len(rem_ids)

    # 8. Check review summary after all are reviewed
    summary_resp2 = await review_api_client.get(f"/api/v1/documents/{doc_id}/review-summary")
    assert summary_resp2.status_code == 200
    summary2 = summary_resp2.json()
    assert summary2["pending_count"] == 0
    assert summary2["completion_pct"] == 100.0
    assert summary2["is_complete"] is True

    # 9. Finalize review
    finalize_resp = await review_api_client.post(f"/api/v1/documents/{doc_id}/finalize-review")
    assert finalize_resp.status_code == 200
    fin_data = finalize_resp.json()
    assert fin_data["document_id"] == doc_id
    assert fin_data["status"] == "COMPLETED"
    assert "exitosamente" in fin_data["message"]

    # 10. Check that processing job is COMPLETED at 100%
    doc_resp = await review_api_client.get(f"/api/v1/documents/{doc_id}")
    assert doc_resp.status_code == 200
    doc_data = doc_resp.json()
    assert doc_data["latest_job"] is not None
    assert doc_data["latest_job"]["status"] == "COMPLETED"
    assert doc_data["latest_job"]["progress_pct"] == 100


@pytest.mark.asyncio
async def test_review_endpoints_not_found(review_api_client: AsyncClient) -> None:
    fake_doc_id = uuid.uuid4()
    fake_field_id = uuid.uuid4()

    # List fields 404
    resp = await review_api_client.get(f"/api/v1/documents/{fake_doc_id}/review-fields")
    assert resp.status_code == 404

    # Summary 404
    resp = await review_api_client.get(f"/api/v1/documents/{fake_doc_id}/review-summary")
    assert resp.status_code == 404

    # Accept 404 doc
    resp = await review_api_client.post(
        f"/api/v1/documents/{fake_doc_id}/review-fields/{fake_field_id}/accept"
    )
    assert resp.status_code == 404

    # Correct 404 doc
    resp = await review_api_client.post(
        f"/api/v1/documents/{fake_doc_id}/review-fields/{fake_field_id}/correct",
        json={"corrected_value": "Nuevo Valor"},
    )
    assert resp.status_code == 404

    # Reject 404 doc
    resp = await review_api_client.post(
        f"/api/v1/documents/{fake_doc_id}/review-fields/{fake_field_id}/reject",
        json={"reason": "Error"},
    )
    assert resp.status_code == 404

    # Batch 404 doc
    resp = await review_api_client.post(
        f"/api/v1/documents/{fake_doc_id}/review-fields/batch",
        json={"field_ids": [str(fake_field_id)], "action": "ACCEPT"},
    )
    assert resp.status_code == 404

    # Finalize 404 doc
    resp = await review_api_client.post(f"/api/v1/documents/{fake_doc_id}/finalize-review")
    assert resp.status_code == 404
