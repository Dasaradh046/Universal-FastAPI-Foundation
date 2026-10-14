# Getting Started

## Prerequisites

- Python 3.12+
- PostgreSQL 14+
- uv (recommended) or pip
- Docker (optional, for containerized development)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd universal-fastapi-foundation
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync --all-extras

# Or using pip
pip install -e ".[dev,mfa,email,storage,ai,observability]"
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ubf

# Security (generate with: python scripts/generate_keys.py)
SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256

# Application
ENVIRONMENT=local
DEBUG=true
```

### 4. Start Database

```bash
# Using Docker Compose
docker compose up -d postgres

# Or use your existing PostgreSQL instance
```

### 5. Run Migrations

```bash
# Create initial migration (if needed)
alembic revision --autogenerate -m "initial"

# Apply migrations
alembic upgrade head
```

### 6. Start Application

```bash
# Development
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or directly
python -m app.main
```

### 7. Verify

- API: http://localhost:8000
- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
universal-fastapi-foundation/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                    # API layer
│   │   ├── router.py           # Main router with versioning
│   │   └── health.py           # Health endpoints
│   ├── core/                   # Core platform
│   │   ├── config.py           # Configuration (Settings)
│   │   ├── database.py         # Database engine/session
│   │   ├── security.py         # JWT, passwords, tokens
│   │   ├── permissions.py      # RBAC, authorization
│   │   ├── middleware.py       # Custom middleware
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── exception_handlers.py
│   │   ├── logging.py          # Structured logging
│   │   ├── lifespan.py         # Startup/shutdown
│   │   └── ...
│   ├── integrations/           # Third-party adapters
│   │   ├── email/
│   │   ├── storage/
│   │   └── ...
│   ├── shared/                 # Shared services
│   │   ├── pagination/
│   │   ├── audit/
│   │   └── ...
│   └── modules/                # Business modules
│       └── example_module/
├── migrations/                 # Alembic migrations
├── tests/                      # Test suites
├── tooling/                    # DevOps tooling
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── pyproject.toml
├── .env.example
├── Dockerfile
└── compose.yaml
```

## Development Workflow

### Running Tests

```bash
# All tests
uv run pytest

# Specific test types
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m security

# With coverage
uv run pytest --cov=app --cov-report=term-missing
```

### Code Quality

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy app/

# Pre-commit
uv run pre-commit run --all-files
```

### Database Operations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Show current revision
alembic current

# Show history
alembic history
```

## Environment Profiles

| Environment | `ENVIRONMENT` | `DEBUG` | Use Case |
|-------------|---------------|---------|----------|
| Local | `local` | `true` | Development |
| Development | `development` | `true` | Shared dev environment |
| Staging | `staging` | `false` | Pre-production |
| Production | `prod` | `false` | Production |

## Configuration Reference

Key settings in `app/core/config.py`:

```python
# Database
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
DATABASE_URL (full asyncpg DSN, overrides components)

# Security
SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
JWT_PRIVATE_KEY_PATH, JWT_PUBLIC_KEY_PATH (for RS256)

# Email
EMAIL_PROVIDER=smtp|brevo|sendgrid|ses|log
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

# Storage
STORAGE_PROVIDER=local|minio|s3|gcs|azure
LOCAL_STORAGE_PATH, MINIO_ENDPOINT, MINIO_ACCESS_KEY, ...

# AI
AI_PROVIDER=openai|anthropic|google|groq|mistral
OPENAI_API_KEY, ANTHROPIC_API_KEY, ...

# Observability
OTEL_ENABLED, OTEL_EXPORTER_OTLP_ENDPOINT
SENTRY_DSN
```

## Next Steps

1. Read [Architecture](architecture.md) for design principles
2. Read [Configuration](configuration.md) for all settings
3. Read [Module Development](module-development.md) to create modules
4. Read [Integrations](integrations.md) for email/storage/AI setup
5. Read [Testing](testing.md) for test strategies
6. Read [Deployment](deployment.md) for production deployment