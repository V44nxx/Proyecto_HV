"""
FastAPI application factory.

Responsibilities:
- Create and configure the FastAPI application
- Register routers
- Configure middleware (CORS, security headers, etc.)
- Register startup/shutdown lifecycle events

This module should NOT contain business logic.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config.settings import get_settings
from app.infrastructure.logging.structured_logger import configure_logging
from app.presentation.api.v1 import health

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager.
    Startup: initialize connections, verify DB, etc.
    Shutdown: close connections gracefully.
    """
    configure_logging(level=settings.log_level)
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        environment=settings.app_env,
    )

    # Verify database connection on startup
    from app.infrastructure.database.session import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_ok")
    except Exception as exc:
        logger.error("database_connection_failed", error=str(exc))
        raise

    yield

    # Shutdown
    from app.infrastructure.database.session import engine
    await engine.dispose()
    logger.info("application_shutdown")


def create_application() -> FastAPI:
    """Application factory. Returns a configured FastAPI instance."""

    app = FastAPI(
        title=settings.app_name,
        description="API para gestión y análisis de hojas de vida",
        version="1.0.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ---- Middleware ----
    _register_middleware(app)

    # ---- Routers ----
    _register_routers(app)
    _register_exception_handlers(app)

    return app


def _register_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order (outermost first)."""

    # CORS — only allow configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # Security headers middleware (custom)
    from app.presentation.middleware.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID middleware
    from app.presentation.middleware.request_id import RequestIDMiddleware
    app.add_middleware(RequestIDMiddleware)


def _register_routers(app: FastAPI) -> None:
    """Register all API routers under the versioned prefix."""
    from app.presentation.api.v1 import (
        auth,
        dashboard,
        documents,
        health,
        reviews,
        search,
        users,
    )

    prefix = settings.api_v1_prefix

    app.include_router(health.router, prefix=prefix, tags=["Sistema"])
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(reviews.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)


def _register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to HTTP responses."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from app.application.use_cases.auth.exceptions import (
        AuthenticationError,
        AuthorizationError,
    )
    from app.application.use_cases.documents.exceptions import (
        DocumentError,
        DocumentNotFoundError,
        DuplicateDocumentError,
        FileTooLargeError,
        InvalidFileFormatError,
    )
    from app.application.use_cases.search.exceptions import CandidateNotFoundError

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message},
        )

    @app.exception_handler(AuthorizationError)
    async def authz_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": exc.message},
        )

    @app.exception_handler(DocumentNotFoundError)
    async def doc_not_found_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message},
        )

    @app.exception_handler(DuplicateDocumentError)
    async def duplicate_doc_handler(request: Request, exc: DuplicateDocumentError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "message": exc.message,
                    "existing_document_id": str(exc.existing_document_id),
                    "existing_filename": exc.existing_filename,
                }
            },
        )

    @app.exception_handler(InvalidFileFormatError)
    async def invalid_file_handler(request: Request, exc: InvalidFileFormatError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message},
        )

    @app.exception_handler(FileTooLargeError)
    async def file_too_large_handler(request: Request, exc: FileTooLargeError) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={"detail": exc.message},
        )

    @app.exception_handler(CandidateNotFoundError)
    async def candidate_not_found_handler(request: Request, exc: CandidateNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message},
        )


# Application instance (used by Gunicorn/Uvicorn)
app = create_application()
