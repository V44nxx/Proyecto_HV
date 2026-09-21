"""
Document classifier domain service.

Classifies incoming resume documents into:
- FORMATO_UNICO: Colombian DAFP standard government resume format.
- ATS: Freeform / ATS-compliant professional resume.
- UNKNOWN: Document not recognized as a supported resume type.
"""

import re
import unicodedata
from typing import Any

from app.config.constants import DocumentType
from app.domain.value_objects.classification_result import ClassificationResult


class DocumentClassifier:
    """
    Pure domain service for document classification.
    Evaluates text structure, key phrases, section headers, and patterns.
    """

    MIN_CONFIDENCE_THRESHOLD = 0.50
    MIN_TEXT_LENGTH = 80

    # ------------------------------------------------------------
    # Formato Único (DAFP) Signatures
    # ------------------------------------------------------------
    FU_HEADER_SIGNATURES = [
        "FORMATO UNICO DE HOJA DE VIDA",
        "DEPARTAMENTO ADMINISTRATIVO DE LA FUNCION PUBLICA",
        "HOJA DE VIDA PERSONA NATURAL",
        "HOJA DE VIDA - PERSONA NATURAL",
        "REPUBLICA DE COLOMBIA",
    ]

    FU_SECTION_SIGNATURES = [
        "DATOS PERSONALES",
        "DATOS BASICOS",
        "FORMACION ACADEMICA",
        "EDUCACION BASICA Y MEDIA",
        "EDUCACION SUPERIOR",
        "EXPERIENCIA LABORAL",
        "TIEMPO TOTAL DE EXPERIENCIA",
        "FIRMA DEL SERVIDOR PUBLICO",
        "OBSERVACIONES DEL JEFE DE PERSONAL",
    ]

    FU_FIELD_SIGNATURES = [
        "PRIMER APELLIDO",
        "SEGUNDO APELLIDO",
        "DOCUMENTO DE IDENTIFICACION",
        "LIBRETA MILITAR",
        "EMPRESA O ENTIDAD",
        "CARGO O CONTRATO ACTUAL",
        "PAIS",
        "DEPARTAMENTO",
        "MUNICIPIO",
    ]

    # ------------------------------------------------------------
    # ATS / Traditional CV Signatures
    # ------------------------------------------------------------
    ATS_PROFILE_SIGNATURES = [
        "PERFIL PROFESIONAL",
        "RESUMEN PROFESIONAL",
        "SOBRE MI",
        "ACERCA DE MI",
        "EXTRACTO",
        "PROFESSIONAL SUMMARY",
        "SUMMARY",
        "ABOUT ME",
        "PROFILE",
    ]

    ATS_EXPERIENCE_SIGNATURES = [
        "EXPERIENCIA LABORAL",
        "EXPERIENCIA PROFESIONAL",
        "HISTORIAL LABORAL",
        "TRAYECTORIA PROFESIONAL",
        "WORK EXPERIENCE",
        "PROFESSIONAL EXPERIENCE",
        "EMPLOYMENT HISTORY",
        "RELEVANT EXPERIENCE",
    ]

    ATS_EDUCATION_SIGNATURES = [
        "EDUCACION",
        "FORMACION ACADEMICA",
        "FORMACION",
        "ESTUDIOS",
        "EDUCATION",
        "ACADEMIC BACKGROUND",
    ]

    ATS_SKILLS_SIGNATURES = [
        "HABILIDADES",
        "COMPETENCIAS",
        "HABILIDADES TECNICAS",
        "TECNOLOGIAS",
        "HERRAMIENTAS",
        "CONOCIMIENTOS",
        "SKILLS",
        "TECHNICAL SKILLS",
        "CORE COMPETENCIES",
        "STACK TECNOLOGICO",
    ]

    ATS_MISC_SIGNATURES = [
        "IDIOMAS",
        "LANGUAGES",
        "CERTIFICACIONES",
        "CERTIFICATIONS",
        "CURSOS",
        "COURSES",
        "PROYECTOS",
        "PROJECTS",
        "LOGROS",
        "ACHIEVEMENTS",
    ]

    # Non-CV Disqualifiers
    NON_CV_SIGNATURES = [
        "FACTURA DE VENTA",
        "CUENTA DE COBRO",
        "TOTAL A PAGAR",
        "SUBTOTAL",
        "CONTRATO DE ARRENDAMIENTO",
        "CONTRATO DE COMPRAVENTA",
        "TERMINOS Y CONDICIONES",
        "POLITICA DE PRIVACIDAD",
    ]

    # Contact Info Regex Patterns
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
    URL_REGEX = re.compile(r"(?:https?://)?(?:www\.)?(?:linkedin\.com/in/|github\.com/|[a-zA-Z0-9-]+\.dev|[a-zA-Z0-9-]+\.io)", re.IGNORECASE)

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalize text: remove diacritics/accents, convert to uppercase,
        and standardize whitespace.
        """
        if not text:
            return ""
        # Decompose Unicode characters and drop non-spacing combining marks (diacritics)
        nfd = unicodedata.normalize("NFD", text)
        clean = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        # Collapse multiple whitespaces and trim
        return re.sub(r"\s+", " ", clean.upper()).strip()

    def evaluate_formato_unico(self, normalized_text: str) -> tuple[float, list[str], list[str]]:
        """
        Evaluate likelihood of document being a DAFP Formato Único.
        Returns: (score, matched_indicators, detected_sections)
        """
        matched: list[str] = []
        sections: list[str] = []
        score = 0.0

        # 1. Primary Headers (Weight up to 0.45)
        header_matches = [h for h in self.FU_HEADER_SIGNATURES if h in normalized_text]
        if header_matches:
            matched.extend(header_matches)
            # Having 1 header gives 0.35, 2 or more gives 0.45
            score += 0.35 if len(header_matches) == 1 else 0.45

        # 2. Canonical Sections (Weight up to 0.35)
        section_matches = [s for s in self.FU_SECTION_SIGNATURES if s in normalized_text]
        if section_matches:
            matched.extend(section_matches)
            sections.extend(section_matches)
            section_weight = min(0.35, len(section_matches) * 0.08)
            score += section_weight

        # 3. Form Fields (Weight up to 0.25)
        field_matches = [f for f in self.FU_FIELD_SIGNATURES if f in normalized_text]
        if field_matches:
            matched.extend(field_matches)
            field_weight = min(0.25, len(field_matches) * 0.05)
            score += field_weight

        # Strong boost if both primary header and multiple fields are present
        if header_matches and len(field_matches) >= 2:
            score = max(score, 0.85)

        return min(1.0, score), matched, sections

    def evaluate_ats(
        self, normalized_text: str, raw_text: str
    ) -> tuple[float, list[str], list[str]]:
        """
        Evaluate likelihood of document being an ATS or standard CV.
        Returns: (score, matched_indicators, detected_sections)
        """
        matched: list[str] = []
        sections: list[str] = []
        score = 0.0

        # 1. Contact Information presence (Weight up to 0.25)
        if self.EMAIL_REGEX.search(raw_text):
            matched.append("CONTACT:EMAIL")
            score += 0.12
        if self.PHONE_REGEX.search(raw_text):
            matched.append("CONTACT:PHONE")
            score += 0.08
        if self.URL_REGEX.search(raw_text):
            matched.append("CONTACT:URL_PROFILE")
            score += 0.05

        # 2. Profile / Summary section (Weight up to 0.20)
        profile_matches = [p for p in self.ATS_PROFILE_SIGNATURES if p in normalized_text]
        if profile_matches:
            matched.append(profile_matches[0])
            sections.append("PROFILE_SUMMARY")
            score += 0.20

        # 3. Experience section (Weight up to 0.25)
        exp_matches = [e for e in self.ATS_EXPERIENCE_SIGNATURES if e in normalized_text]
        if exp_matches:
            matched.append(exp_matches[0])
            sections.append("EXPERIENCE")
            score += 0.25

        # 4. Education section (Weight up to 0.20)
        edu_matches = [ed for ed in self.ATS_EDUCATION_SIGNATURES if ed in normalized_text]
        if edu_matches:
            matched.append(edu_matches[0])
            sections.append("EDUCATION")
            score += 0.20

        # 5. Skills section (Weight up to 0.15)
        skill_matches = [sk for sk in self.ATS_SKILLS_SIGNATURES if sk in normalized_text]
        if skill_matches:
            matched.append(skill_matches[0])
            sections.append("SKILLS")
            score += 0.15

        # 6. Additional sections (Weight up to 0.10)
        misc_matches = [m for m in self.ATS_MISC_SIGNATURES if m in normalized_text]
        if misc_matches:
            matched.append(misc_matches[0])
            sections.append("ADDITIONAL")
            score += 0.10

        # Penalize if strong Formato Único government marks are detected
        fu_exclusive_marks = [
            "FORMATO UNICO DE HOJA DE VIDA",
            "DEPARTAMENTO ADMINISTRATIVO DE LA FUNCION PUBLICA",
            "FIRMA DEL SERVIDOR PUBLICO",
            "OBSERVACIONES DEL JEFE DE PERSONAL",
        ]
        if any(mark in normalized_text for mark in fu_exclusive_marks):
            score *= 0.20  # Heavily discount ATS if official government form markers exist

        return min(1.0, score), matched, sections

    def classify(
        self, text: str, page_texts: list[str] | None = None
    ) -> ClassificationResult:
        """
        Classifies the document text into FORMATO_UNICO, ATS, or UNKNOWN.
        """
        raw_text = text or ""
        normalized = self.normalize_text(raw_text)

        # 1. Short text or empty text check
        if len(normalized) < self.MIN_TEXT_LENGTH:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                matched_indicators=[],
                scores={"FORMATO_UNICO": 0.0, "ATS": 0.0},
                detected_sections=[],
                reasons=[f"Texto insuficiente para clasificación ({len(normalized)} caracteres < {self.MIN_TEXT_LENGTH})"],
            )

        # 2. Disqualifier check for non-CV documents
        non_cv_matches = [n for n in self.NON_CV_SIGNATURES if n in normalized]
        if non_cv_matches:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence=0.1,
                matched_indicators=non_cv_matches,
                scores={"FORMATO_UNICO": 0.0, "ATS": 0.0},
                detected_sections=[],
                reasons=[f"Documento no corresponde a una hoja de vida (detectado marcador: {non_cv_matches[0]})"],
            )

        # 3. Evaluate both candidates
        fu_score, fu_indicators, fu_sections = self.evaluate_formato_unico(normalized)
        ats_score, ats_indicators, ats_sections = self.evaluate_ats(normalized, raw_text)

        scores = {
            "FORMATO_UNICO": round(fu_score, 4),
            "ATS": round(ats_score, 4),
        }

        # 4. Decision logic
        # Formato Único takes precedence if it exceeds threshold and beats ATS
        if fu_score >= 0.55 and fu_score >= ats_score:
            reasons = [
                f"Detectada estructura de Formato Único DAFP con confianza {fu_score:.2f}",
                f"Indicadores clave: {', '.join(fu_indicators[:5])}",
            ]
            return ClassificationResult(
                document_type=DocumentType.FORMATO_UNICO,
                confidence=fu_score,
                matched_indicators=fu_indicators,
                scores=scores,
                detected_sections=fu_sections,
                reasons=reasons,
            )

        # ATS / CV standard
        if ats_score >= self.MIN_CONFIDENCE_THRESHOLD and ats_score > fu_score:
            reasons = [
                f"Detectada estructura de hoja de vida libre / ATS con confianza {ats_score:.2f}",
                f"Secciones detectadas: {', '.join(ats_sections)}",
            ]
            return ClassificationResult(
                document_type=DocumentType.ATS,
                confidence=ats_score,
                matched_indicators=ats_indicators,
                scores=scores,
                detected_sections=ats_sections,
                reasons=reasons,
            )

        # UNKNOWN / Review Required
        max_score = max(fu_score, ats_score)
        reasons = [
            f"El documento no alcanzó el umbral mínimo de confianza ({self.MIN_CONFIDENCE_THRESHOLD:.2f}). Mayor puntuación: {max_score:.2f}",
            "Se requiere revisión humana para determinar el formato de la hoja de vida.",
        ]
        all_indicators = fu_indicators + ats_indicators
        all_sections = list(set(fu_sections + ats_sections))

        return ClassificationResult(
            document_type=DocumentType.UNKNOWN,
            confidence=max_score,
            matched_indicators=all_indicators[:10],
            scores=scores,
            detected_sections=all_sections,
            reasons=reasons,
        )
