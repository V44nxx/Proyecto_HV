"""
Health check endpoints.

These endpoints verify that all critical system dependencies are reachable.
They are used by Docker health checks, load balancers, and monitoring.

GET /health          — basic API liveness (no auth required)
GET /health/db       — PostgreSQL connectivity (auth required)
GET /health/storage  — file storage connectivity (auth required)
"""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.infrastructure.database.session import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Verificar estado del API",
    description="Endpoint público de liveness. No requiere autenticación.",
    tags=["Sistema"],
)
async def health_check(settings: Settings = Depends(get_settings)) -> dict:
    """Returns basic API liveness information."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get(
    "/health/db",
    summary="Verificar conexión a base de datos",
    tags=["Sistema"],
)
async def health_check_db(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Checks PostgreSQL connectivity.
    Returns the server version and current timestamp from the DB.
    Requires authentication (added when auth middleware is implemented).
    """
    try:
        result = await db.execute(
            text("SELECT version(), NOW() AT TIME ZONE 'UTC' as db_time")
        )
        row = result.first()

        logger.debug("health_check_db_ok")
        return {
            "status": "ok",
            "database": "postgresql",
            "server_version": row[0].split(" ")[1] if row else "unknown",
            "db_time": row[1].isoformat() if row else None,
        }
    except Exception as exc:
        logger.error("health_check_db_failed", error=str(exc))
        return {
            "status": "error",
            "database": "postgresql",
            "error": "Database connection failed",
        }


@router.get(
    "/health/storage",
    summary="Verificar almacenamiento de archivos",
    tags=["Sistema"],
)
async def health_check_storage(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Checks that the file storage backend is reachable.
    For local storage, verifies the directory exists and is writable.
    """
    from pathlib import Path

    if settings.storage_backend == "local":
        storage_path = Path(settings.storage_local_path)
        try:
            storage_path.mkdir(parents=True, exist_ok=True)
            test_file = storage_path / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            return {"status": "ok", "backend": "local", "path": str(storage_path)}
        except Exception as exc:
            logger.error("health_check_storage_failed", error=str(exc))
            return {
                "status": "error",
                "backend": "local",
                "error": "Storage directory not writable",
            }

    return {
        "status": "not_implemented",
        "backend": settings.storage_backend,
        "message": "Health check for this backend is not yet implemented",
    }
