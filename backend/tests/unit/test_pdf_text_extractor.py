"""
Unit tests for native PDFTextExtractor using PyMuPDF.
"""

import fitz
import pytest

from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor


def create_sample_pdf(text: str = "Información Personal Carlos Gomez Bogotá", pages: int = 1) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), f"{text} - Página número {i + 1}")
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def create_blank_pdf(pages: int = 1) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=595, height=842)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def test_extract_native_document() -> None:
    extractor = PDFTextExtractor()
    pdf_bytes = create_sample_pdf(pages=2)

    doc_result = extractor.extract_document(pdf_bytes)

    assert doc_result.page_count == 2
    assert doc_result.provider == "NATIVE"
    assert "Carlos Gomez" in doc_result.full_text

    p1 = doc_result.pages[0]
    assert p1.page_number == 1
    assert p1.has_native_text is True
    assert p1.width_pts == 595.0
    assert p1.height_pts == 842.0
    assert len(p1.tokens) > 0

    # Token has bounding box
    token = p1.tokens[0]
    assert token.bounding_box is not None
    assert token.bounding_box.width > 0
    assert token.bounding_box.height > 0
    assert token.confidence == 0.99


def test_render_page_image() -> None:
    extractor = PDFTextExtractor()
    pdf_bytes = create_sample_pdf(pages=1)

    png_bytes = extractor.render_page_image(pdf_bytes, page_number=1, dpi=100)

    assert len(png_bytes) > 0
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_invalid_page_number_raises() -> None:
    extractor = PDFTextExtractor()
    pdf_bytes = create_sample_pdf(pages=1)

    with pytest.raises(ValueError) as exc:
        extractor.render_page_image(pdf_bytes, page_number=99)
    assert "inválido" in str(exc.value).lower()


def test_has_scanned_pages() -> None:
    extractor = PDFTextExtractor(min_chars_per_page=50)

    # Document with rich text: no scanned pages
    rich_pdf = create_sample_pdf(
        text="Este es un texto largo y completo que supera ampliamente los cincuenta caracteres requeridos",
        pages=2,
    )
    assert extractor.has_scanned_pages(rich_pdf) is False

    # Document with blank page: has scanned pages
    blank_pdf = create_blank_pdf(pages=1)
    assert extractor.has_scanned_pages(blank_pdf) is True
