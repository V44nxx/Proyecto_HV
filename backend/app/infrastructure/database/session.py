"""
Database session factory and async engine configuration.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import get_settings

_settings = get_settings()

if "sqlite" in _settings.database_url:
    import json
    import sqlite3
    from sqlalchemy.dialects.postgresql import INET, JSONB
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.types import ARRAY

    try:
        sqlite3.register_adapter(list, json.dumps)
    except Exception:
        pass

    @compiles(ARRAY, "sqlite")
    def _compile_array_sqlite(type_, compiler, **kw):
        return "TEXT"

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    @compiles(INET, "sqlite")
    def _compile_inet_sqlite(type_, compiler, **kw):
        return "VARCHAR(45)"

    engine: AsyncEngine = create_async_engine(
        _settings.database_url,
        echo=_settings.debug,
        connect_args={"check_same_thread": False},
    )
else:
    engine: AsyncEngine = create_async_engine(
        _settings.database_url,
        echo=_settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )

# ---- Session factory ----
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoid lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            ...

    The session is committed on success and rolled back on exception.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
