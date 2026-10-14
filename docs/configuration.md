# Configuration Guide

Universal FastAPI Foundation uses **pydantic-settings v2** for type-safe, validated configuration loaded from environment variables and `.env` files.

## Configuration Class

All settings are defined in `app/core/config.py` as a `Settings` class inheriting from `BaseSettings`.

```python
from app.core.config import settings

# Access settings
database_url = settings.database_url
secret_key = settings.SECRET_KEY
debug_mode = settings.DEBUG
```

## Environment Variables

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | "Universal FastAPI Foundation" | Application display name |
| `APP_VERSION` | "0.1.0" | Application version |
| `DEBUG` | `false` | Enable debug mode |
| `ENVIRONMENT` | `local` | Environment: `local`, `development`, `staging`, `prod` |
| `API_V1_STR` | `/api/v1` | API version prefix |

### Database

**Component-based (recommended):**

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `DB_NAME` | `ubf` | Database name |

**Full DSN (overrides components):**

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async DSN (asyncpg): `postgresql+asyncpg://user:pass@host:port/db` |
| `DATABASE_URL_SYNC` | Sync DSN (psycopg2): `postgresql+psycopg2://user:pass@host:port/db` |

Derived properties:
```python
settings.database_url      # Async DSN for app + online migrations
settings.database_url_sync # Sync DSN for offline migrations/scripts
```

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | JWT signing key (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token TTL |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ALGORITHM` | `HS256` | `HS256` or `RS256` |
| `JWT_PRIVATE_KEY_PATH` | - | Path to RSA private key (RS256) |
| `JWT_PUBLIC_KEY_PATH` | - | Path to RSA public key (RS256) |
| `JWT_ISSUER` | `universal-fastapi-foundation` | JWT issuer claim |
| `JWT_AUDIENCE` | `universal-fastapi-foundation-users` | JWT audience claim |
| `JWT_LEEWAY_SECONDS` | `10` | Clock skew tolerance |
| `JWT_KEY_ID` | - | Key ID for JWKS rotation |

**Cookie settings:**

| Variable | Default |
|----------|---------|
| `COOKIE_ACCESS_NAME` | `ph_access_token` |
| `COOKIE_REFRESH_NAME` | `ph_refresh_token` |
| `COOKIE_SAMESITE` | `lax` |

### Frontend

| Variable | Default |
|----------|---------|
| `FRONTEND_BASE_URL` | `http://localhost:3000` |

### MFA / 2FA

| Variable | Default |
|----------|---------|
| `MFA_TOKEN_EXPIRE_MINUTES` | `5` |
| `TWO_FACTOR_PENDING_TIMEOUT_MINUTES` | `30` |
| `TWO_FACTOR_ISSUER` | `Universal FastAPI Foundation` |

### Password Policy

| Variable | Default |
|----------|---------|
| `PASSWORD_MIN_LENGTH` | `12` |
| `PASSWORD_EXPIRATION_ENABLED` | `true` |
| `PASSWORD_EXPIRE_DAYS` | `90` |
| `PASSWORD_EXPIRE_WARNING_DAYS` | `7` |
| `PASSWORD_BLOCKLIST_ENABLED` | `false` |
| `PASSWORD_BLOCKLIST` | `[]` (comma-separated) |

### Rate Limiting (Auth)

| Variable | Default |
|----------|---------|
| `LOGIN_RATE_LIMIT_REQUESTS` | `5` |
| `LOGIN_RATE_LIMIT_WINDOW` | `900` (seconds) |
| `MFA_RATE_LIMIT_REQUESTS` | `10` |
| `MFA_RATE_LIMIT_WINDOW` | `900` (seconds) |

### Refresh Token Rotation

| Variable | Default |
|----------|---------|
| `REFRESH_TOKEN_ROTATION_ENABLED` | `true` |
| `REFRESH_TOKEN_SLIDING_EXPIRATION` | `false` |
| `SESSION_ABSOLUTE_MAX_DAYS` | `90` |

### Email

| Variable | Default |
|----------|---------|
| `EMAIL_PROVIDER` | `log` (smtp, brevo, sendgrid, ses, log) |
| `SMTP_HOST` | - |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | - |
| `SMTP_PASSWORD` | - |
| `SMTP_TLS` | `true` |
| `SMTP_SSL` | `false` |
| `NOTIFICATIONS_FROM_EMAIL` | - |
| `NOTIFICATIONS_FROM_NAME` | - |

### Storage

| Variable | Default |
|----------|---------|
| `STORAGE_PROVIDER` | `local` (local, minio, s3, gcs, azure) |
| `LOCAL_STORAGE_PATH` | `./uploads` |
| `MINIO_ENDPOINT` | `localhost:9000` |
| `MINIO_ACCESS_KEY` | `minioadmin` |
| `MINIO_SECRET_KEY` | `minioadmin` |
| `MINIO_SECURE` | `false` |

### AI Providers

| Variable | Default |
|----------|---------|
| `AI_PROVIDER` | `openai` (openai, anthropic, google, groq, mistral) |
| `OPENAI_API_KEY` | - |
| `ANTHROPIC_API_KEY` | - |
| `GOOGLE_API_KEY` | - |
| `GROQ_API_KEY` | - |
| `MISTRAL_API_KEY` | - |

### Observability

| Variable | Default |
|----------|---------|
| `OTEL_ENABLED` | `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - |
| `OTEL_EXPORTER_OTLP_HEADERS` | - |
| `SENTRY_DSN` | - |

### Rate Limiting (General)

| Variable | Default |
|----------|---------|
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_REQUESTS` | `100` |
| `RATE_LIMIT_WINDOW` | `60` (seconds) |
| `RATE_LIMIT_STRATEGY` | `fixed-window` |

### CORS

| Variable | Default |
|----------|---------|
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000,http://localhost:8080` |

### File Upload

| Variable | Default |
|----------|---------|
| `MAX_UPLOAD_SIZE` | `10485760` (10 MB) |

### Encryption

| Variable | Default |
|----------|---------|
| `ENCRYPTION_KEY` | - (Fernet key) |
| `ENCRYPTION_KEY_FILE` | - (Path to key file) |

### Multi-Tenancy

| Variable | Default |
|----------|---------|
| `TENANT_GUC_NAME` | `app.tenant_id` (PostgreSQL GUC) |

## Environment-Specific Configuration

### Local Development (`.env`)

```env
ENVIRONMENT=local
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ubf
SECRET_KEY=dev-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
EMAIL_PROVIDER=log
STORAGE_PROVIDER=local
```

### Production

```env
ENVIRONMENT=prod
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:strong-pass@prod-db:5432/ubf
SECRET_KEY=strong-random-key-64-chars-minimum
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/secrets/jwt_public.pem
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=sg.xxx
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=my-bucket
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector:4317
SENTRY_DSN=https://xxx@sentry.io/xxx
```

## Configuration Validation

Settings are validated on startup via `settings.enforce_production_secrets()` called in `app/core/lifespan.py`.

Validation rules:
- `SECRET_KEY` must be ≥32 chars, not default in non-local
- `JWT_ALGORITHM=RS256` required for prod/staging
- Database credentials must not contain placeholders
- `ENCRYPTION_KEY` or `ENCRYPTION_KEY_FILE` required outside local

## Accessing Settings in Code

```python
# Direct import (singleton)
from app.core.config import settings

# Via FastAPI dependency (for testing override)
from app.core.config import get_settings

@app.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    return {"environment": settings.ENVIRONMENT}
```

## Override in Tests

```python
# conftest.py
from app.core.config import get_settings, Settings

@pytest.fixture
def test_settings():
    return Settings(
        ENVIRONMENT="local",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
        SECRET_KEY="test-secret-key-for-testing-only-32-chars",
    )

def test_something(app, test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    # ...
```

## Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use secret managers** in production (AWS Secrets Manager, HashiCorp Vault, etc.)
3. **Rotate keys regularly** - Especially `SECRET_KEY` and JWT keys
4. **Use RS256 in production** - Generate keypair with `python scripts/generate_keys.py`
5. **Restrict CORS origins** - Set `BACKEND_CORS_ORIGINS` explicitly
6. **Enable HTTPS** - Set `COOKIE_SAMESITE=none` with `Secure` flag in production