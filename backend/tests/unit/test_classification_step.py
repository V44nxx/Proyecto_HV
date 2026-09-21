"""
Unit tests for DocumentClassificationStep pipeline step.
"""

import uuid
import fitz
import pytest

from app.application.interfaces.ocr_provider import OCRDocumentResult, OCRPageResult
from app.config.constants import DocumentType, JobStatus
from app.infrastructure.extraction.document_classification_step import DocumentClassificationStep
from app.infrastructure.extraction.pipeline_context import ProcessingContext


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_classification_step_with_ocr_result_fu() -> None:
    step = DocumentClassificationStep()
    fu_text = (
        "FORMATO ÚNICO DE HOJA DE VIDA PERSONA NATURAL DAFP\n"
        "1. DATOS PERSONALES\n"
        "PRIMER APELLIDO: MARTINEZ SEGUNDO APELLIDO: CASTRO NOMBRES: DIANA\n"
        "DOCUMENTO DE IDENTIFICACION CC 52123456\n"
        "2. FORMACION ACADEMICA UNIVERSITARIA\n"
        "3. EXPERIENCIA LABORAL EMPRESA O ENTIDAD ICBF\n"
        "FIRMA DEL SERVIDOR PUBLICO\n"
    )

    page_res = OCRPageResult(
        page_number=1,
        full_text=fu_text,
        tokens=[],
        confidence=0.98,
        width_pts=595.0,
        height_pts=842.0,
    )
    doc_res = OCRDocumentResult(
        provider="MOCK",
        pages=[page_res],
        model_version="1.0.0",
        processing_ms=10,
    )

    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=b"%PDF-mock",
        ocr_result=doc_res,
    )

    result_ctx = await step.execute(ctx)
    assert result_ctx.document_type == DocumentType.FORMATO_UNICO
    assert result_ctx.confidence_score >= 0.80
    assert "classification" in result_ctx.metadata
    assert result_ctx.current_step == "document_classification"


@pytest.mark.asyncio
async def test_classification_step_with_pdf_bytes_ats() -> None:
    step = DocumentClassificationStep()
    ats_text = (
        "ANDRES FELIPE HERRERA\n"
        "andres.herrera@techmail.co | +57 300 123 4567 | Bogota\n"
        "PERFIL PROFESIONAL\n"
        "Desarrollador fullstack con 5 anos de experiencia en Python y React.\n"
        "EXPERIENCIA LABORAL\n"
        "Tech Solutions SAS - Desarrollador Senior\n"
        "EDUCACION\n"
        "Universidad Nacional de Colombia - Ingenieria de Sistemas\n"
        "HABILIDADES\n"
        "Python, Docker, AWS, FastAPI, PostgreSQL\n"
    )
    pdf_bytes = make_pdf(ats_text)

    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=pdf_bytes,
        ocr_result=None,
    )

    result_ctx = await step.execute(ctx)
    assert result_ctx.document_type == DocumentType.ATS
    assert result_ctx.confidence_score >= 0.55
    assert result_ctx.current_step == "document_classification"


@pytest.mark.asyncio
async def test_classification_step_unknown_sets_review_required() -> None:
    step = DocumentClassificationStep()
    unknown_text = (
        "FACTURA DE VENTA N° 1023\n"
        "TOTAL A PAGAR: $100.000 COP\n"
        "FECHA DE VENCIMIENTO: 2026-10-15\n"
        "GRACIAS POR SU PAGO EN LINEA.\n"
    )
    pdf_bytes = make_pdf(unknown_text)

    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=pdf_bytes,
        ocr_result=None,
    )

    result_ctx = await step.execute(ctx)
    assert result_ctx.document_type == DocumentType.UNKNOWN
    assert result_ctx.status == JobStatus.REVIEW_REQUIRED
    assert result_ctx.error_type == "UNKNOWN_DOCUMENT_TYPE"
