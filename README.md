# Universal FastAPI Foundation

A reusable, integration-ready FastAPI application platform designed to serve as a foundation for building various business applications.

## Overview

The Universal FastAPI Foundation provides a solid foundation for building backend applications with:

- Modular architecture with pluggable modules
- Integration adapters for common services (email, storage, AI, etc.)
- Standardized API patterns and conventions
- Comprehensive testing infrastructure
- DevOps and CI/CD integration
- Docker-based deployment
- Multi-tenancy support
- Security-first approach
- Observability integration

## Features

- **Modular Architecture**: Clean separation of concerns with reusable modules
- **Integration Hub**: Standardized interfaces for email, SMS, storage, AI providers, and external APIs
- **Developer Toolchain**: Pre-configured testing, linting, type checking, and code quality tools
- **Operations Ready**: Logging, metrics, tracing, health checks, and operational documentation
- **Security First**: Authentication, authorization, input validation, and secure defaults
- **Performance Oriented**: Designed for scalability with async support and connection pooling
- **Multi-tenancy**: Built-in support for tenant isolation using PostgreSQL Row-Level Security
- **Observability**: Integrated logging, metrics, and tracing with OpenTelemetry support

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Docker and Docker Compose (optional, for containerized deployment)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/universal-fastapi-foundation.git
   cd universal-fastapi-foundation
   ```

2. Install dependencies using uv:
   ```bash
   pip install uv
   uv sync
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. For production use, generate cryptographic keys:
   ```bash
   python scripts/generate_keys.py
   ```

5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```

6. Run the application:
   ```bash
   uvicorn apps.api.app.main:app --reload
   ```

### Running with Docker Compose

```bash
docker-compose up --build
```

The API will be available at http://localhost:8000

## API Documentation

Once the application is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
universal-fastapi-foundation/
├── apps/
│   └── api/
│       └── app/
│           ├── main.py              # Application entry point
│           ├── api/                 # API routers
│           ├── core/                # Core functionality (config, database, security, etc.)
│           ├── integrations/        # Third-party service integrations
│           ├── shared/              # Shared business-neutral capabilities
│           ├── modules/             # Business modules
│           └── tests/               # Application tests
├── packages/                        # Shared packages
├── tooling/                         # Developer tooling configurations
├── migrations/                      # Database migrations
├── config/                          # Configuration files
├── docs/                            # Documentation
├── scripts/                         # Utility scripts
├── keys/                            # Cryptographic keys (generated)
├── logs/                            # Application logs
├── uploads/                         # File uploads
└── tests/                           # Project-wide tests
```

## Making Your First API Request

```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "message": "Universal FastAPI Foundation",
  "version": "0.1.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

## Testing

Run the test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=apps
```

## Key Generation

The foundation includes a script to generate cryptographic keys:

```bash
python scripts/generate_keys.py
```

This will generate:
1. A strong secret key for HS256 JWT signing
2. An RSA keypair for RS256 JWT signing (more secure)
3. A Fernet key for field-level encryption

The keys are added to your `.env` file automatically.

## Email Integration

The foundation includes an email integration layer with support for:
- SMTP (standard email protocol)
- Brevo (transactional email service)
- SendGrid (email delivery service)
- Amazon SES (AWS email service)
- Logging (development mode that logs instead of sending)

To configure email, set the `EMAIL_PROVIDER` environment variable and provide the necessary credentials.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For support, please open an issue in the repository.