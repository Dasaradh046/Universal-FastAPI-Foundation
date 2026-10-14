# Universal FastAPI Foundation - Improved Version

This is an enhanced version of the Universal FastAPI Foundation with production-ready improvements including SOLID principles, OOP concepts, design patterns, and security best practices.

## Features

- **Production Ready**: Enhanced error handling, validation, and security
- **SOLID Principles**: Proper application of all five SOLID principles
- **Dependency Injection**: Throughout the codebase for better testability
- **Modular Architecture**: Easy to add new modules
- **Multi-tenancy Support**: Built-in tenant context handling
- **Audit Trail**: Comprehensive audit logging for compliance
- **Health Checks**: Ready for Kubernetes deployment
- **UUID Primary Keys**: Globally unique identifiers for all entities
- **Pydantic v2**: Modern data validation and serialization
- **Async/Await**: Full asynchronous I/O for better performance

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- uv (recommended) or pip
- Docker (optional, for containerized development)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd universal-fastapi-foundation
   ```

2. **Install Dependencies**
   ```bash
   # Using uv (recommended)
   uv sync --all-extras
   
   # Or using pip
   pip install -e ".[dev,mfa,email,storage,ai,observability]"
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start Database**
   ```bash
   # Using Docker Compose
   docker compose up -d postgres
   
   # Or use your existing PostgreSQL instance
   ```

5. **Run Migrations**
   ```bash
   # Create initial migration (if needed)
   alembic revision --autogenerate -m "initial"
   
   # Apply migrations
   alembic upgrade head
   ```

6. **Start Application**
   ```bash
   # Development
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or directly
   python -m app.main
   ```

7. **Verify**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health
   - Detailed Health: http://localhost:8000/health/detailed

## Module Structure

The foundation follows a modular architecture where each module contains:

- `router.py` - API endpoints
- `schemas.py` - Pydantic models for validation
- `models.py` - SQLAlchemy ORM models
- `repository.py` - Data access layer
- `service.py` - Business logic layer
- `dependencies.py` - FastAPI dependency providers
- `permissions.py` - Module-specific permissions
- `events.py` - Domain events (optional)
- `migrations/` - Alembic migration files

## Running Tests

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

## Documentation

- [Architecture](docs/architecture.md) - Design principles and structure
- [Configuration](docs/configuration.md) - All available settings
- [Getting Started](docs/getting-started.md) - Setup and usage guide
- [Module Development](docs/module-development.md) - Creating new modules
- [Integrations](docs/integrations.md) - Third-party service integration
- [Testing](docs/testing.md) - Testing strategies and practices
- [Deployment](docs/deployment.md) - Deployment guides and best practices

## Key Improvements

See [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) for detailed information about the enhancements made to make this foundation production-ready.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.