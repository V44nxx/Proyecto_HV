"""
Gunicorn configuration for production deployment with Uvicorn workers.

Optimized for async FastAPI processing on VPS with multi-core CPUs,
memory-leak prevention (max_requests with jitter), and generous timeouts
for dense document processing and OCR workloads.
"""

import multiprocessing
import os

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# Worker processes
# Calculate default based on CPU cores, allowing override via WEB_CONCURRENCY
cpu_count = multiprocessing.cpu_count()
default_workers = max(2, min(cpu_count * 2 + 1, 8))
workers = int(os.getenv("WEB_CONCURRENCY", str(default_workers)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))

# Worker lifecycle & memory leak prevention
# Periodically restart workers after processing a batch of PDF operations
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Timeouts
# Set generous timeout (120s) for dense multi-page OCR and PDF parsing
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Logging
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# Security & Process naming
proc_name = "proyecto_hv_backend"


def on_starting(server):
    """Log startup message with active worker configuration."""
    server.log.info(
        "Iniciando servidor de producción Proyecto HV (Gunicorn + Uvicorn) - "
        f"Workers: {workers}, Bind: {bind}, Timeout: {timeout}s"
    )


def worker_int(worker):
    """Handle graceful shutdown signal for a worker."""
    worker.log.info(f"Worker {worker.pid} recibió señal de terminación; cerrando conexiones activas...")
