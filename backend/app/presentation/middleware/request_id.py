"""
Middleware: Request ID injection.

Assigns a unique ID to each request for distributed tracing.
The ID is propagated in logs and returned in the X-Request-ID response header.
"""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates or propagates a unique Request-ID per HTTP request.
    Binds it to structlog context so all log lines for a request
    include the same request_id.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Accept incoming request ID from reverse proxy or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context (available in all loggers during this request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)  # type: ignore[call-arg]
        response.headers["X-Request-ID"] = request_id

        return response
