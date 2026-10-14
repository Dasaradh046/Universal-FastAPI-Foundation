"""
Application configuration settings.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    # Application
    APP_NAME: str = "Universal FastAPI Foundation"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["local", "development", "staging", "prod"] = "local"
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # Database - Individual components (preferred method)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = Field(default="postgres", validation_alias="DB_PASSWORD")
    DB_NAME: str = "ubf"
    
    # Database - Full DSN (optional, overrides individual components if set)
    DATABASE_URL: str | None = None  # asyncpg URL
    DATABASE_URL_SYNC: str | None = None  # psycopg2 URL for Alembic
    
    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-prod-a-strong-secret-key-min-32-chars-long",
        validation_alias="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes - short lived access
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    
    # JWT Algorithm options: HS256 (symmetric) or RS256 (asymmetric)
    # RS256 requires generating a keypair with scripts/generate_keys.py
    JWT_ALGORITHM: Literal["HS256", "RS256"] = "HS256"
    JWT_PRIVATE_KEY_PATH: str | None = None
    JWT_PUBLIC_KEY_PATH: str | None = None
    JWT_ISSUER: str = "universal-fastapi-foundation"
    JWT_AUDIENCE: str = "universal-fastapi-foundation-users"
    JWT_LEEWAY_SECONDS: int = 10  # Clock leeway for expiration validation
    JWT_KEY_ID: str | None = None  # Key ID for JWKS/rotation support
    
    # Cookie settings for httpOnly JWT transport
    COOKIE_ACCESS_NAME: str = "ph_access_token"
    COOKIE_REFRESH_NAME: str = "ph_refresh_token"
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "lax"
    
    # Frontend settings
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    
    # MFA / 2FA settings
    MFA_TOKEN_EXPIRE_MINUTES: int = 5
    TWO_FACTOR_PENDING_TIMEOUT_MINUTES: int = 30
    TWO_FACTOR_ISSUER: str = "Universal FastAPI Foundation"
    
    # Password policy
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_EXPIRATION_ENABLED: bool = True
    PASSWORD_EXPIRE_DAYS: int = 90
    PASSWORD_EXPIRE_WARNING_DAYS: int = 7
    PASSWORD_BLOCKLIST_ENABLED: bool = False
    PASSWORD_BLOCKLIST: list[str] = Field(default_factory=list)
    
    # Rate limiting for auth endpoints
    LOGIN_RATE_LIMIT_REQUESTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW: int = 900  # 15 minutes
    MFA_RATE_LIMIT_REQUESTS: int = 10
    MFA_RATE_LIMIT_WINDOW: int = 900  # 15 minutes
    
    # Refresh token rotation
    REFRESH_TOKEN_ROTATION_ENABLED: bool = True
    REFRESH_TOKEN_SLIDING_EXPIRATION: bool = False
    SESSION_ABSOLUTE_MAX_DAYS: int = 90
    
    # Email
    EMAIL_PROVIDER: Literal["smtp", "brevo", "sendgrid", "ses", "log"] = "log"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    
    # Email notifications
    NOTIFICATIONS_FROM_EMAIL: str | None = None
    NOTIFICATIONS_FROM_NAME: str | None = None
    
    # Storage
    STORAGE_PROVIDER: Literal["local", "minio", "s3", "gcs", "azure"] = "local"
    LOCAL_STORAGE_PATH: str = "./uploads"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    
    # AI Providers
    AI_PROVIDER: Literal["openai", "anthropic", "google", "groq", "mistral"] = "openai"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    
    # Observability
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_HEADERS: str | None = None
    SENTRY_DSN: str | None = None
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_STRATEGY: Literal["fixed-window", "sliding-window", "token-bucket"] = "fixed-window"
    
    # CORS
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    
    # File upload limits
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    # Encryption key for field-level encryption
    ENCRYPTION_KEY: str | None = None
    ENCRYPTION_KEY_FILE: str | None = None
    
    # Tenant GUC name for multi-tenancy (PostgreSQL specific)
    TENANT_GUC_NAME: str = "app.tenant_id"
    
    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("SECRET_KEY")
    @classmethod
    def _check_secret_key(cls, v: str) -> str:
        if not cls.is_local and v.startswith("change-me"):
            raise ValueError(
                "SECRET_KEY is still the default placeholder. "
                f"Set a strong random value for ENVIRONMENT={cls.ENVIRONMENT!r}."
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    def _dsn(self, driver: str) -> str:
        """Build a PostgreSQL DSN for `driver` from the DB_* parts."""
        return (
            f"postgresql+{driver}://"
            f"{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url(self) -> str:
        """Async DSN (asyncpg) for the app + Alembic online migrations.

        ``DATABASE_URL`` (full DSN) wins when explicitly set; otherwise the
        URL is composed from ``DB_HOST``/``DB_PORT``/``DB_USER``/``DB_PASSWORD``/``DB_NAME``.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return self._dsn("asyncpg")

    @property
    def database_url_sync(self) -> str:
        """Sync DSN (psycopg2) for Alembic offline mode / sync scripts."""
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        return self._dsn("psycopg2")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse ``BACKEND_CORS_ORIGINS`` into a clean list for the CORS middleware."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_prod(self) -> bool:
        return self.ENVIRONMENT == "prod"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == "local"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    def enforce_production_secrets(self) -> None:
        """Fail fast in non-local envs if a default secret is still in use.

        Call this once at app startup (``app/main.py`` lifespan).
        """
        if self.is_local:
            return
            
        # Check JWT configuration
        using_rs256 = self.JWT_ALGORITHM == "RS256"
        if self.is_prod or self.is_staging:
            if not using_rs256:
                raise RuntimeError(
                    f"JWT_ALGORITHM must be RS256 for ENVIRONMENT={self.ENVIRONMENT!r}. "
                    "Generate a keypair with: python scripts/generate_keys.py"
                )
            if not (self.JWT_PRIVATE_KEY_PATH and self.JWT_PUBLIC_KEY_PATH):
                raise RuntimeError(
                    "JWT_ALGORITHM=RS256 requires JWT_PRIVATE_KEY_PATH and "
                    "JWT_PUBLIC_KEY_PATH. Generate a keypair with: "
                    "python scripts/generate_keys.py"
                )
        elif not using_rs256 and self.SECRET_KEY.startswith("change-me-in-prod"):
            raise RuntimeError(
                "SECRET_KEY is still the default placeholder. "
                f"Set a strong random value for ENVIRONMENT={self.ENVIRONMENT!r}."
            )
            
        # Check database credentials
        if "change-me" in self.database_url:
            raise RuntimeError(
                "Database credentials still contain a placeholder. "
                "Set DB_USER/DB_PASSWORD (or DATABASE_URL) for "
                f"ENVIRONMENT={self.ENVIRONMENT!r}."
            )
            
        # Check encryption key
        if not (self.ENCRYPTION_KEY or self.ENCRYPTION_KEY_FILE):
            raise RuntimeError(
                "ENCRYPTION_KEY or ENCRYPTION_KEY_FILE is required outside "
                "local development (Fernet key for field-level encryption at rest). "
                "Generate one with: python scripts/generate_keys.py"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` singleton.

    Use this in FastAPI ``Depends(get_settings)`` so tests can override it
    via ``app.dependency_overrides[get_settings] = lambda: test_settings``.
    """
    return Settings()


# The module-level singleton is what most code imports directly.
settings = get_settings()