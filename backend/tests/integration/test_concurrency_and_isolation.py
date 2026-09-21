"""
Integration tests for Concurrency, Soft-Delete Isolation, and Edge Pagination:
- Concurrent uploads and extractions via asyncio.gather
- Soft-delete isolation: deleted documents disappear from listings and queries
- Out-of-bounds pagination handling
"""

import asyncio
import io
import fitz
import pytest
from httpx import AsyncClient


def _make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_concurrent_document_uploads(integration_client: AsyncClient):
    """
    Simulates concurrent uploads to test for race conditions and DB connection locking.
    """
    async def upload_one(index: int):
        cv_text = f"""
        FORMATO ÚNICO DE HOJA DE VIDA
        1. DATOS PERSONALES
        PRIMER APELLIDO: USUARIO_{index}  SEGUNDO APELLIDO: TEST
        NOMBRES: CANDIDATO_{index}
        DOCUMENTO DE IDENTIFICACIÓN: C.C. No. {90000000 + index}
        PAÍS: COLOMBIA
        """
        pdf_bytes = _make_pdf(cv_text)
        files = {"file": (f"cv_concurrente_{index}.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        return await integration_client.post("/api/v1/documents", files=files)

    # Launch 5 concurrent uploads
    responses = await asyncio.gather(*(upload_one(i) for i in range(5)))

    assert all(r.status_code == 201 for r in responses)
    doc_ids = [r.json()["document"]["id"] for r in responses]
    # Verify all doc IDs are unique
    assert len(set(doc_ids)) == 5


@pytest.mark.asyncio
async def test_soft_delete_isolation(integration_client: AsyncClient):
    """
    Validates that soft-deleted documents are strictly excluded from lists and queries.
    """
    pdf_bytes = _make_pdf("Documento para prueba de aislamiento por eliminacion logica.")
    files = {"file": ("doc_para_borrar.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # 1. Upload
    up_resp = await integration_client.post("/api/v1/documents", files=files)
    assert up_resp.status_code == 201
    doc_id = up_resp.json()["document"]["id"]

    # Verify present in list
    list_before = await integration_client.get("/api/v1/documents")
    assert list_before.status_code == 200
    assert any(d["id"] == doc_id for d in list_before.json()["items"])

    # 2. Soft-delete
    del_resp = await integration_client.delete(f"/api/v1/documents/{doc_id}")
    assert del_resp.status_code in (200, 204)

    # 3. Verify single get returns 404
    get_after = await integration_client.get(f"/api/v1/documents/{doc_id}")
    assert get_after.status_code == 404

    # 4. Verify excluded from listings
    list_after = await integration_client.get("/api/v1/documents")
    assert list_after.status_code == 200
    assert not any(d["id"] == doc_id for d in list_after.json()["items"])


@pytest.mark.asyncio
async def test_pagination_out_of_bounds_resilience(integration_client: AsyncClient):
    """
    Validates that requesting a page far beyond existing results returns an empty list gracefully.
    """
    resp = await integration_client.get("/api/v1/search/candidates?page=9999&page_size=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["page"] == 9999
