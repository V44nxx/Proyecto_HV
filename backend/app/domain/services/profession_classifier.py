"""
Profession and category classification domain service.

Classifies degrees, professional titles, and work positions into standardized
canonical categories and professions using resilient semantic and heuristic matching.
Does not depend on external databases or network services (pure domain service).
"""

import re
from typing import Any
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ProfessionMatch:
    """Classification result for a candidate's profession."""
    category_name: str
    profession_name: str
    confidence: float
    matched_keyword: str | None = None


# Canonical taxonomy definition: Category -> list of (Profession, Aliases/Keywords)
TAXONOMY: dict[str, list[dict[str, Any]]] = {
    "Ingeniería y Tecnología": [
        {
            "profession": "Ingeniería de Sistemas y Computación",
            "aliases": [
                "sistemas", "computacion", "software", "informatica", "computer science",
                "desarrollador", "developer", "devops", "cloud", "full stack", "backend",
                "frontend", "datos", "data engineer", "data scientist", "arquitecto de software",
                "programador", "ingeniero de software", "systems engineer", "ti",
            ],
        },
        {
            "profession": "Ingeniería Electrónica y Telecomunicaciones",
            "aliases": [
                "electronica", "telecomunicaciones", "redes", "electronico", "electronic engineer",
                "telecom", "fibra optica", "hardware", "iot", "circuitos",
            ],
        },
        {
            "profession": "Ingeniería Civil",
            "aliases": [
                "civil", "estructuras", "obras civiles", "vias", "transporte", "geotecnia",
                "construccion", "hidraulica", "civil engineer",
            ],
        },
        {
            "profession": "Ingeniería Industrial",
            "aliases": [
                "industrial", "procesos", "operaciones", "logistica", "calidad", "supply chain",
                "produccion", "mejora continua", "industrial engineer",
            ],
        },
        {
            "profession": "Ingeniería Mecánica y Mecatrónica",
            "aliases": [
                "mecanica", "mecatronica", "mecanico", "mecatronico", "mantenimiento industrial",
                "termodinamica", "automatizacion", "robotica", "mechanical engineer",
            ],
        },
        {
            "profession": "Ingeniería Eléctrica",
            "aliases": [
                "electrica", "electricista", "alta tension", "subestaciones", "energia",
                "potencia electrica", "electrical engineer",
            ],
        },
        {
            "profession": "Ingeniería Ambiental y Sanitaria",
            "aliases": [
                "ambiental", "sanitaria", "recursos naturales", "sostenibilidad",
                "gestion ambiental", "environmental engineer",
            ],
        },
        {
            "profession": "Ingeniería Química",
            "aliases": [
                "quimica", "quimico", "procesos quimicos", "petroquimica", "chemical engineer",
            ],
        },
        {
            "profession": "Ingeniería Biomédica",
            "aliases": [
                "biomedica", "biomedico", "bioingenieria", "equipos medicos", "biomedical",
            ],
        },
    ],
    "Ciencias de la Salud": [
        {
            "profession": "Medicina General y Especialidades",
            "aliases": [
                "medicina", "medico", "medica", "cirujano", "doctor", "clinica", "pediatria",
                "urgencias", "terapia intensiva", "physician", "doctor of medicine",
            ],
        },
        {
            "profession": "Enfermería",
            "aliases": [
                "enfermeria", "enfermero", "enfermera", "cuidados intensivos", "nurse", "nursing",
            ],
        },
        {
            "profession": "Odontología",
            "aliases": [
                "odontologia", "odontologo", "odontologa", "dentista", "salud oral", "dentistry",
            ],
        },
        {
            "profession": "Fisioterapia y Terapia Física",
            "aliases": [
                "fisioterapia", "fisioterapeuta", "terapia fisica", "rehabilitacion", "kinesiologia",
            ],
        },
        {
            "profession": "Bacteriología y Microbiología",
            "aliases": [
                "bacteriologia", "bacteriologo", "microbiologia", "microbiologo", "laboratorio clinico",
            ],
        },
        {
            "profession": "Nutrición y Dietética",
            "aliases": [
                "nutricion", "dietetica", "nutricionista", "dietista", "alimentacion",
            ],
        },
    ],
    "Ciencias Económicas y Administrativas": [
        {
            "profession": "Administración de Empresas",
            "aliases": [
                "administracion", "administrador", "gestion empresarial", "business administration",
                "gerencia", "management", "recursos humanos", "talento humano",
            ],
        },
        {
            "profession": "Contaduría Pública",
            "aliases": [
                "contaduria", "contador", "contabilidad", "auditoria", "revisoria fiscal",
                "tributaria", "accountant", "cpa",
            ],
        },
        {
            "profession": "Economía",
            "aliases": [
                "economia", "economista", "analisis economico", "macroeconomia", "economist",
            ],
        },
        {
            "profession": "Mercadeo y Publicidad",
            "aliases": [
                "mercadeo", "marketing", "publicidad", "ventas", "growth", "comercial",
                "brand manager", "publicista",
            ],
        },
        {
            "profession": "Negocios Internacionales",
            "aliases": [
                "negocios internacionales", "comercio exterior", "comercio internacional",
                "aduanas", "international business",
            ],
        },
    ],
    "Ciencias Sociales y Humanidades": [
        {
            "profession": "Psicología",
            "aliases": [
                "psicologia", "psicologo", "psicologa", "psicoterapia", "psicologia clinica",
                "psicologia organizacional", "psychologist", "psychology",
            ],
        },
        {
            "profession": "Trabajo Social",
            "aliases": [
                "trabajo social", "trabajador social", "trabajadora social", "desarrollo comunitario",
            ],
        },
        {
            "profession": "Comunicación Social y Periodismo",
            "aliases": [
                "comunicacion social", "periodismo", "periodista", "comunicador", "relaciones publicas",
                "comunicacion corporativa", "redactor",
            ],
        },
        {
            "profession": "Sociología y Antropología",
            "aliases": [
                "sociologia", "sociologo", "antropologia", "antropologo",
            ],
        },
        {
            "profession": "Filosofía e Historia",
            "aliases": [
                "filosofia", "filosofo", "historia", "historiador", "humanidades",
            ],
        },
    ],
    "Derecho y Ciencias Políticas": [
        {
            "profession": "Derecho y Abogacía",
            "aliases": [
                "derecho", "abogado", "abogada", "juridico", "legal", "jurista", "penal",
                "laboral", "civil y comercial", "litigante", "lawyer", "attorney",
            ],
        },
        {
            "profession": "Ciencias Políticas y Gobierno",
            "aliases": [
                "ciencias politicas", "politologo", "politologa", "relaciones internacionales",
                "politicas publicas", "gobierno",
            ],
        },
    ],
    "Ciencias de la Educación": [
        {
            "profession": "Licenciatura y Pedagogía",
            "aliases": [
                "licenciatura", "licenciado", "licenciada", "pedagogia", "docencia", "docente",
                "profesor", "profesora", "maestro", "maestra", "educador", "educacion infantil",
            ],
        },
    ],
    "Arquitectura, Diseño y Artes": [
        {
            "profession": "Arquitectura y Urbanismo",
            "aliases": [
                "arquitectura", "arquitecto", "arquitecta", "urbanismo", "diseño arquitectonico",
                "architect",
            ],
        },
        {
            "profession": "Diseño Gráfico y Visual",
            "aliases": [
                "diseño grafico", "diseñador grafico", "disenador", "ui/ux", "ux/ui", "multimedia",
                "ilustrador", "animacion", "graphic design",
            ],
        },
        {
            "profession": "Diseño Industrial",
            "aliases": [
                "diseño industrial", "diseñador industrial", "diseño de producto", "modelado 3d",
            ],
        },
    ],
}


class ProfessionClassifier:
    """
    Normalizes candidate titles, degrees, or positions to standardized
    categories and professions.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """Removes diacritics, punctuation and converts to lowercase."""
        if not text:
            return ""
        # Normalize unicode and strip accents
        nfd = unicodedata.normalize("NFKD", text)
        clean = "".join(c for c in nfd if not unicodedata.combining(c))
        clean = clean.lower()
        # Replace non-alphanumeric with space
        clean = re.sub(r"[^\w\s]", " ", clean)
        # Collapse multiple spaces
        return re.sub(r"\s+", " ", clean).strip()

    @classmethod
    def classify(
        cls,
        texts: list[str | None],
    ) -> ProfessionMatch:
        """
        Takes candidate title strings (e.g. degrees, programs, positions, summaries),
        matches against the canonical taxonomy, and returns the highest confidence match.
        """
        best_match: ProfessionMatch | None = None
        best_score = 0.0

        for raw_text in texts:
            if not raw_text:
                continue

            norm_input = cls.normalize_text(raw_text)
            if not norm_input:
                continue

            for category, professions in TAXONOMY.items():
                for prof_data in professions:
                    prof_name = prof_data["profession"]
                    norm_prof = cls.normalize_text(prof_name)

                    # 1. Exact match with profession name
                    if norm_prof == norm_input:
                        return ProfessionMatch(
                            category_name=category,
                            profession_name=prof_name,
                            confidence=1.0,
                            matched_keyword=prof_name,
                        )

                    # 2. Check aliases
                    for alias in prof_data["aliases"]:
                        norm_alias = cls.normalize_text(alias)
                        if not norm_alias:
                            continue

                        # Word boundary regex search
                        pattern = rf"\b{re.escape(norm_alias)}\b"
                        if re.search(pattern, norm_input):
                            # Calculate score based on length of alias relative to input
                            alias_len = len(norm_alias.split())
                            score = 0.85 if alias_len >= 2 else 0.75

                            if score > best_score:
                                best_score = score
                                best_match = ProfessionMatch(
                                    category_name=category,
                                    profession_name=prof_name,
                                    confidence=score,
                                    matched_keyword=alias,
                                )

        if best_match and best_match.confidence >= 0.6:
            return best_match

        return ProfessionMatch(
            category_name="Otras Áreas",
            profession_name="Profesión No Clasificada",
            confidence=0.0,
            matched_keyword=None,
        )
