"""
Unit tests for DocumentClassifier domain service.
"""

import pytest

from app.config.constants import DocumentType
from app.domain.services.document_classifier import DocumentClassifier
from app.domain.value_objects.classification_result import ClassificationResult


@pytest.fixture
def classifier() -> DocumentClassifier:
    return DocumentClassifier()


def test_classify_empty_or_short_text(classifier: DocumentClassifier) -> None:
    result = classifier.classify("")
    assert result.document_type == DocumentType.UNKNOWN
    assert result.confidence == 0.0
    assert not result.is_definitive
    assert len(result.reasons) > 0

    short_result = classifier.classify("Solo unas pocas palabras")
    assert short_result.document_type == DocumentType.UNKNOWN
    assert short_result.confidence == 0.0


def test_classify_non_cv_document(classifier: DocumentClassifier) -> None:
    invoice_text = (
        "FACTURA DE VENTA ELECTRÓNICA N° 98234\n"
        "EMPRESA COMERCIALIZADORA SAS\n"
        "NIT: 900.123.456-7\n"
        "CLIENTE: JUAN PEREZ\n"
        "DETALLE: SERVICIOS DE CONSULTORIA ENERO 2026\n"
        "SUBTOTAL: $5.000.000\n"
        "IVA 19%: $950.000\n"
        "TOTAL A PAGAR: $5.950.000\n"
        "GRACIAS POR SU COMPRA."
    )
    result = classifier.classify(invoice_text)
    assert result.document_type == DocumentType.UNKNOWN
    assert not result.is_definitive
    assert any("no corresponde a una hoja de vida" in r for r in result.reasons)


def test_classify_formato_unico_full_dafp(classifier: DocumentClassifier) -> None:
    fu_text = (
        "FORMATO ÚNICO DE HOJA DE VIDA\n"
        "PERSONA NATURAL\n"
        "REPÚBLICA DE COLOMBIA\n"
        "DEPARTAMENTO ADMINISTRATIVO DE LA FUNCIÓN PÚBLICA\n\n"
        "1. DATOS PERSONALES\n"
        "PRIMER APELLIDO: RODRÍGUEZ\n"
        "SEGUNDO APELLIDO: PÉREZ\n"
        "NOMBRES: CARLOS ALBERTO\n"
        "DOCUMENTO DE IDENTIFICACIÓN: C.C. 1.020.304.050\n"
        "LIBRETA MILITAR: NÚMERO 1020304050 CLASE PRIMERA\n"
        "PAÍS: COLOMBIA DEPARTAMENTO: CUNDINAMARCA MUNICIPIO: BOGOTÁ D.C.\n\n"
        "2. FORMACIÓN ACADÉMICA\n"
        "EDUCACIÓN BÁSICA Y MEDIA: TÍTULO OBTENIDO: BACHILLER ACADÉMICO\n"
        "EDUCACIÓN SUPERIOR: MODALIDAD: UNIVERSITARIA NOMBRE DE LA INSTITUCIÓN: UNIVERSIDAD NACIONAL\n"
        "TÍTULO: INGENIERO DE SISTEMAS\n\n"
        "3. EXPERIENCIA LABORAL\n"
        "EMPRESA O ENTIDAD: ALCALDÍA MAYOR DE BOGOTÁ\n"
        "CARGO O CONTRATO ACTUAL: ASESOR DE TECNOLOGÍA\n"
        "TIEMPO TOTAL DE EXPERIENCIA: 5 AÑOS, 3 MESES\n\n"
        "4. FIRMA DEL SERVIDOR PÚBLICO O CONTRATISTA\n"
    )
    result = classifier.classify(fu_text)
    assert result.document_type == DocumentType.FORMATO_UNICO
    assert result.confidence >= 0.85
    assert result.is_definitive
    assert "FORMATO UNICO DE HOJA DE VIDA" in result.matched_indicators
    assert "1. DATOS PERSONALES" in result.detected_sections or "DATOS PERSONALES" in result.detected_sections
    dict_repr = result.to_dict()
    assert dict_repr["document_type"] == "FORMATO_UNICO"
    assert "scores" in dict_repr


def test_classify_formato_unico_scanned_ocr_noise(classifier: DocumentClassifier) -> None:
    # Text without accents and slightly altered punctuation
    fu_noisy = (
        "HOJA DE VIDA PERSONA NATURAL DAFP\n"
        "DATOS BASICOS\n"
        "PRIMER APELLIDO GOMEZ SEGUNDO APELLIDO SUAREZ NOMBRES ANDRES FELIPE\n"
        "DOCUMENTO DE IDENTIFICACION CC 80123456\n"
        "LIBRETA MILITAR CLASE 1\n"
        "FORMACION ACADEMICA UNIVERSIDAD DE LOS ANDES INGENIERO INDUSTRIAL\n"
        "EXPERIENCIA LABORAL EMPRESA O ENTIDAD MINISTERIO DE HACIENDA\n"
        "CARGO O CONTRATO ACTUAL PROFESIONAL ESPECIALIZADO TIEMPO TOTAL DE EXPERIENCIA 8 ANOS\n"
        "FIRMA DEL SERVIDOR PUBLICO\n"
    )
    result = classifier.classify(fu_noisy)
    assert result.document_type == DocumentType.FORMATO_UNICO
    assert result.confidence >= 0.60
    assert result.is_definitive


def test_classify_ats_resume_spanish(classifier: DocumentClassifier) -> None:
    ats_text = (
        "MARÍA FERNANDA LÓPEZ OSORIO\n"
        "Email: maria.lopez@email.com | Teléfono: +57 310 987 6543 | Bogotá, Colombia\n"
        "LinkedIn: linkedin.com/in/mariaflopez | GitHub: github.com/mflopez\n\n"
        "PERFIL PROFESIONAL\n"
        "Ingeniera de software con más de 6 años de experiencia desarrollando aplicaciones web distribuidas "
        "y microservicios escalables utilizando Python, FastAPI, Docker y PostgreSQL.\n\n"
        "EXPERIENCIA LABORAL\n"
        "Desarrolladora Senior Backend — Globant Colombia (2021 - Presente)\n"
        "- Diseño de arquitecturas de microservicios para clientes de banca y seguros.\n"
        "- Optimización de pipelines de datos y consultas SQL complejas.\n\n"
        "EDUCACIÓN\n"
        "Pontificia Universidad Javeriana — Pregrado en Ingeniería de Sistemas (2014 - 2019)\n\n"
        "HABILIDADES TÉCNICAS\n"
        "Python, Django, FastAPI, TypeScript, React, Docker, Kubernetes, AWS, Git, CI/CD.\n\n"
        "IDIOMAS\n"
        "Español (Nativo), Inglés (Avanzado C1).\n"
    )
    result = classifier.classify(ats_text)
    assert result.document_type == DocumentType.ATS
    assert result.confidence >= 0.60
    assert result.is_definitive
    assert "CONTACT:EMAIL" in result.matched_indicators
    assert "EXPERIENCE" in result.detected_sections
    assert "EDUCATION" in result.detected_sections
    assert "SKILLS" in result.detected_sections


def test_classify_ats_resume_english(classifier: DocumentClassifier) -> None:
    ats_en = (
        "ALEXANDER J. MERCER\n"
        "alex.mercer@techcorp.io | +1 (555) 234-5678 | San Francisco, CA\n"
        "https://linkedin.com/in/alexmercer | https://github.com/alexmercer\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Results-oriented Lead Cloud Architect with 8+ years architecting enterprise SaaS solutions, "
        "specializing in Kubernetes orchestration, event-driven architectures, and high-throughput systems.\n\n"
        "WORK EXPERIENCE\n"
        "Senior Cloud Architect — Datadog Inc (2020 - Present)\n"
        "- Led migration of core telemetry platform to AWS multi-region infrastructure.\n"
        "- Reduced latency by 45% using gRPC and Redis caching layers.\n\n"
        "EDUCATION\n"
        "B.S. Computer Science — University of California, Berkeley (2012 - 2016)\n\n"
        "TECHNICAL SKILLS\n"
        "Go, Python, Terraform, Docker, Kubernetes, AWS, Prometheus, PostgreSQL, Kafka.\n\n"
        "CERTIFICATIONS\n"
        "AWS Certified Solutions Architect – Professional (2023)\n"
    )
    result = classifier.classify(ats_en)
    assert result.document_type == DocumentType.ATS
    assert result.confidence >= 0.60
    assert result.is_definitive
    assert "CONTACT:EMAIL" in result.matched_indicators
    assert "PROFILE_SUMMARY" in result.detected_sections


def test_classify_ambiguous_text_returns_unknown(classifier: DocumentClassifier) -> None:
    ambiguous_text = (
        "Este es un texto descriptivo sobre la historia de la informática en América Latina. "
        "Durante las décadas de los setenta y ochenta surgieron diversos proyectos académicos "
        "y centros de cálculo en diversas universidades de la región. "
        "Sin embargo, no se presentan datos personales ni historiales de empleo aquí."
    )
    result = classifier.classify(ambiguous_text)
    assert result.document_type == DocumentType.UNKNOWN
    assert result.confidence < 0.50
    assert not result.is_definitive
    assert len(result.reasons) > 0
