"""
Google Document AI OCR provider adapter.
"""

import json
import os
import time
from typing import Any
import structlog

from app.application.interfaces.ocr_provider import (
    BoundingBox,
    OCRDocumentResult,
    OCRPageResult,
    OCRProcessingError,
    OCRProvider,
    OCRProviderUnavailableError,
    OCRToken,
)
from app.config.constants import OCRProvider as OCRProviderEnum
from app.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


class GoogleDocumentAIProvider(OCRProvider):
    """
    Adapter for Google Cloud Document AI.
    Converts Document AI responses to canonical OCRDocumentResult.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def provider_name(self) -> str:
        return OCRProviderEnum.GOOGLE_DAI.value

    async def health_check(self) -> bool:
        """
        Verify that Google Document AI settings and client can be initialized.
        """
        if not self._settings.google_project_id or not self._settings.google_processor_id:
            return False
        return True

    def _ensure_configured(self) -> None:
        if not self._settings.google_project_id or not self._settings.google_processor_id:
            raise OCRProviderUnavailableError(
                "Google Document AI no está configurado. "
                "Defina GOOGLE_PROJECT_ID y GOOGLE_PROCESSOR_ID en las variables de entorno."
            )

    async def process_page(
        self,
        image_bytes: bytes,
        page_number: int,
    ) -> OCRPageResult:
        self._ensure_configured()
        # Document AI typically processes full PDFs or image bytes via process_document
        res = await self.process_document(pdf_bytes=image_bytes)
        if res.pages:
            return res.pages[0]
        raise OCRProcessingError("Google Document AI no retornó páginas para la imagen enviada.")

    async def process_document(
        self,
        pdf_bytes: bytes,
    ) -> OCRDocumentResult:
        self._ensure_configured()
        start_time = time.perf_counter()

        try:
            from google.cloud import documentai_v1 as documentai

            client_options = {"api_endpoint": f"{self._settings.google_location}-documentai.googleapis.com"}
            client_kwargs: dict[str, Any] = {"client_options": client_options}

            sa_json = self._settings.google_service_account_json
            if sa_json:
                from google.oauth2 import service_account
                if os.path.isfile(sa_json):
                    client_kwargs["credentials"] = service_account.Credentials.from_service_account_file(sa_json)
                else:
                    try:
                        info = json.loads(sa_json)
                        client_kwargs["credentials"] = service_account.Credentials.from_service_account_info(info)
                    except Exception:
                        pass

            client = documentai.DocumentProcessorServiceClient(**client_kwargs)
            name = client.processor_path(
                self._settings.google_project_id,
                self._settings.google_location,
                self._settings.google_processor_id,
            )

            raw_document = documentai.RawDocument(
                content=pdf_bytes,
                mime_type="application/pdf",
            )
            request = documentai.ProcessRequest(name=name, raw_document=raw_document)
            result = client.process_document(request=request)
            document = result.document

            pages_results: list[OCRPageResult] = []
            for idx, page in enumerate(document.pages):
                page_tokens: list[OCRToken] = []
                page_text_segments: list[str] = []

                # Extract tokens
                for token in page.tokens:
                    # Token text from document.text and text_anchor
                    segments = token.layout.text_anchor.text_segments
                    token_text = "".join(
                        document.text[int(s.start_index):int(s.end_index)]
                        for s in segments
                    )
                    page_text_segments.append(token_text)

                    # Bounding poly
                    bbox = None
                    if token.layout.bounding_poly and token.layout.bounding_poly.normalized_vertices:
                        verts = token.layout.bounding_poly.normalized_vertices
                        min_x = min(v.x for v in verts) * float(page.dimension.width or 595.0)
                        min_y = min(v.y for v in verts) * float(page.dimension.height or 842.0)
                        max_x = max(v.x for v in verts) * float(page.dimension.width or 595.0)
                        max_y = max(v.y for v in verts) * float(page.dimension.height or 842.0)
                        bbox = BoundingBox(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)

                    page_tokens.append(
                        OCRToken(
                            text=token_text.strip(),
                            confidence=float(token.layout.confidence or 0.90),
                            page_number=idx + 1,
                            bounding_box=bbox,
                        )
                    )

                page_full_text = " ".join(t.text for t in page_tokens if t.text)
                avg_conf = (
                    sum(t.confidence for t in page_tokens) / len(page_tokens)
                    if page_tokens
                    else 0.90
                )

                pages_results.append(
                    OCRPageResult(
                        page_number=idx + 1,
                        full_text=page_full_text,
                        tokens=page_tokens,
                        confidence=avg_conf,
                        raw_response={"pages_count": len(document.pages)},
                        width_pts=float(page.dimension.width or 595.0),
                        height_pts=float(page.dimension.height or 842.0),
                        has_native_text=False,
                    )
                )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return OCRDocumentResult(
                pages=pages_results,
                provider=self.provider_name,
                model_version="google-docai-v1",
                processing_ms=duration_ms,
            )

        except Exception as exc:
            logger.error("google_documentai_failed", error=str(exc))
            raise OCRProcessingError(
                f"Error al procesar documento con Google Document AI: {exc}"
            ) from exc
