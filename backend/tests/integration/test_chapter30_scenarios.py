"""
Integration tests for the 10 mandatory scenarios specified in Chapter 30:
1. Valid Formato Único
2. Valid ATS
3. Poor-quality PDF
4. PDF with no text (scanned pages triggering OCR)
5. Unsupported file format
6. Corrupted PDF
7. Duplicate document (SHA-256 deduplication)
8. Missing fields (graceful partial extraction)
9. Low-confidence OCR result
10. Low-confidence / Unknown document classification
"""

import io
import fitz
import pytest
from httpx import AsyncClient

# Sample realistic texts
SAMPLE_FORMATO_UNICO_TEXT = """
FORMATO ÚNICO DE HOJA DE VIDA
PERSONA NATURAL
(Leyes 190 de 1995, 489 y 443 de 1998)

1. DATOS PERSONALES
PRIMER APELLIDO: RODRIGUEZ  SEGUNDO APELLIDO: PEREZ  NOMBRES: JORGE ANDRES
DOCUMENTO DE IDENTIFICACIÓN: C.C. No. 71987654  PAÍS: COLOMBIA
SEXO: M  NACIONALIDAD: COLOMBIANA
DIRECCIÓN: CALLE 45 # 12-34  PAÍS: COLOMBIA  DEPTO: ANTIOQUIA  MUNICIPIO: MEDELLIN
TELÉFONO: 6041234567  CORREO ELECTRÓNICO: jorge.rodriguez@example.com

2. FORMACIÓN ACADÉMICA
EDUCACIÓN BÁSICA Y MEDIA:
TITULO OBTENIDO: BACHILLER ACADEMICO  FECHA DE GRADO: 12/2010

EDUCACIÓN SUPERIOR (PREGRADO Y POSTGRADO):
MODALIDAD ACADÉMICA: UNIVERSITARIA
NO. SEMESTRES APROBADOS: 10  GRADUADO: SI
NOMBRE DE LOS ESTUDIOS O TÍTULO OBTENIDO: INGENIERO CIVIL
INSTITUCIÓN: UNIVERSIDAD NACIONAL DE COLOMBIA
FECHA DE TERMINACIÓN: 06/2016  NO. TARJETA PROFESIONAL: 052431

3. EXPERIENCIA LABORAL
EMPRESA O ENTIDAD: CONSTRUCTORA ANDINA S.A.S.  PÚBLICA: NO  PRIVADA: SI
PAÍS: COLOMBIA  DEPARTAMENTO: ANTIOQUIA  MUNICIPIO: MEDELLIN
CORREO ELECTRÓNICO ENTIDAD: contacto@andina.com  TELÉFONOS: 6049876543
CARGO O CONTRATO ACTUAL: INGENIERO DE PROYECTOS
DEPENDENCIA: GERENCIA DE OBRAS
DIRECCIÓN: CARRERA 50 # 30-20
FECHA DE INGRESO: 01/08/2018  FECHA DE RETIRO: 30/11/2022

4. TIEMPO TOTAL DE EXPERIENCIA
TOTAL TIEMPO EXPERIENCIA:
OCUPACIÓN O CARGO: INGENIERO CIVIL  AÑOS: 4  MESES: 4
"""

SAMPLE_ATS_TEXT = """
MARIA LOPEZ
Bogota, Colombia | Tel: +57 315 987 6543 | maria.lopez@devmail.com | linkedin.com/in/marialopez

RESUMEN PROFESIONAL
Ingeniera de Sistemas con 6 anos de experiencia en desarrollo backend con Python y microservicios.
Especializada en FastAPI, PostgreSQL y arquitectura en la nube.

HABILIDADES TECNICAS
Python, FastAPI, Docker, PostgreSQL, Redis, PyTorch, Git, Linux, REST APIs

EXPERIENCIA LABORAL
Senior Software Engineer | SoftSolutions Inc.
Bogota, Colombia | 01/2021 - Presente
- Diseno e implementacion de servicios REST de alta disponibilidad.
- Optimizacion de consultas SQL reduciendo latencia en 40%.

Backend Developer | TechCorp Colombia
Medellin, Colombia | 03/2018 - 12/2020
- Desarrollo de APIs empresariales y pipelines de datos.

EDUCACION
Ingenieria de Sistemas | Universidad de los Andes | 2013 - 2017
Bogota, Colombia

IDIOMAS
Espanol: Nativo
Ingles: C1 Avanzado
"""


def _create_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# -----------------------------------------------------------------------------
# 1. Valid Formato Único
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_1_valid_formato_unico(integration_client: AsyncClient):
    pdf_bytes = _create_pdf(SAMPLE_FORMATO_UNICO_TEXT)
    files = {"file": ("formato_unico_jorge.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # Upload
    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    # Classify
    resp_class = await integration_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert resp_class.status_code == 200
    assert resp_class.json()["document_type"] == "FORMATO_UNICO"

    # Extract
    resp_ext = await integration_client.post(f"/api/v1/documents/{doc_id}/extract-formato-unico")
    assert resp_ext.status_code == 200
    ext_data = resp_ext.json()
    assert ext_data["person"]["first_name"] == "JORGE"
    assert ext_data["person"]["first_surname"] == "RODRIGUEZ"
    assert ext_data["person"]["identification_number"] == "71987654"
    assert len(ext_data["educations"]) >= 1
    assert len(ext_data["work_experiences"]) >= 1


# -----------------------------------------------------------------------------
# 2. Valid ATS
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_2_valid_ats(integration_client: AsyncClient):
    pdf_bytes = _create_pdf(SAMPLE_ATS_TEXT)
    files = {"file": ("ats_maria_lopez.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    resp_class = await integration_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert resp_class.status_code == 200
    assert resp_class.json()["document_type"] == "ATS"

    resp_ext = await integration_client.post(f"/api/v1/documents/{doc_id}/extract-ats")
    assert resp_ext.status_code == 200
    ext_data = resp_ext.json()
    assert ext_data["person"]["first_name"] == "MARIA"
    assert ext_data["person"]["first_surname"] == "LOPEZ"
    assert len(ext_data["educations"]) >= 1
    assert len(ext_data["work_experiences"]) >= 1


# -----------------------------------------------------------------------------
# 3. Poor-Quality PDF
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_3_poor_quality_pdf(integration_client: AsyncClient):
    # Simulated degraded scan text
    degraded_text = """
    FORMAT0 UN1C0 D3 H0JA DE V1DA
    1. DAT0S P3RS0NAL3S
    PR1MER AP3LL1D0: G0MEZ   N0MBR3: C4RL0S
    D0CUM3NT0: 12345678
    """
    pdf_bytes = _create_pdf(degraded_text)
    files = {"file": ("scan_degradado.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    # Low-confidence classification or text processing still proceeds gracefully
    resp_proc = await integration_client.post(f"/api/v1/documents/{doc_id}/process-text")
    assert resp_proc.status_code == 200


# -----------------------------------------------------------------------------
# 4. PDF with No Text (Scanned Image)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_4_pdf_with_no_text(integration_client: AsyncClient):
    # Create empty graphical page with no text
    doc = fitz.open()
    doc.new_page()  # Blank page
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("scanned_blank.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    # Process text: step detects page has_text=False and invokes OCR provider
    resp_proc = await integration_client.post(f"/api/v1/documents/{doc_id}/process-text")
    assert resp_proc.status_code == 200
    assert resp_proc.json()["pages_count"] >= 1


# -----------------------------------------------------------------------------
# 5. Unsupported File
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_5_unsupported_file(integration_client: AsyncClient):
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {"file": ("malicious.exe", io.BytesIO(fake_exe), "application/x-msdownload")}

    resp = await integration_client.post("/api/v1/documents", files=files)
    assert resp.status_code == 400
    assert "no permitido" in resp.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 6. Corrupted PDF
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_6_corrupted_pdf(integration_client: AsyncClient):
    corrupt_bytes = b"%PDF-1.4\n%corrupted_data_without_trailer_or_xref\n%%EOF"
    files = {"file": ("corrupted.pdf", io.BytesIO(corrupt_bytes), "application/pdf")}

    resp = await integration_client.post("/api/v1/documents", files=files)
    assert resp.status_code == 400


# -----------------------------------------------------------------------------
# 7. Duplicate Document (SHA-256 Deduplication)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_7_duplicate_document(integration_client: AsyncClient):
    pdf_bytes = _create_pdf("Documento unico para deduplicacion SHA-256")
    files_1 = {"file": ("doc_original.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    files_2 = {"file": ("doc_copia.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # First upload succeeds
    resp1 = await integration_client.post("/api/v1/documents", files=files_1)
    assert resp1.status_code == 201

    # Second upload with identical bytes must be rejected as duplicate (409 Conflict)
    resp2 = await integration_client.post("/api/v1/documents", files=files_2)
    assert resp2.status_code == 409
    assert "subido al sistema previamente" in str(resp2.json()["detail"]).lower()


# -----------------------------------------------------------------------------
# 8. Missing Fields (Tolerant Partial Extraction)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_8_missing_fields(integration_client: AsyncClient):
    minimal_fu = """
    FORMATO ÚNICO DE HOJA DE VIDA
    1. DATOS PERSONALES
    PRIMER APELLIDO: ZAMBRANO  SEGUNDO APELLIDO:   NOMBRES: LUCIA
    DOCUMENTO DE IDENTIFICACIÓN: C.C. No. 55443322
    PAÍS: COLOMBIA
    """
    pdf_bytes = _create_pdf(minimal_fu)
    files = {"file": ("fu_incompleto.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    resp_ext = await integration_client.post(f"/api/v1/documents/{doc_id}/extract-formato-unico")
    assert resp_ext.status_code == 200
    person = resp_ext.json()["person"]
    assert person["first_name"] == "LUCIA"
    assert person["first_surname"] == "ZAMBRANO"
    assert person["second_surname"] is None  # Gracefully handled as None


# -----------------------------------------------------------------------------
# 9. Low Confidence Extraction & Review Transition
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_9_incorrect_ocr_low_confidence(integration_client: AsyncClient):
    unclear_cv = """
    ¿?%&$ #@!??
    Curriculum Vitae ???
    Uncertain name: ???
    """
    pdf_bytes = _create_pdf(unclear_cv)
    files = {"file": ("unclear_ocr.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    # Classifying ambiguous text
    resp_class = await integration_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert resp_class.status_code == 200
    data = resp_class.json()
    # If confidence is below threshold, it flags low confidence or requires review
    assert "confidence" in data
    assert "document_type" in data


# -----------------------------------------------------------------------------
# 10. Low Confidence / Unknown Document Classification
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_10_low_confidence_classification(integration_client: AsyncClient):
    unrelated_text = """
    FACTURA DE VENTA ELECTRÓNICA
    No. 99824
    CLIENTE: DISTRIBUIDORA NORTE
    CANTIDAD: 50 ARTÍCULOS
    TOTAL A PAGAR: $ 500.000 COP
    """
    pdf_bytes = _create_pdf(unrelated_text)
    files = {"file": ("factura.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    resp_up = await integration_client.post("/api/v1/documents", files=files)
    assert resp_up.status_code == 201
    doc_id = resp_up.json()["document"]["id"]

    resp_class = await integration_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert resp_class.status_code == 200
    assert resp_class.json()["document_type"] == "UNKNOWN"
