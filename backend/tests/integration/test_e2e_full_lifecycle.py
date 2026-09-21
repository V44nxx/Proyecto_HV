"""
Full End-to-End (E2E) Integration Lifecycle Test:
Ingestion -> Classification -> Extraction -> Human Review ->
Search & Dossier -> Dashboard Metrics -> Institutional Reports -> Audit Trail.
"""

import io
import fitz
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.user_models import AuditLog

SAMPLE_E2E_CV_TEXT = """
FORMATO ÚNICO DE HOJA DE VIDA
PERSONA NATURAL
(Leyes 190 de 1995, 489 y 443 de 1998)

1. DATOS PERSONALES
PRIMER APELLIDO: ECHEVERRI  SEGUNDO APELLIDO: MEJIA  NOMBRES: DANIELA
DOCUMENTO DE IDENTIFICACIÓN: C.C. No. 1017234567  PAÍS: COLOMBIA
DIRECCIÓN: CALLE 10 # 40-20  PAÍS: COLOMBIA  DEPTO: ANTIOQUIA  MUNICIPIO: MEDELLIN
TELÉFONO: 6044445566  CORREO ELECTRÓNICO: daniela.echeverri@test.gov.co

2. FORMACIÓN ACADÉMICA
MODALIDAD ACADÉMICA: UNIVERSITARIA
NO. SEMESTRES APROBADOS: 10  GRADUADO: SI
NOMBRE DE LOS ESTUDIOS O TÍTULO OBTENIDO: INGENIERO DE SISTEMAS
INSTITUCIÓN: UNIVERSIDAD DE ANTIOQUIA
FECHA DE TERMINACIÓN: 11/2019

3. EXPERIENCIA LABORAL
EMPRESA O ENTIDAD: ALCALDÍA DE MEDELLÍN  PÚBLICA: SI  PRIVADA: NO
PAÍS: COLOMBIA  DEPARTAMENTO: ANTIOQUIA  MUNICIPIO: MEDELLIN
CARGO O CONTRATO ACTUAL: LIDER DE DESARROLLO DE SOFTWARE
FECHA DE INGRESO: 01/02/2020  FECHA DE RETIRO: 15/12/2023
"""


def _make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_full_platform_lifecycle_e2e(
    integration_client: AsyncClient,
    test_db: AsyncSession,
) -> None:
    # -------------------------------------------------------------------------
    # STEP 1: Upload Document
    # -------------------------------------------------------------------------
    pdf_bytes = _make_pdf(SAMPLE_E2E_CV_TEXT)
    files = {"file": ("cv_daniela_echeverri.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_resp = await integration_client.post("/api/v1/documents", files=files)
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["document"]["id"]
    job_id = doc_data["job"]["id"]
    assert doc_id is not None
    assert doc_data["job"]["status"] == "UPLOADED"

    # -------------------------------------------------------------------------
    # STEP 2: Classify Document
    # -------------------------------------------------------------------------
    classify_resp = await integration_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert classify_resp.status_code == 200
    class_data = classify_resp.json()
    assert class_data["document_type"] == "FORMATO_UNICO"
    assert class_data["confidence"] >= 0.70

    # -------------------------------------------------------------------------
    # STEP 3: Extract Formato Único Data
    # -------------------------------------------------------------------------
    extract_resp = await integration_client.post(f"/api/v1/documents/{doc_id}/extract-formato-unico")
    assert extract_resp.status_code == 200
    ext_data = extract_resp.json()
    person_id = ext_data["person_id"]
    assert person_id is not None
    assert ext_data["person"]["first_name"] == "DANIELA"
    assert ext_data["person"]["first_surname"] == "ECHEVERRI"
    assert ext_data["person"]["identification_number"] == "1017234567"

    # -------------------------------------------------------------------------
    # STEP 4: Human Review Workflow
    # -------------------------------------------------------------------------
    fields_resp = await integration_client.get(f"/api/v1/documents/{doc_id}/review-fields")
    assert fields_resp.status_code == 200
    fields = fields_resp.json()
    assert len(fields) >= 1

    # Accept first field
    first_field_id = fields[0]["id"]
    accept_resp = await integration_client.post(
        f"/api/v1/documents/{doc_id}/review-fields/{first_field_id}/accept",
        json={"notes": "Campo validado conforme a documento original."},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["review_status"] == "ACCEPTED"

    # Finalize document review
    finalize_resp = await integration_client.post(
        f"/api/v1/documents/{doc_id}/finalize-review",
        json={"notes": "Revision humana formalmente concluida sin observaciones."},
    )
    assert finalize_resp.status_code == 200
    assert finalize_resp.json()["status"] == "COMPLETED"

    # -------------------------------------------------------------------------
    # STEP 5: Search Engine Queries
    # -------------------------------------------------------------------------
    # Free-text search
    search_q = await integration_client.get("/api/v1/search/candidates?q=Daniela")
    assert search_q.status_code == 200
    assert search_q.json()["total"] >= 1
    assert any(c["id"] == person_id for c in search_q.json()["items"])

    # Municipality search
    search_mun = await integration_client.get("/api/v1/search/candidates?municipality=Medellin")
    assert search_mun.status_code == 200
    assert search_mun.json()["total"] >= 1

    # -------------------------------------------------------------------------
    # STEP 6: Candidate Dossier & Page Traceability
    # -------------------------------------------------------------------------
    detail_resp = await integration_client.get(f"/api/v1/search/candidates/{person_id}")
    assert detail_resp.status_code == 200
    dossier = detail_resp.json()
    assert dossier["id"] == person_id
    assert dossier["first_name"] == "DANIELA"
    assert dossier["first_surname"] == "ECHEVERRI"
    assert dossier["contact"] is not None
    assert dossier["contact"]["municipality"] == "MEDELLIN"
    assert len(dossier["educations"]) >= 1
    assert len(dossier["work_experiences"]) >= 1

    # -------------------------------------------------------------------------
    # STEP 7: Analytics Dashboard Overview
    # -------------------------------------------------------------------------
    dash_resp = await integration_client.get("/api/v1/dashboard/overview")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["kpis"]["total_documents"] >= 1
    assert dash_data["kpis"]["total_persons"] >= 1
    assert dash_data["kpis"]["processed_documents"] >= 1

    # -------------------------------------------------------------------------
    # STEP 8: Institutional Reports Generation & Streaming
    # -------------------------------------------------------------------------
    # Preview
    preview_resp = await integration_client.post(
        "/api/v1/reports/preview",
        json={"report_type": "INVENTORY", "filters": {}},
    )
    assert preview_resp.status_code == 200
    assert preview_resp.json()["total_records"] >= 1
    assert len(preview_resp.json()["rows"]) >= 1

    # Excel export
    excel_resp = await integration_client.post(
        "/api/v1/reports/export",
        json={"report_type": "INVENTORY", "report_format": "EXCEL", "filters": {}},
    )
    assert excel_resp.status_code == 200
    assert "application/vnd.openxmlformats" in excel_resp.headers["content-type"]
    assert len(excel_resp.content) > 1000

    # PDF export
    pdf_resp = await integration_client.post(
        "/api/v1/reports/export",
        json={"report_type": "INVENTORY", "report_format": "PDF", "filters": {}},
    )
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["content-type"]
    assert len(pdf_resp.content) > 1000

    # -------------------------------------------------------------------------
    # STEP 9: Audit Trail Integrity Verification
    # -------------------------------------------------------------------------
    audit_stmt = select(AuditLog).order_by(AuditLog.created_at.asc())
    audit_rows = (await test_db.execute(audit_stmt)).scalars().all()
    actions = [row.action for row in audit_rows]

    # Verify upload, extraction, review and report export were all recorded
    assert any("UPLOAD" in act or "DOCUMENT" in act for act in actions)
    assert any("REPORT" in act for act in actions)
