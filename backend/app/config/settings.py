"""
Application configuration using Pydantic BaseSettings.

All settings are loaded from environment variables (or .env file in development).
No secrets are hardcoded here.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageBackend(StrEnum):
    LOCAL = "local"
    MINIO = "minio"
    S3 = "s3"


class OCRProviderName(StrEnum):
    MOCK = "mock"
    GOOGLE_DAI = "google_dai"
    AZURE_DI = "azure_di"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "Gestión de Hojas de Vida"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: str = "INFO"

    # ---- API ----
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ---- Security ----
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4
    max_failed_login_attempts: int = 5

    # ---- Database ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "proyecto_hv"
    postgres_user: str = "hv_app"
    postgres_password: str = Field(min_length=8)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Synchronous URL for Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ---- Redis ----
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ---- File Storage ----
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_local_path: Path = Path("./data/documents")
    max_upload_size_mb: int = 50
    allowed_mime_types: list[str] = ["application/pdf"]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # MinIO
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "proyecto-hv-documents"
    minio_secure: bool = False

    # ---- OCR ----
    ocr_provider: OCRProviderName = OCRProviderName.MOCK
    ocr_confidence_high_threshold: float = 0.90
    ocr_confidence_medium_threshold: float = 0.70

    # Google Document AI
    google_project_id: str = ""
    google_processor_id: str = ""
    google_location: str = "us"
    google_service_account_json: str = ""

    # Azure Document Intelligence
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""

    # ---- Workers ----
    worker_concurrency: int = 4
    max_job_retries: int = 3

    # ---- CORS ----
    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # ---- Rate Limiting ----
    rate_limit_auth_per_minute: int = 10
    rate_limit_api_per_minute: int = 60

    @field_validator("app_env", mode="before")
    @classmethod
    def validate_env(cls, v: str) -> str:
        return v.lower()

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Use this function as a FastAPI dependency.

    Example:
        @router.get("/example")
        async def example(settings: Settings = Depends(get_settings)):
            ...
    """
    return Settings()
