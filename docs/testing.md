# Testing Strategy

Universal FastAPI Foundation provides a comprehensive testing strategy that follows the test pyramid principle, ensuring quality at every level.

## Test Pyramid

The foundation enforces a standard test pyramid with the following layers:

```
                                🔺 UI/E2E Tests
                             🔺 Contract Tests
                          🔺 API/Integration Tests
                       🔺 Service Tests
                    🔺 Repository Tests
                 🔺 Unit Tests
```

## 8. Automated test strategy for every generated backend

The reusable foundation should provide a testing toolkit and enforce a standard test pyramid.

| Test layer          | Scope                                       | Example                                                |
|---------------------|---------------------------------------------|--------------------------------------------------------|
| Unit                | Isolated domain behavior                    | Salary calculation, order total, validation rules      |
| Service             | Business workflows and transaction behavior | Employee creation, inventory reservation               |
| Repository/database | SQL, constraints, indexes and persistence   | Unique email, foreign-key constraints                  |
| API integration     | Request-to-response behavior                | CRUD, filters, pagination and status codes             |
| Security            | Authentication and authorization            | Expired JWT, missing permission, tenant mismatch       |
| Contract            | API schema and compatibility                | OpenAPI response schema, error contract                |
| Architecture        | Module boundaries and dependency rules      | No forbidden cross-module imports                      |
| End-to-end          | Complete user/business workflow             | Create record, approve it, verify final state          |
| Performance         | Latency, throughput and resource usage      | Endpoint benchmark and concurrency ramp                |
| Resilience          | Failure handling and recovery               | Database disconnect, slow dependency, retry exhaustion |

### 8.1 Required test cases per CRUD module

For a typical resource such as employees, customers, or inventory:

- Create valid record.
- Reject invalid payloads and missing required fields.
- Reject duplicate values where uniqueness applies.
- Read by ID and list records.
- Validate pagination, filters, sorting and maximum page size.
- Update valid fields and reject invalid transitions.
- Delete or deactivate according to the domain's deletion policy.
- Return correct 404 behavior for missing or inaccessible resources.
- Reject unauthenticated and unauthorized requests.
- Verify tenant isolation where enabled.
- Test database constraint failures and rollback.
- Test concurrent updates where lost updates or conflicting changes are possible.
- Verify that audit records and events are created when required.
- Verify response schemas do not expose internal fields.
- Test repeated requests and idempotency where applicable.

### 8.2 Test infrastructure and quality gates

Use `pytest`, `pytest-asyncio`, and HTTPX as the baseline. Provide fixtures for database sessions, test users, permissions, tenant contexts and test data.

Recommended conventions:

- Separate unit, integration, API, security, slow and end-to-end markers.
- Run fast tests on every pull request.
- Run database and integration tests in CI against a real PostgreSQL service or isolated container.
- Validate Alembic migrations from a clean database.
- Run a branch-coverage report, initially targeting at least 80% overall, with stricter requirements for critical security and business rules.
- Run linting, formatting, static typing, dependency checks and architecture checks.
- Keep tests deterministic by controlling time, randomness and external dependencies.
- Use disposable test databases and synthetic datasets.
- Run performance tests on a controlled schedule or dedicated environment, rather than treating noisy benchmarks as ordinary unit tests.

Coverage is a signal, not proof of correctness. Critical paths require explicit tests even if the global coverage threshold is met.

## Test Configuration

### pytest configuration (`pyproject.toml`)

```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-v",
    "--strict-markers",
    "--disable-warnings",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "api: API tests",
    "security: Security tests",
    "contract: Contract tests",
    "architecture: Architecture tests",
    "e2e: End-to-end tests",
    "performance: Performance tests",
    "slow: Slow tests",
]
```

### Test fixtures

The foundation provides reusable fixtures for:

- Database sessions
- Test users and authentication
- Permissions and tenant contexts
- Test data factories
- Mock integrations (email, storage, AI providers)
- Test clients

Example fixture structure:

```python
# tests/conftest.py
import pytest
from app.core.config import get_settings, Settings
from app.core.database import get_db, engine, Base
from httpx import AsyncClient

@pytest.fixture
def test_settings():
    return Settings(
        ENVIRONMENT="local",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
        SECRET_KEY="test-secret-key-for-testing-only-32-chars",
    )

@pytest.fixture
async def db_session(test_settings):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            async with Session(engine) as session:
                yield session
        finally:
            await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

## Test Organization

```
tests/
├── unit/                 # Isolated domain logic tests
│   ├── test_salary_calculation.py
│   └── test_validation_rules.py
├── integration/          # Database and service tests
│   ├── test_user_service.py
│   └── test_inventory_repository.py
├── api/                  # API endpoint tests
│   ├── test_users_endpoints.py
│   └── test_inventory_endpoints.py
├── security/             # Authentication and authorization tests
│   ├── test_jwt_validation.py
│   └── test_permissions.py
├── contract/             # API schema and compatibility tests
│   └_test_openapi_schema.py
├── architecture/         # Module boundary and dependency tests
│   └_test_forbidden_imports.py
└── e2e/                  # End-to-end workflow tests
    ├── test_user_registration_flow.py
    └── test_order_processing_flow.py
```

## Performance Testing

Performance testing uses existing tools such as Locust or k6 rather than building custom solutions.

### Locust Integration

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_users(self):
        self.client.get("/api/v1/users")
    
    @task
    def create_user(self):
        self.client.post("/api/v1/users", json={
            "name": "Test User",
            "email": "test@example.com"
        })
```

### k6 Integration

```javascript
// tests/performance/k6-script.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 }, // ramp up
    { duration: '5m', target: 100 }, // stay at 100
    { duration: '2m', target: 0 },   // ramp down
  ],
};

export default function () {
  const res = http.get('http://localhost:8000/api/v1/users');
  check(res, {
    'status was 200': (r) => r.status == 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

## Test Execution

### Running Tests

```bash
# All tests
uv run pytest

# Specific test types
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m security
uv run pytest -m contract
uv run pytest -m architecture

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Performance tests (Locust)
uv run locust -f tests/performance/locustfile.py --host http://localhost:8000

# Performance tests (k6)
uv run k6 run tests/performance/k6-script.js
```

## Quality Gates

The foundation includes automated quality gates in CI/CD pipelines:

1. **Fast feedback loop** (on every push):
   - Unit tests
   - Linting (Ruff)
   - Type checking (mypy/Pyright)
   - Security scanning (Bandit)

2. **Extended validation** (on pull requests):
   - Integration tests
   - Contract tests
   - Architecture tests
   - Dependency vulnerability scanning

3. **Release validation** (on releases to main):
   - Full test suite
   - Performance tests
   - Security scans
   - Container scanning

## Best Practices

1. **Keep tests deterministic** - Control time, randomness and external dependencies
2. **Use descriptive test names** - Follow given/when/then format
3. **Test at the right level** - Unit tests for domain logic, integration tests for external interactions
4. **Mock external services** - Use fakes/mocks for email, storage, AI providers
5. **Test error conditions** - Validate proper error handling and validation
6. **Maintain test isolation** - Each test should be able to run independently
7. **Update tests with changes** - Keep tests in sync with implementation changes
8. **Test security scenarios** - Include authentication, authorization and input validation tests