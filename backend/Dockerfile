# ============================================================
# Backend Dockerfile
# Multi-stage build: builder → production
# ============================================================

# ---- Stage 1: Builder ----
# Install dependencies in a venv to keep the final image lean
FROM python:3.12-slim AS builder

# System dependencies for building Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies first (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .


# ---- Stage 2: Production ----
FROM python:3.12-slim AS production

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Create application directory
WORKDIR /app

# Create data directory with proper ownership
RUN mkdir -p /app/data/documents && chown -R appuser:appgroup /app

# Copy application code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command for production: Gunicorn with Uvicorn workers and gunicorn_conf.py
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
