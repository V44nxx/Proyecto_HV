"""
Unit tests for AtsResumeExtractor and AtsExtractionStep.
"""

from datetime import date
import uuid
import pytest

from app.application.interfaces.ocr_provider import OCRDocumentResult, OCRPageResult
from app.config.constants import DocumentType
from app.infrastructure.extraction.ats_extractor import AtsResumeExtractor
from app.infrastructure.extraction.ats_extraction_step import AtsExtractionStep
from app.infrastructure.extraction.pipeline_context import ProcessingContext

ATS_SPANISH_SAMPLE = """
MARIA FERNANDA LOPEZ RAMIREZ
Ingeniera de Sistemas | Backend & Cloud
Email: maria.lopez@techcorp.com | Tel: +57 312 456 7890
Bogotá, Colombia
https://www.linkedin.com/in/marialopez | https://github.com/marialopez
C.C. 52.894.120

PERFIL PROFESIONAL
Ingeniera de software con más de 6 años de experiencia desarrollando aplicaciones distribuidas y microservicios escalables de alta disponibilidad en la nube.

EXPERIENCIA LABORAL
TechCorp Solutions - Senior Backend Engineer
Ene 2021 - Presente
- Arquitectura de microservicios utilizando FastAPI, Python y PostgreSQL.
- Despliegue de infraestructura como código con Docker y AWS ECS.
- Liderazgo técnico de equipo ágil bajo metodología Scrum.

Startup Innovate - Desarrollador Fullstack
02/2018 - 12/2020
- Creación de plataformas web interactivas con React, TypeScript y Node.js.
- Optimización de consultas SQL y caché con Redis.

EDUCACIÓN
Ingeniera de Sistemas
Universidad de los Andes
Año de grado: 2017

HABILIDADES TÉCNICAS
Python, FastAPI, Docker, AWS, PostgreSQL, Redis, React, TypeScript, Git, Scrum, Linux

IDIOMAS
Español: Nativo
Inglés: Avanzado (C1)

CERTIFICACIONES
AWS Certified Solutions Architect - 2022
Scrum Master Certified - 2020
"""

ATS_ENGLISH_SAMPLE = """
DAVID MICHAEL SMITH
Cloud Architect & Distributed Systems Engineer
Email: david.smith@cloudsystems.io | Phone: +1 (555) 234-5678
New York, USA
linkedin.com/in/davidsmith | github.com/davidsmith

SUMMARY
Passionate software architect with extensive expertise in cloud computing, container orchestration, and high-performance distributed systems.

WORK EXPERIENCE
CloudSystems Inc - Lead Cloud Architect
March 2020 - Present
- Designed multi-region Kubernetes clusters on GCP and AWS.
- Implemented automated CI/CD pipelines with GitHub Actions.
- Mentored junior engineers in Golang and cloud architecture best practices.

FinTech Global - Software Engineer
2016 - 2020
- Developed resilient transaction processing APIs in Go and Java.
- Maintained PostgreSQL and MongoDB databases under heavy financial workloads.

EDUCATION
Bachelor of Science in Computer Science
MIT - Massachusetts Institute of Technology
Graduation: 2016

SKILLS
Go, Python, Java, Kubernetes, Docker, Terraform, GCP, AWS, PostgreSQL, MongoDB, CI/CD, Microservices

LANGUAGES
English: Native
French: Intermediate (B2)

CERTIFICATIONS
Google Cloud Certified Professional Cloud Architect - 2021
"""


def test_ats_extractor_spanish_sample():
    extractor = AtsResumeExtractor()
    resume = extractor.extract(ATS_SPANISH_SAMPLE)

    # 1. Person & Contact
    assert resume.person.first_name == "MARIA"
    assert resume.person.middle_name == "FERNANDA"
    assert resume.person.first_surname == "LOPEZ"
    assert resume.person.second_surname == "RAMIREZ"
    assert resume.person.identification_number == "52894120"
    assert resume.contact.email == "maria.lopez@techcorp.com"
    assert "+57 312 456 7890" in str(resume.contact.telephone)
    assert resume.contact.municipality == "Bogotá"
    assert resume.contact.country == "Colombia"

    # 2. Metadata / Summary
    assert "summary" in resume.metadata
    assert "6 años de experiencia" in resume.metadata["summary"]

    # 3. Work Experience
    assert len(resume.work_experiences) == 2
    exp1 = resume.work_experiences[0]
    assert "TechCorp Solutions" in exp1.company_name
    assert exp1.is_current is True
    assert exp1.start_date == date(2021, 1, 1)
    assert exp1.end_date is None
    assert "FastAPI" in exp1.responsibilities

    exp2 = resume.work_experiences[1]
    assert "Startup Innovate" in exp2.company_name
    assert exp2.is_current is False
    assert exp2.start_date == date(2018, 2, 1)
    assert exp2.end_date == date(2020, 12, 1)

    # 4. Education
    assert len(resume.educations) >= 1
    edu = resume.educations[0]
    assert "Ingeniera de Sistemas" in edu.degree_title
    assert "Universidad de los Andes" in edu.institution
    assert edu.completion_year == 2017
    assert edu.level == "UNDERGRADUATE"

    # 5. Skills
    skills = resume.metadata.get("skills", [])
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "PostgreSQL" in skills

    # 6. Languages
    assert len(resume.languages) >= 2
    lang_names = [l.language_name for l in resume.languages]
    assert "ESPAÑOL" in lang_names
    assert "INGLES" in lang_names

    # 7. URLs & Certifications
    urls = resume.metadata.get("professional_urls", [])
    assert any("linkedin.com/in/marialopez" in u for u in urls)
    certs = resume.metadata.get("certifications", [])
    assert any("AWS Certified Solutions Architect" in c["name"] for c in certs)

    # 8. Field Traceability
    field_names = [f.field_name for f in resume.extracted_fields]
    assert "full_name" in field_names
    assert "email" in field_names
    assert "telephone" in field_names


def test_ats_extractor_english_sample():
    extractor = AtsResumeExtractor()
    resume = extractor.extract(ATS_ENGLISH_SAMPLE)

    assert resume.person.first_name == "DAVID"
    assert resume.contact.email == "david.smith@cloudsystems.io"
    assert len(resume.work_experiences) == 2
    assert resume.work_experiences[0].is_current is True
    assert resume.work_experiences[0].start_date == date(2020, 3, 1)

    assert len(resume.educations) >= 1
    assert "Computer Science" in resume.educations[0].degree_title
    assert resume.educations[0].completion_year == 2016

    skills = resume.metadata.get("skills", [])
    assert "Kubernetes" in skills
    assert "Terraform" in skills

    lang_names = [l.language_name for l in resume.languages]
    assert "INGLES" in lang_names
    assert "FRANCES" in lang_names


def test_ats_extractor_empty_and_short_text():
    extractor = AtsResumeExtractor()
    resume_empty = extractor.extract("")
    assert resume_empty.person.first_name is None
    assert resume_empty.work_experiences == []
    assert resume_empty.educations == []
    assert resume_empty.metadata["source_format"] == "ATS"

    resume_short = extractor.extract("Solo una línea sin datos estructurados")
    assert resume_short.person.first_name is None


@pytest.mark.asyncio
async def test_ats_extraction_step_skips_non_ats():
    step = AtsExtractionStep()
    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=b"%PDF-test",
        document_type=DocumentType.FORMATO_UNICO,
    )
    result_ctx = await step.execute(ctx)
    assert result_ctx.canonical_resume == {}


@pytest.mark.asyncio
async def test_ats_extraction_step_executes_ats():
    step = AtsExtractionStep()
    ctx = ProcessingContext(
        document_id=uuid.uuid4(),
        pdf_bytes=b"%PDF-test",
        document_type=DocumentType.ATS,
        ocr_result=OCRDocumentResult(
            provider="MOCK",
            pages=[OCRPageResult(page_number=1, full_text=ATS_SPANISH_SAMPLE)],
        ),
    )
    result_ctx = await step.execute(ctx)
    assert result_ctx.canonical_resume != {}
    assert result_ctx.canonical_resume["person"]["first_name"] == "MARIA"
    assert result_ctx.canonical_resume["metadata"]["source_format"] == "ATS"
    assert result_ctx.metadata["skills_count"] > 0
