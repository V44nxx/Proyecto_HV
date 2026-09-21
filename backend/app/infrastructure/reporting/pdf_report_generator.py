"""
PDF report generator using reportlab.
Produces printable, publication-grade tabular reports with institutional styling.
"""

import io
from typing import Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.value_objects.report_types import ReportDataset


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that adds total page count and institutional footer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        # Footer dividing rule
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(36, 32, 792 - 36, 32)

        # Institutional footer text
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            36,
            20,
            "Plataforma de Gestión de Hojas de Vida — Reporte Oficial Confidencial",
        )

        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(792 - 36, 20, page_str)
        self.restoreState()


class PdfReportGenerator:
    """Renders a ReportDataset into a printable PDF file in bytes."""

    def __init__(self) -> None:
        self._styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self) -> None:
        self.style_super_title = ParagraphStyle(
            "ReportSuperTitle",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=2,
            textTransform="uppercase",
        )
        self.style_title = ParagraphStyle(
            "ReportTitle",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1B365D"),
            spaceAfter=3,
        )
        self.style_subtitle = ParagraphStyle(
            "ReportSubtitle",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            spaceAfter=8,
        )
        self.style_meta_label = ParagraphStyle(
            "MetaLabel",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        self.style_meta_val = ParagraphStyle(
            "MetaVal",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334155"),
        )
        self.style_th = ParagraphStyle(
            "TableHead",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1,  # Center
        )
        self.style_td = ParagraphStyle(
            "TableData",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0F172A"),
        )
        self.style_td_center = ParagraphStyle(
            "TableDataCenter",
            parent=self.style_td,
            alignment=1,
        )
        self.style_td_right = ParagraphStyle(
            "TableDataRight",
            parent=self.style_td,
            alignment=2,
        )

    def generate(self, dataset: ReportDataset) -> bytes:
        """Generates a landscape Letter PDF report for the dataset."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=45,
        )

        printable_width = 792 - 72  # 720 pt

        story = []

        # 1. Header Block
        story.append(Paragraph("PLATAFORMA INSTITUCIONAL DE GESTIÓN DE HOJAS DE VIDA", self.style_super_title))
        story.append(Paragraph(dataset.title, self.style_title))
        story.append(Paragraph(dataset.description, self.style_subtitle))

        # 2. Metadata Information Box
        date_str = dataset.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        filters_str = self._format_filters(dataset.applied_filters)

        meta_data = [
            [
                Paragraph("<b>Fecha de Emisión:</b>", self.style_meta_label),
                Paragraph(date_str, self.style_meta_val),
                Paragraph("<b>Generado por:</b>", self.style_meta_label),
                Paragraph(dataset.generated_by, self.style_meta_val),
            ],
            [
                Paragraph("<b>Total Registros:</b>", self.style_meta_label),
                Paragraph(str(dataset.total_records), self.style_meta_val),
                Paragraph("<b>Filtros Aplicados:</b>", self.style_meta_label),
                Paragraph(filters_str, self.style_meta_val),
            ],
        ]

        meta_table = Table(
            meta_data,
            colWidths=[90, 180, 90, 360],
        )
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # 3. Main Data Table
        # Calculate proportional column widths
        total_ratio = sum(col.width_pdf_ratio for col in dataset.columns) or len(dataset.columns)
        col_widths = [(col.width_pdf_ratio / total_ratio) * printable_width for col in dataset.columns]

        # Table rows: Header + Data
        table_data = []

        # Headers
        header_cells = [Paragraph(col.label, self.style_th) for col in dataset.columns]
        table_data.append(header_cells)

        # Rows
        for row in dataset.rows:
            row_cells = []
            for col in dataset.columns:
                val = row.get(col.key)
                text = self._format_cell_value(val)

                if col.align == "center":
                    p = Paragraph(text, self.style_td_center)
                elif col.align == "right":
                    p = Paragraph(text, self.style_td_right)
                else:
                    p = Paragraph(text, self.style_td)
                row_cells.append(p)
            table_data.append(row_cells)

        main_table = Table(
            table_data,
            colWidths=col_widths,
            repeatRows=1,  # Repeat header on subsequent pages
        )

        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B365D")),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]

        # Alternating row colors
        for r_idx in range(1, len(table_data)):
            bg = colors.HexColor("#F8FAFC") if r_idx % 2 == 0 else colors.white
            table_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), bg))

        main_table.setStyle(TableStyle(table_style))
        story.append(main_table)

        # Build document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()

    def _format_cell_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Sí" if value else "No"
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M")
        if isinstance(value, list):
            return ", ".join(str(v) for v in value if v)
        return str(value)

    def _format_filters(self, filters: dict[str, Any]) -> str:
        if not filters:
            return "Ninguno (Catálogo completo)"
        parts = []
        for k, v in filters.items():
            if v is not None and v != "":
                parts.append(f"{k}: {v}")
        return " | ".join(parts) if parts else "Ninguno (Catálogo completo)"
