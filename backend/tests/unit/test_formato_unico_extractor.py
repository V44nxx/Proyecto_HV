"""
Unit tests for FormatoUnicoExtractor and FormatoUnicoExtractionStep.
"""

from datetime import date
import uuid
import pytest

from app.application.interfaces.ocr_provider import OCRDocumentResult, OCRPageResult
from app.config.constants import DocumentType
from app.infrastructure.extraction.formato_unico_extractor import FormatoUnicoExtractor
from app.infrastructure.extraction.formato_unico_step import FormatoUnicoExtractionStep
from app.infrastructure.extraction.pipeline_context import ProcessingContext

FU_FULL_SAMPLE = (
    "FORMATO ÚNICO DE HOJA DE VIDA\n"
    "PERSONA NATURAL\n"
    "REPÚBLICA DE COLOMBIA\n"
    "DEPARTAMENTO ADMINISTRATIVO DE LA FUNCIÓN PÚBLICA\n\n"
    "1. DATOS PERSONALES\n"
    "PRIMER APELLIDO: RODRIGUEZ\n"
    "SEGUNDO APELLIDO: PEREZ\n"
    "NOMBRES: CARLOS ALBERTO\n"
    "DOCUMENTO DE IDENTIFICACIÓN: C.C. 1.020.304.050\n"
    "SEXO: MASCULINO NACIONALIDAD: COLOMBIANA\n"
    "PAÍS: COLOMBIA DEPARTAMENTO: CUNDINAMARCA MUNICIPIO: BOGOTA\n"
    "FECHA DE NACIMIENTO: 15/04/1988\n"
    "LIBRETA MILITAR: NÚMERO 1020304050 DISTRITO: 48 CLASE: PRIMERA\n"
    "DIRECCIÓN: CALLE 100 # 15-20 APTO 402\n"
    "MUNICIPIO: BOGOTA TELÉFONO: +57 300 987 6543\n"
    "CORREO ELECTRÓNICO: carlos.rodriguez@email.gov.co\n\n"
    "2. FORMACIÓN ACADÉMICA\n"
    "EDUCACIÓN BÁSICA Y MEDIA: TÍTULO OBTENIDO: BACHILLER ACADÉMICO\n"
    "EDUCACIÓN SUPERIOR (PREGRADO Y POSTGRADO)\n"
    "MODALIDAD ACADÉMICA: UNIVERSITARIA NO. SEMESTRES: 10 GRADUADO: SÍ\n"
    "NOMBRE DE LA INSTITUCIÓN: UNIVERSIDAD NACIONAL DE COLOMBIA\n"
    "TÍTULO O PROGRAMA ACADÉMICO: INGENIERO DE SISTEMAS\n"
    "FECHA DE GRADO: AÑO: 2012 MES: 6\n"
    "TARJETA PROFESIONAL: NÚMERO 2598471\n\n"
    "IDIOMAS: INGLÉS HABLA: BIEN LEE: BIEN ESCRIBE: BIEN\n\n"
    "3. EXPERIENCIA LABORAL\n"
    "EMPRESA O ENTIDAD: ALCALDÍA MAYOR DE BOGOTÁ\n"
    "PÚBLICA PAÍS: COLOMBIA DEPARTAMENTO: CUNDINAMARCA MUNICIPIO: BOGOTÁ\n"
    "CARGO O CONTRATO ACTUAL: ASESOR DE TECNOLOGÍA DEPENDENCIA: SECRETARÍA GENERAL\n"
    "FECHA DE INGRESO: 01/02/2018 FECHA DE RETIRO: 31/12/2022\n\n"
    "EMPRESA O ENTIDAD: BANCO DE BOGOTÁ\n"
    "PRIVADA PAÍS: COLOMBIA MUNICIPIO: BOGOTÁ\n"
    "CARGO O CONTRATO ACTUAL: DESARROLLADOR SENIOR\n"
    "FECHA DE INGRESO: 15/01/2013 FECHA DE RETIRO: 15/01/2018\n\n"
    "4. TIEMPO TOTAL DE EXPERIENCIA\n"
    "SERVIDOR PÚBLICO: 4 AÑOS, 11 MESES\n"
    "SECTOR PRIVADO: 5 AÑOS, 0 MESES\n"
    "TIEMPO TOTAL DE EXPERIENCIA: 9 AÑOS, 11 MESES\n"
)


def test_formato_unico_extractor_parses_all_sections() -> None:
    extractor = FormatoUnicoExtractor()
    resume = extractor.extract(FU_FULL_SAMPLE)

    # 1. Person
    assert resume.person.first_surname == "RODRIGUEZ"
    assert resume.person.second_surname == "PEREZ"
    assert resume.person.first_name == "CARLOS"
    assert resume.person.middle_name == "ALBERTO"
    assert resume.person.full_name == "CARLOS ALBERTO RODRIGUEZ PEREZ"
    assert resume.person.identification_number == "1020304050"
    assert resume.person.identification_type == "CC"
    assert resume.person.sex == "MASCULINO"
    assert resume.person.birth_date == date(1988, 4, 15)
    assert resume.person.military_card_number == "1020304050"
    assert resume.person.military_card_class == "PRIMERA"

    # 2. Contact
    assert resume.contact.email == "carlos.rodriguez@email.gov.co"
    assert "+57 300 987 6543" in str(resume.contact.telephone)
    assert "CALLE 100" in str(resume.contact.address)

    # 3. Educations
    assert len(resume.educations) >= 2
    high_school = [e for e in resume.educations if e.level == "HIGH_SCHOOL"]
    assert len(high_school) == 1
    assert "BACHILLER" in high_school[0].degree_title.upper()

    undergrad = [e for e in resume.educations if e.level == "UNDERGRADUATE"]
    assert len(undergrad) == 1
    assert "INGENIERO DE SISTEMAS" in undergrad[0].degree_title.upper()
    assert "UNIVERSIDAD NACIONAL" in undergrad[0].institution.upper()
    assert undergrad[0].completion_year == 2012
    assert undergrad[0].completion_month == 6
    assert undergrad[0].professional_card_no == "2598471"

    # 4. Languages
    assert len(resume.languages) == 1
    assert resume.languages[0].language_name == "INGLES"

    # 5. Work Experience
    assert len(resume.work_experiences) == 2
    exp1 = resume.work_experiences[0]
    assert "ALCALDÍA" in exp1.company_name.upper()
    assert exp1.sector == "PUBLIC"
    assert "ASESOR" in exp1.position.upper()
    assert exp1.start_date == date(2018, 2, 1)
    assert exp1.end_date == date(2022, 12, 31)

    exp2 = resume.work_experiences[1]
    assert "BANCO DE BOGOTÁ" in exp2.company_name.upper()
    assert exp2.sector == "PRIVATE"
    assert exp2.start_date == date(2013, 1, 15)

    # 6. Summary
    assert resume.experience_summary is not None
    assert resume.experience_summary.public_years == 4
    assert resume.experience_summary.private_years == 5
    assert resume.experience_summary.total_years == 9

    # 7. Traceability fields
    assert len(resume.extracted_fields) >= 4
    field_names = [f.field_name for f in resume.extracted_fields]
    assert "first_surname" in field_names
    assert "identification_number" in field_names
    assert "email" in field_names


def test_parse_date_variations() -> None:
    assert FormatoUnicoExtractor.parse_date("25/12/2020") == date(2020, 12, 25)
    assert FormatoUnicoExtractor.parse_date("2021-05-10") == date(2021, 5, 10)
    assert FormatoUnicoExtractor.parse_date("15 de Mayo de 1995") == date(1995, 5, 15)
    assert FormatoUnicoExtractor.parse_date("Invalid date text") is None
    assert FormatoUnicoExtractor.parse_date("") is None


@pytest.mark.asyncio
async def test_formato_unico_step_skips_non_fu() -> None:
    step = FormatoUnicoExtractionStep()
    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=b"%PDF-test",
        document_type=DocumentType.ATS,
    )
    result_ctx = await step.execute(ctx)
    assert result_ctx.canonical_resume == {}


@pytest.mark.asyncio
async def test_formato_unico_step_executes_fu() -> None:
    step = FormatoUnicoExtractionStep()
    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=b"%PDF-test",
        document_type=DocumentType.FORMATO_UNICO,
        ocr_result=OCRDocumentResult(
            provider="MOCK",
            pages=[OCRPageResult(page_number=1, full_text=FU_FULL_SAMPLE)],
        ),
    )
    result_ctx = await step.execute(ctx)
    assert result_ctx.canonical_resume != {}
    assert result_ctx.canonical_resume["person"]["identification_number"] == "1020304050"
    assert result_ctx.canonical_resume["metadata"]["source_format"] == "FORMATO_UNICO_DAFP"


def test_formato_unico_extractor_empty_text() -> None:
    extractor = FormatoUnicoExtractor()
    resume = extractor.extract("")
    assert resume.person.full_name == ""
    assert resume.person.first_name is None
    assert resume.educations == []
    assert resume.work_experiences == []
    assert resume.languages == []
    assert resume.extracted_fields == []


def test_canonical_resume_to_dict() -> None:
    extractor = FormatoUnicoExtractor()
    resume = extractor.extract(FU_FULL_SAMPLE)
    d = resume.to_dict()
    assert isinstance(d, dict)
    assert d["person"]["first_name"] == "CARLOS"
    assert d["contact"]["email"] == "carlos.rodriguez@email.gov.co"
    assert len(d["educations"]) >= 2
    assert len(d["work_experiences"]) == 2
    assert len(d["languages"]) == 1
    assert d["experience_summary"]["total_years"] == 9

