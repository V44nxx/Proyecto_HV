"""
Integration tests fixtures.

Provides in-memory SQLite database session and fully wired test client.
"""

from collections.abc import AsyncGenerator
import json
import sqlite3
import uuid
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import ARRAY

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db_session
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_application
from app.presentation.dependencies.auth import AuthenticatedUser, get_current_user
from app.presentation.dependencies.document_dependencies import get_ocr, get_storage

sqlite3.register_adapter(list, json.dumps)

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(INET, "sqlite")
def compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Create an isolated in-memory SQLite engine for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session for inspecting persisted data."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def integration_client(test_engine, tmp_path) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated client for full integration tests."""
    app = create_application()
    test_user_id = uuid.uuid4()
    mock_user = AuthenticatedUser(
        user_id=str(test_user_id),
        role="ADMIN",
        permissions=[
            "documents:read",
            "documents:write",
            "documents:delete",
            "users:read",
            "users:write",
            "reports:read",
        ],
        jti=str(uuid.uuid4()),
    )

    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    storage = LocalStorageProvider(base_path=str(tmp_path / "integration_storage"))

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
