# Architecture Overview

Universal FastAPI Foundation (UBF) is a reusable, integration-ready FastAPI application platform built on SOLID principles, clean architecture, and dependency injection.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Modules   │  │   Shared    │  │ Integrations│             │
│  │  (Business) │  │  Services   │  │  (Adapters) │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
├─────────┼────────────────┼────────────────┼────────────────────┤
│         │                │                │                    │
│  ┌──────▼────────────────▼────────────────▼──────┐            │
│  │                  Core Platform                │            │
│  │  Config │ Database │ Security │ Lifecycle    │            │
│  │  Logging│ Middleware│ Exceptions│ Health     │            │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

| Layer | Responsibility | Must Not |
|-------|----------------|----------|
| **Router** | HTTP methods, paths, status codes, request/response schemas | Contain business workflows or SQL queries |
| **Dependencies** | Inject sessions, authenticated principals, permissions, request-scoped context | Become an alternative business logic layer |
| **Service** | Business rules, transactions, orchestration, domain validation | Depend directly on HTTP request objects |
| **Repository** | Encapsulate database queries and persistence operations | Make authorization decisions |
| **Models** | Represent persistence entities and relationships | Become public API schemas automatically |
| **Schemas** | Validate requests and define response contracts | Expose database-only fields unintentionally |
| **Core** | Configuration, security, lifecycle, logging, database, shared infrastructure | Accumulate unrelated business features |
| **Shared Services** | Reusable capabilities (files, audit, notifications, jobs) | Become an unstructured dumping ground |

## Request Flow

```
HTTP Request
    │
    ▼
┌─────────────┐
│  Middleware │  ──► Correlation ID, Logging, Rate Limiting, CORS
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Router    │  ──► Path/Method matching, Request validation (Pydantic)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Dependencies│  ──► DB Session, Auth User, Permissions, Tenant Context
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service   │  ──► Business Logic, Transactions, Orchestration
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Repository  │  ──► Database Queries, Persistence
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Database   │  ──► PostgreSQL (asyncpg)
└─────────────┘
```

## Core Components

### Configuration (`app/core/config.py`)
- Pydantic Settings v2 for type-safe configuration
- Environment variable loading with validation
- Support for `.env` files
- Derived properties for database URLs, CORS origins, etc.

### Database (`app/core/database.py`)
- Async SQLAlchemy 2.x with asyncpg
- Connection pooling with NullPool for testing
- Session lifecycle management
- Engine disposal on shutdown

### Security (`app/core/security.py`)
- JWT token creation and validation
- Password hashing with bcrypt
- Token blacklist for logout/revocation
- MFA/TOTP support

### Permissions (`app/core/permissions.py`)
- Role-based access control (RBAC)
- Permission-based authorization
- Tenant isolation enforcement

### Lifecycle (`app/core/lifespan.py`)
- FastAPI lifespan handlers for startup/shutdown
- Database engine initialization/disposal
- Redis/client initialization

## Module Architecture

Each module follows the same structure:

```
modules/
└── example_module/
    ├── __init__.py           # Module registration
    ├── router.py             # HTTP endpoints
    ├── schemas.py            # Request/Response models
    ├── models.py             # SQLAlchemy models
    ├── repository.py         # Data access
    ├── service.py            # Business logic
    ├── dependencies.py       # Module-specific dependencies
    ├── permissions.py        # Module permissions
    ├── events.py             # Domain events
    └── migrations/           # Module-specific migrations
```

## Integration Architecture

Integrations follow the Adapter pattern with common contracts:

```
┌──────────────────┐     ┌──────────────────┐
│  Business Code   │────►│  Integration     │
│  (EmailService)  │     │  Contract        │
└──────────────────┘     │  (EmailSender)   │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
       │  SMTP       │    │  Brevo      │    │  SendGrid   │
       │  Adapter    │    │  Adapter    │    │  Adapter    │
       └─────────────┘    └─────────────┘    └─────────────┘
```

## Multi-Tenancy

- Optional tenant strategy (single-tenant by default)
- Shared database with tenant_id column + Row-Level Security
- Tenant context propagated via dependencies
- Cross-tenant isolation tests included

## Observability

- Structured JSON logging (production)
- Request ID / Correlation ID propagation
- Prometheus metrics
- OpenTelemetry traces (optional)
- Health checks (liveness/readiness)
- Sentry integration (optional)