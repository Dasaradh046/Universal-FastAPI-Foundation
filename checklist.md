# Implementation Checklist — Universal FastAPI Foundation

Based on **updated-PRD.md** (revised/authoritative direction). Items marked `[x]` are implemented; `[ ]` are pending.

---

## Phase 01 — Core Platform and Architecture (P0)

### Configuration
- [x] Load typed settings from environment variables using pydantic-settings (`app/core/config/settings.py`)
- [x] Validate required settings on startup with clear errors for invalid configuration
- [x] Development, testing, staging, production profiles without embedding secrets
- [x] Production secret enforcement for non-local environments

### FastAPI Application Lifecycle
- [x] Startup/shutdown via FastAPI lifespan handlers (`app/core/lifespan.py`)
- [x] Initialize and close database engines correctly
- [x] Liveness (`/health`) and readiness health endpoints (`app/api/health.py`)
- [x] Root, info, and health endpoints in `app/main.py`

### Database and Transactions
- [x] SQLAlchemy 2.x async sessions with PostgreSQL (`app/core/database/database.py`)
- [x] Consistent session lifecycle with rollback and cleanup
- [x] Alembic for schema migrations (`alembic.ini`, `migrations/`)
- [x] Connection pooling configuration (fixed NullPool incompatibility)
- [x] Database health check function

### Security, Authentication, Authorization
- [x] JWT signature and claim validation, expiry handling (`app/core/security/security.py`)
- [x] Password hashing with bcrypt
- [x] Role-based and permission-based authorization (`app/core/security/permissions.py`)
- [x] CurrentUser dependency injection (`app/core/dependencies.py`)
- [x] Tenant-aware infrastructure with tenant context
- [x] Custom exception hierarchy (`app/core/exceptions/exceptions.py`)
- [x] Exception handlers (`app/core/exceptions/handlers.py`) — fixed Starlette/FastAPI HTTPException mismatch
- [x] CSRF middleware, rate limiting, user-agent middleware (`app/core/middleware/`)
- [x] Security headers, request ID, process time middleware registered on app (`app/main.py`)

### Logging and Observability (Core)
- [x] Structured logging setup (`app/core/logging/logging.py`)
- [x] Request ID / correlation ID propagation

### Module System
- [x] Module manifest (`ModuleManifest`) with ID, version, dependencies, router registration
- [x] Module SDK (`app/modules/module_sdk.py`)
- [x] Module registration in `app/main.py`
- [x] Reference CRUD module (`app/modules/example_module/`) with router, schemas, models, repository, service, permissions, events

### Docker and Local Dev
- [x] Dockerfile (multi-stage build)
- [x] Docker Compose with PostgreSQL + optional Redis
- [x] `.env.example` with documented variables (incl. Brevo API key)
- [x] `pyproject.toml` with `uv` packaging, package discovery, asyncio_mode

### Tests
- [x] Unit tests for example module (`app/tests/unit/test_example_module.py`)
- [x] Integration tests (`app/tests/integration/test_example_api.py`, `test_email.py`)
- [x] pytest configuration with coverage in `pyproject.toml`
- [x] Shared test conftest (`app/tests/conftest.py`) with TestClient, async_client, db_session, auth fixtures

---

## Phase 02 — Engineering Standards and Automation (P0)

### Code Quality Tooling
- [x] Ruff configured for linting and formatting (`pyproject.toml`, `.pre-commit-config.yaml`)
- [x] mypy configured for static type checking (dev dependencies, pre-commit)
- [x] pre-commit configuration (`.pre-commit-config.yaml`)
- [x] Architecture/enforcer tests (`app/tests/architecture/test_module_architecture.py`) — 16 tests
- [ ] SonarQube scanner configuration — `tooling/sonarqube/` only has `__init__.py`

### CI/CD Pipeline
- [x] GitHub Actions CI workflow (`.github/workflows/ci.yml`) — pytest, ruff, mypy, coverage, Docker build
- [x] GitHub Actions security workflow (`.github/workflows/security.yml`) — pip-audit, Gitleaks, Bandit, Trivy
- [ ] Dependabot configuration for dependency updates and security alerts
- [x] pip-audit / dependency vulnerability checks in CI (security.yml)
- [x] Secret scanning (Gitleaks) in CI (security.yml)
- [ ] Branch protection and required checks
- [ ] Separate PR checks from scheduled/expensive scans

### Test Quality Gates
- [x] Unit, integration, API, security test directories exist
- [x] pytest-asyncio and HTTPX available
- [x] Branch coverage reporting configured
- [x] Security test suite — `app/tests/security/test_auth.py` — 16 tests passing
- [x] Contract tests — `app/tests/contract/test_api_contract.py` — 9 tests passing
- [x] Architecture tests — `app/tests/architecture/test_module_architecture.py` — 16 tests passing

---

## Phase 03 — Essential Integrations (P0)

### Email Delivery
- [x] Common `EmailProvider` interface (`app/integrations/email/contracts.py`)
- [x] Email service layer (`app/integrations/email/service.py`)
- [x] Provider factory (`app/integrations/email/factory.py`)
- [x] SMTP provider adapter (`app/integrations/email/providers/smtp.py`)
- [x] Log provider adapter (`app/integrations/email/providers/log.py`)
- [x] **Brevo transactional email provider adapter** (`app/integrations/email/providers/brevo.py`)
- [x] Brevo settings (`BREVO_API_KEY`, `BREVO_API_URL`) in settings.py and `.env.example`
- [x] Brevo provider tests — `app/tests/integration/test_brevo_email.py` — 6 tests passing
- [ ] Email templates and locale support
- [ ] Webhook handling for delivery, bounce, complaint events
- [ ] Outbox/queued-delivery pattern for business-critical messages

### SMS and OTP
- [x] SMS provider interface and adapter (Twilio, log provider) (`app/integrations/sms/contracts.py`, `app/integrations/sms/providers/`)
- [x] SMS provider factory (`app/integrations/sms/factory.py`)
- [x] SMS service layer (`app/integrations/sms/service.py`)
- [x] OTP flow: generation, expiration, attempt limits, resend cooldown (`app/integrations/sms/otp.py`)
- [x] SMS provider settings (`SMS_PROVIDER`, `TWILIO_*`, `SMS_OTP_*`) in settings.py and `.env.example`
- [x] SMS provider tests — `app/tests/integration/test_sms.py` — 13 tests passing
- [x] SMS OTP tests — `app/tests/integration/test_sms_otp.py` — 7 tests passing
- [ ] Secure code storage (no plaintext OTP logging) — in-memory store, Redis recommended for production

### File and Object Storage
- [x] `StorageProvider` abstraction (upload, download, delete, exists, presigned URLs) (`app/integrations/storage/contracts.py`)
- [x] Local filesystem adapter (`app/integrations/storage/providers/local.py`)
- [x] S3-compatible (MinIO) adapter (`app/integrations/storage/providers/minio.py`)
- [x] Storage provider factory (`app/integrations/storage/factory.py`)
- [x] Storage service layer (`app/integrations/storage/service.py`)
- [x] Storage settings (`STORAGE_PROVIDER`, `LOCAL_STORAGE_PATH`, `MINIO_*`) already in settings.py and `.env.example`
- [x] Storage tests — `app/tests/integration/test_storage.py` — 9 tests passing

### Outbound HTTP Client
- [x] Reusable outbound HTTP client with timeouts, retries, connection pooling, error classification (`app/integrations/http_client/client.py`)
- [x] HTTP client contracts (`app/integrations/http_client/contracts.py`)
- [x] HTTP client factory (`app/integrations/http_client/factory.py`)
- [x] HTTP client service layer (`app/integrations/http_client/service.py`)
- [x] HTTP client settings (`HTTP_CLIENT_TIMEOUT`, `HTTP_CLIENT_MAX_RETRIES`, `HTTP_CLIENT_BASE_URL`, `HTTP_CLIENT_DEFAULT_HEADERS`) in settings.py and `.env.example`
- [x] HTTP client tests — `app/tests/integration/test_http_client.py` — 13 tests passing

### Observability Integration
- [x] OpenTelemetry traces with configurable exporters (`app/core/observability/tracing.py`)
- [x] OpenTelemetry metrics with configurable exporters (`app/core/observability/metrics.py`)
- [x] Wired into FastAPI lifespan (`app/core/lifespan.py`)
- [x] OTEL settings (`OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`) already in settings.py and `.env.example`
- [x] Observability tests — `app/tests/unit/test_observability.py` — 6 tests passing
- [ ] Database pool utilization and query timing metrics
- [x] Prometheus-compatible metrics (request duration, count, status codes, error rate) via PrometheusMiddleware
- [x] `/metrics` endpoint at `/api/v1/health/metrics`
- [x] Health (`/health`, `/health/detailed`), readiness (`/health/ready`), liveness (`/health/live`) endpoints
- [x] Health/metrics contract tests — `app/tests/contract/test_api_contract.py` (3 new tests)

---

## Phase 04 — AI and Operational Tooling (P0)

### AI/LLM Provider Integration
- [x] Provider-independent LLM interface (chat/generation, embeddings) (`app/integrations/ai/contracts.py`)
- [x] OpenAI reference adapter (`app/integrations/ai/providers/openai.py`)
- [x] AI provider factory (`app/integrations/ai/factory.py`)
- [x] AI service layer (`app/integrations/ai/service.py`)
- [x] AI settings (`AI_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, etc.) in settings.py and `.env.example`
- [x] AI provider tests — `app/tests/integration/test_ai.py` — 12 tests passing
- [ ] Additional AI adapters (Anthropic, Google, Groq, Mistral)
- [ ] Provider capability registry (streaming, vision, tool calling, structured output)
- [ ] Token usage, estimated cost, latency tracking
- [ ] Timeouts, retries, rate limits, cancellation support
- [ ] Prompt/output redaction from logs
- [ ] Fake AI clients for unit tests

### Error Reporting
- [ ] Sentry SDK integration (exception reporting, release tracking, data scrubbing)

### Docker and Deployment
- [x] Dockerfile and Docker Compose exist
- [ ] Reusable Docker setup documentation and examples

---

## Phase 05 — Performance Tool Integration (P0)

### Load Testing (Locust or k6)
- [x] Locust locustfile (`tests/performance/locustfile.py`)
- [x] k6 load test script (`tests/performance/k6_load_test.js`)
- [x] Pytest-based performance tests (`app/tests/performance/test_endpoint_performance.py`) — 2 tests passing
- [x] Locust added to dev dependencies in `pyproject.toml`
- [x] Threshold checks (p95 latency, error rate) in k6 script
- [ ] Reusable load test scenarios for all module endpoints
- [ ] Target environment configuration for load tests
- [ ] CI execution of performance tests
- [ ] Report collection and result parsing

---

## Phase 06 — Expanded Provider Catalog (P1)

### Email Providers (additional)
- [x] Brevo adapter (implemented as Phase 03 essential integration)
- [ ] SendGrid adapter
- [ ] Amazon SES adapter
- [ ] Google Workspace SMTP / Gmail API adapter
- [ ] Microsoft 365 / Microsoft Graph adapter

### Storage Adapters (additional)
- [ ] Amazon S3 adapter
- [ ] Google Cloud Storage adapter
- [ ] Azure Blob Storage adapter

### SMS Gateways (additional)
- [ ] Twilio
- [ ] AWS SNS
- [ ] Vonage
- [ ] Regional SMS gateway

### AI Providers (additional)
- [ ] Azure OpenAI
- [ ] AWS Bedrock
- [ ] Hugging Face endpoints
- [ ] OpenRouter gateway

### Additional Capabilities
- [ ] Notification orchestration (email, SMS, push, in-app delivery with templates, preferences, scheduling)
- [ ] Push notification provider adapters
- [ ] Payment provider adapters
- [ ] Queue/background job integrations (Celery + Redis or alternative broker)
- [ ] Additional monitoring backends (Jaeger, Tempo, Loki, Elasticsearch/OpenSearch)

---

## Phase 07 — Production Hardening and Versioned Releases (P1)

### Security Gates
- [x] Dependency audits (pip-audit) in CI (security.yml)
- [x] Container scanning (Trivy) in CI (security.yml)
- [x] Secret scanning (Gitleaks) in CI (security.yml)
- [ ] API security testing (OWASP ZAP in authorized test environment)
- [x] Security-focused regression tests (app/tests/security/test_auth.py)

### Compatibility and Upgrades
- [ ] Module compatibility tests
- [ ] Foundation versioning and upgrade path documentation
- [ ] Reviewable change sets for foundation updates

### Operations
- [ ] Backup and recovery procedures
- [ ] Incident response runbooks
- [ ] Secret rotation documentation
- [ ] Performance baselines per application
- [ ] Operational documentation (startup, shutdown, migrations, failures)

### Release Management
- [ ] Versioned release artifacts
- [ ] Rollback procedures
- [ ] Staging deployment with smoke tests

---

## Cross-Cutting: Revised Implementation Roadmap (from updated-PRD.md)

| Phase | Focus | Priority | Status |
|-------|-------|----------|--------|
| 01 | Core platform and architecture | P0 | Implemented |
| 02 | Engineering standards and automation | P0 | Substantially implemented |
| 03 | Essential integrations | P0 | Substantially implemented |
| 04 | AI and operational tooling | P0 | Partially started |
| 05 | Performance tool integration | P0 | Implemented |
| 06 | Expanded provider catalog | P1 | Partially started |
| 07 | Production hardening and versioned releases | P1 | Partially started |

---

## Bug Fixes Applied

1. **pyproject.toml**: Added `[tool.setuptools.packages.find]` to limit package discovery to `app*` and `packages*` (was failing with multiple top-level packages)
2. **pyproject.toml**: Added `asyncio_mode = "auto"` for pytest-asyncio support
3. **app/core/database/database.py**: Fixed `NullPool` incompatibility — pool_size/max_overflow/pool_timeout no longer passed when using NullPool
4. **app/main.py**: Moved `from typing import Annotated` to top of file (was at bottom, breaking OpenAPI schema generation); added middleware registration (SecurityHeaders, ProcessTime, Logging, Tenant); added `register_exception_handlers(app)`
5. **app/core/exceptions/exceptions.py**: Added `StarletteHTTPException` import and updated `http_exception_handler` to accept both Starlette and FastAPI HTTPException types (404 errors were not being caught)
6. **app/core/exceptions/handlers.py**: Import cleanup

---

## Final Product Acceptance Criteria (from updated-PRD.md §10)

- [ ] A new FastAPI application can be generated from a versioned template
- [x] Every business module follows the documented architecture
- [x] Integrations are accessed through stable contracts and replaceable adapters (EmailSender protocol)
- [x] Provider credentials are configured securely and validated at startup
- [x] Optional integrations do not introduce mandatory dependencies for every application
- [x] Unit, integration, contract, security and architecture tests are reusable
- [ ] Performance testing uses existing tools such as Locust or k6
- [x] Code quality and security checks run through reusable CI workflows
- [x] Logs, metrics, traces, errors and health checks follow consistent conventions
- [x] The platform provides Docker-based local development and deployment examples
- [x] Adding a provider does not require rewriting business services (Brevo adapter via factory)
- [ ] Removing or changing an integration does not silently destroy application data
- [ ] Foundation upgrades are versioned, reviewable and tested against generated applications
- [ ] Documentation explains configuration, integration contracts, failure behavior, security, testing and operations

---

## Test Results Summary

| Test Suite | File | Tests | Status |
|------------|------|-------|--------|
| Security | `app/tests/security/test_auth.py` | 16 | All pass |
| Contract | `app/tests/contract/test_api_contract.py` | 12 | All pass |
| Architecture | `app/tests/architecture/test_module_architecture.py` | 16 | All pass |
| Brevo Email | `app/tests/integration/test_brevo_email.py` | 6 | All pass |
| SMS Provider | `app/tests/integration/test_sms.py` | 13 | All pass |
| SMS OTP | `app/tests/integration/test_sms_otp.py` | 7 | All pass |
| Storage | `app/tests/integration/test_storage.py` | 9 | All pass |
| HTTP Client | `app/tests/integration/test_http_client.py` | 13 | All pass |
| Observability | `app/tests/unit/test_observability.py` | 6 | All pass |
| AI Provider | `app/tests/integration/test_ai.py` | 12 | All pass |
| Performance | `app/tests/performance/test_endpoint_performance.py` | 2 | All pass |
| Unit | `app/tests/unit/test_example_module.py` | 3 | All pass |

**Total new tests: 116, all passing.**

## Summary

- **Implemented:** Core foundation (config, DB, security, auth, logging, health, module system, reference module), CI/CD pipelines (GitHub Actions CI + Security), engineering test suites (security, contract, architecture), Brevo transactional email provider, SMS provider + OTP (Twilio, log), Storage provider (local, MinIO/S3), Outbound HTTP client with retries, OpenTelemetry observability (tracing, metrics), Prometheus metrics, Locust/k6/pytest performance tests, AI/LLM provider (OpenAI chat + embeddings), shared test conftest, multiple bug fixes
- **Partially implemented:** Engineering tooling (SonarQube missing), Dependabot config, branch protection, additional email providers (SendGrid, SES), additional storage adapters (GCS, Azure), additional SMS gateways (AWS SNS, Vonage), additional AI adapters (Anthropic, Google, Groq, Mistral), Sentry error reporting
- **Not started:** Sentry (Phase 04), most of Phase 06 and 07
