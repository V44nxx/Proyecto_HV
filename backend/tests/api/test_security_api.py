"""
API integration tests for Security Hardening & DevSecOps:
- Security Health Check: GET /api/v1/health/security
- Rate Limiting Middleware: HTTP 429 Too Many Requests & Retry-After
- Malicious PDF Injection Prevention: Block PDFs with embedded scripts
- Security Headers: OWASP & Cross-Origin Isolation headers
"""

import io
import uuid
import fitz
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db_session
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider
from app.infrastructure.security.rate_limiter import rate_limiter
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_application
from app.presentation.dependencies.auth import AuthenticatedUser, get_current_user
from app.presentation.dependencies.document_dependencies import get_ocr, get_storage


@pytest_asyncio.fixture
async def security_api_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    # Clear rate limits before test suite runs
    await rate_limiter.clear_all()

    test_user_id = uuid.uuid4()
    mock_user = AuthenticatedUser(
        user_id=str(test_user_id),
        role="ADMIN",
        permissions=["documents:read", "documents:write", "documents:delete"],
        jti=str(uuid.uuid4()),
    )

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        yield test_db

    storage = LocalStorageProvider(base_path=str(tmp_path / "sec_storage"))

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await rate_limiter.clear_all()


@pytest.mark.asyncio
async def test_health_security_endpoint(security_api_client: AsyncClient):
    resp = await security_api_client.get("/api/v1/health/security")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "security_score" in data
    assert "checks" in data
    checks = data["checks"]
    assert checks["rate_limiting_active"] is True
    assert checks["secret_key_configured"] is True
    assert checks["dlp_encryption_ready"] is True


@pytest.mark.asyncio
async def test_security_headers_present_on_response(security_api_client: AsyncClient):
    resp = await security_api_client.get("/api/v1/health")
    assert resp.status_code == 200
    headers = resp.headers

    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("cross-origin-opener-policy") == "same-origin"
    assert headers.get("cross-origin-resource-policy") == "same-origin"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_rate_limiting_enforced_on_auth_endpoint(security_api_client: AsyncClient):
    await rate_limiter.clear_all()

    # The auth login endpoint has a rate limit of 10 requests per minute
    client_ip = "192.168.10.50"
    headers = {"x-forwarded-for": client_ip}

    # Send 10 requests (all should pass through rate limiter, returning 400 or 422 for bad login payload)
    for _ in range(10):
        resp = await security_api_client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@test.com", "password": "wrongpassword123"},
            headers=headers,
        )
        assert resp.status_code in (400, 401, 422)
        assert "x-ratelimit-remaining" in resp.headers

    # The 11th request must trigger rate limit 429 Too Many Requests
    blocked_resp = await security_api_client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@test.com", "password": "wrongpassword123"},
        headers=headers,
    )
    assert blocked_resp.status_code == 429
    assert "retry-after" in blocked_resp.headers
    assert int(blocked_resp.headers["retry-after"]) >= 1
    data = blocked_resp.json()
    assert "Demasiadas solicitudes" in data["detail"]

    # Different client IP should not be blocked
    other_ip_resp = await security_api_client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@test.com", "password": "wrongpassword123"},
        headers={"x-forwarded-for": "192.168.10.99"},
    )
    assert other_ip_resp.status_code != 429


@pytest.mark.asyncio
async def test_upload_malicious_pdf_with_javascript_blocked(security_api_client: AsyncClient):
    # Generate clean PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "CV con script malicioso")
    clean_bytes = doc.tobytes()
    doc.close()

    # Inject dangerous active JavaScript payload
    malicious_bytes = clean_bytes + b"\n% /JavaScript << /JS (app.alert('pwned')) >>\n"

    file_tuple = ("cv_malicioso.pdf", io.BytesIO(malicious_bytes), "application/pdf")
    resp = await security_api_client.post(
        "/api/v1/documents",
        files={"file": file_tuple},
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data
    assert "seguridad" in data["detail"].lower() or "javascript" in data["detail"].lower()
