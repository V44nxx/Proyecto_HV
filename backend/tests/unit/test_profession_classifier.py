"""
Unit tests for ProfessionClassifier domain service.
"""

import pytest
from app.domain.services.profession_classifier import (
    ProfessionClassifier,
    ProfessionMatch,
)


def test_normalize_text():
    assert ProfessionClassifier.normalize_text("Ingeniería de Software!") == "ingenieria de software"
    assert ProfessionClassifier.normalize_text("  MÉDICO CIRUJANO  ") == "medico cirujano"
    assert ProfessionClassifier.normalize_text("") == ""
    assert ProfessionClassifier.normalize_text(None) == ""


def test_classify_exact_matches():
    match = ProfessionClassifier.classify(["Ingeniería de Sistemas y Computación"])
    assert match.category_name == "Ingeniería y Tecnología"
    assert match.profession_name == "Ingeniería de Sistemas y Computación"
    assert match.confidence == 1.0


def test_classify_alias_devops_developer():
    match = ProfessionClassifier.classify(["Senior DevOps Engineer & Cloud Architect"])
    assert match.category_name == "Ingeniería y Tecnología"
    assert match.profession_name == "Ingeniería de Sistemas y Computación"
    assert match.confidence >= 0.75

    match2 = ProfessionClassifier.classify(["Desarrollador Full Stack Python React"])
    assert match2.category_name == "Ingeniería y Tecnología"
    assert match2.profession_name == "Ingeniería de Sistemas y Computación"


def test_classify_health_sciences():
    match = ProfessionClassifier.classify(["Médico Cirujano General"])
    assert match.category_name == "Ciencias de la Salud"
    assert match.profession_name == "Medicina General y Especialidades"
    assert match.confidence >= 0.75

    match_nurse = ProfessionClassifier.classify(["Enfermero Jefe de Unidad de Cuidados Intensivos"])
    assert match_nurse.category_name == "Ciencias de la Salud"
    assert match_nurse.profession_name == "Enfermería"


def test_classify_law():
    match = ProfessionClassifier.classify(["Abogado Especialista en Derecho Administrativo"])
    assert match.category_name == "Derecho y Ciencias Políticas"
    assert match.profession_name == "Derecho y Abogacía"


def test_classify_psychology():
    match = ProfessionClassifier.classify(["Psicólogo Organizacional y de Gestión Humana"])
    assert match.category_name == "Ciencias Sociales y Humanidades"
    assert match.profession_name == "Psicología"


def test_classify_administration_and_accounting():
    match_adm = ProfessionClassifier.classify(["Administrador de Empresas"])
    assert match_adm.category_name == "Ciencias Económicas y Administrativas"
    assert match_adm.profession_name == "Administración de Empresas"

    match_cpa = ProfessionClassifier.classify(["Contador Público Titulado"])
    assert match_cpa.category_name == "Ciencias Económicas y Administrativas"
    assert match_cpa.profession_name == "Contaduría Pública"


def test_classify_education():
    match = ProfessionClassifier.classify(["Licenciado en Pedagogía Infantil"])
    assert match.category_name == "Ciencias de la Educación"
    assert match.profession_name == "Licenciatura y Pedagogía"


def test_classify_architecture():
    match = ProfessionClassifier.classify(["Arquitecto Constructor y Urbanista"])
    assert match.category_name == "Arquitectura, Diseño y Artes"
    assert match.profession_name == "Arquitectura y Urbanismo"


def test_classify_unknown():
    match = ProfessionClassifier.classify(["Atronauta Cuántico Interdimensional 123"])
    assert match.category_name == "Otras Áreas"
    assert match.profession_name == "Profesión No Clasificada"
    assert match.confidence == 0.0
    assert match.matched_keyword is None


def test_classify_empty_or_none():
    match = ProfessionClassifier.classify([None, "", "   "])
    assert match.category_name == "Otras Áreas"
    assert match.confidence == 0.0
