# Deployment Guide

Universal FastAPI Foundation provides consistent deployment practices using Docker Compose for local development and GitHub Actions for CI/CD, supporting repeatable local development, CI/CD, Docker deployment and production operations.

## 9. Developer experience: how you will build future applications

### 9.1 Proposed project creation workflow

The foundation should not only contain reusable code. It should make the workflow for starting a new project predictable and fast.

### 9.2 CLI requirements

Develop a CLI after the underlying contracts are stable. A possible command interface is:

```
# Create a new backend project
ubp new my-crm

# Validate the project and module manifests
ubp validate

# Inspect enabled modules and their dependencies
ubp modules list

# Add a module from the approved module catalog
ubp modules add customers

# Generate and validate database migrations
ubp db migrate

# Run selected test suites
ubp test unit
ubp test security
ubp test integration

# Run the project's performance test suite
ubp perf run --suite baseline

# Produce a project quality report
ubp report
```

### 9.3 Project configuration

The generator should produce a validated application manifest that records:

- Application name, version and environment.
- Enabled modules and their versions.
- Module dependencies and configuration.
- Database and cache choices.
- Authentication and tenancy modes.
- API prefix and version.
- Testing profiles and performance thresholds.
- Required environment variables.
- Migration and deployment settings.

Secrets must be referenced through environment variables or secret managers, not committed to the manifest.

### 9.4 Generation and update rules

The generator must distinguish between generated files, application-owned files and platform-owned files.

- A new application starts from a pinned, versioned foundation release.
- Generated modules are explicit and traceable.
- Updating the foundation must produce a reviewable change set.
- Existing business logic must not be silently overwritten.
- Schema changes require migrations and approval.
- Removed modules must not automatically delete their data.
- Each project must be able to identify its foundation version and supported upgrade path.

Initially, prefer a versioned template plus shared packages over a complicated runtime plugin marketplace. This reduces coupling and makes applications easier to debug and deploy.

## 5. CI/CD and DevSecOps integration

The foundation should ship with reusable CI/CD workflows and security configurations, so each generated application inherits a consistent engineering pipeline.

### 5.1 Developer toolchain

| Tool            | Purpose                                         | Integration approach                                 |
|-----------------|-------------------------------------------------|------------------------------------------------------|
| GitHub Actions  | CI/CD automation                                | Reusable workflow files and composite actions        |
| Dependabot      | Dependency update proposals and security alerts | Repository configuration and automated pull requests |
| SonarQube       | Static analysis and quality gates               | Scanner configuration and pipeline gate              |
| Snyk            | Security vulnerability analysis                 | CLI or supported CI integration                      |
| Ruff            | Python formatting and linting                   | Local development and CI                             |
| mypy or Pyright | Static type checking                            | CI quality gate                                      |
| pytest          | Automated testing                               | Standardized test commands and reports               |
| pip-audit       | Python dependency vulnerability checks          | CI dependency audit                                  |
| Trivy           | Container and configuration scanning            | Image-build pipeline                                 |
| Gitleaks        | Secret detection                                | Pre-commit and CI checks                             |
| pre-commit      | Consistent developer checks                     | Shared repository configuration                      |
| Docker          | Reproducible application packaging              | Standardized Dockerfile and Compose setup            |

### 5.2 Recommended CI/CD pipeline

The foundation provides reusable GitHub Actions workflows for:

1. **Pull Request Validation** (on every PR)
   - Dependency installation
   - Linting (Ruff)
   - Formatting check
   - Type checking (mypy/Pyright)
   - Unit tests
   - Security scanning (Bandit, pip-audit)
   - Dependency vulnerability scanning (Dependabot alerts)
   - Secret scanning (Gitleaks)

2. **Extended Validation** (on PR to main/develop)
   - Everything from PR validation plus:
   - Integration tests
   - Contract tests
   - Architecture tests
   - Container scanning (Trivy)
   - Code quality scanning (SonarQube)

3. **Release Pipeline** (on push to main with version tag)
   - Everything from extended validation plus:
   - Performance tests (Locust/k6)
   - Security scanning (Snyk)
   - Container image build and push
   - Deployment to staging
   - Smoke tests
   - Deployment to production (approval-controlled)

4. **Scheduled Pipelines** (nightly/weekly)
   - Dependency updates
   - Deep security scans
   - Performance trend analysis
   - Log analysis

### 5.3 Development environments

Every new project should include a consistent developer setup:

- `.env.example` with documented variable names and safe placeholders.
- `pyproject.toml` and `uv.lock`.
- Dockerfile and Docker Compose configuration.
- Pre-commit configuration.
- Ruff, typing and pytest configuration.
- CI workflow templates.
- Alembic configuration.
- Local database and optional Redis services.
- A developer README with exact commands.

A developer should be able to clone a generated project, configure required secrets, start dependencies, apply migrations, run tests and start the API without reverse-engineering the repository.

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install uv for fast Python package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project --all-extras

# Copy application code
COPY . .

# Install project in development mode
RUN uv sync --all-extras

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yaml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: ubf_postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ubf
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro

  redis:
    image: redis:7-alpine
    container_name: ubf_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    container_name: ubf_minio
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  app:
    build: .
    container_name: ubf_app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=local
      - DEBUG=true
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ubf
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production-min-32-chars
      - JWT_ALGORITHM=HS256
      - EMAIL_PROVIDER=log
      - STORAGE_PROVIDER=minio
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - MINIO_SECURE=false
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    volumes:
      - ./app:/app:cached
      - ./logs:/app/logs:cached

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

## Environment-Specific Configuration

### Local Development (.env)

```env
ENVIRONMENT=local
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ubf
SECRET_KEY=dev-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
EMAIL_PROVIDER=log
STORAGE_PROVIDER=local
```

### Production (.env.prod)

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

## Production Deployment Considerations

### Container Orchestration

The foundation supports deployment to various container orchestration platforms:

1. **Docker Swarm** - Simple deployment for small to medium applications
2. **Kubernetes** - Full orchestration for scalable applications
3. **Amazon ECS/ECS** - AWS managed container service
4. **Google Cloud Run** - Fully managed serverless containers
5. **Azure Container Apps** - Microsoft's managed container platform

### Kubernetes Example

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ubf-app
  labels:
    app: ubf-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ubf-app
  template:
    metadata:
      labels:
        app: ubf-app
    spec:
      containers:
      - name: app
        image: ubf-app:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: ubf-secrets
        - configMapRef:
            name: ubf-config
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: ubf-app-service
spec:
  selector:
    app: ubf-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### Environment Variables and Secrets

Secrets should be managed through:
- Docker Secrets (for Swarm)
- Kubernetes Secrets (for K8s)
- AWS Secrets Manager / Parameter Store (for ECS)
- Google Secret Manager (for Cloud Run)
- Azure Key Vault (for Container Apps)

### Health Checks

The foundation provides standardized health check endpoints:
- `GET /health` - Overall health (readiness)
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /health/db` - Database connectivity
- `GET /health/redis` - Redis connectivity (if enabled)

## Monitoring and Observability in Production

### Logging

Structured JSON logging in production with:
- Timestamp
- Log level
- Message
- Service name
- Version
- Trace ID (when available)
- Span ID (when available)
- User ID (when authenticated)
- Request ID

### Metrics

Prometheus-compatible metrics endpoint:
- `GET /metrics` - Application metrics
- HTTP request duration, count, status codes
- Database connection pool usage
- Business metric counters (configurable per module)
- Custom gauges and histograms

### Tracing

OpenTelemetry integration with:
- Automatic instrumentation for FastAPI
- Database query tracing (SQLAlchemy)
- Outbound HTTP client tracing
- Custom span creation for business operations
- Configurable exporters (Jaeger, Tempo, Zipkin, OTLP)

### Error Tracking

Sentry integration for:
- Exception tracking
- Performance monitoring
- Release tracking
- User feedback collection

## Backup and Recovery

### Database Backup Strategy

1. **Automated backups** - Daily logical backups using pg_dump
2. **Point-in-time recovery** - WAL archiving for PITR
3. **Geographic replication** - For disaster recovery
4. **Backup validation** - Regular restore tests

### Application Data Backup

For applications with file storage:
- Versioned backups of storage buckets
- Metadata snapshots
- Integrity verification scripts

## Rollback Procedures

### Database Rollbacks

1. **Transaction rollbacks** - Automatic on failed transactions
2. **Migration rollbacks** - Alembic downgrade capabilities
3. **Point-in-time recovery** - For catastrophic failures
4. **Blue-green deployments** - For zero-downtime rollbacks

### Application Rollbacks

1. **Container image rollbacks** - Deploy previous known-good image
2. **Feature flags** - Disable problematic features without redeploy
3. **Traffic shifting** - Gradual rollback using service mesh

## Security Considerations in Production

### Image Security

1. **Base image scanning** - Trivy scanning of base images
2. **Dependency scanning** - Safety check of Python dependencies
3. **Container scanning** - Trivy or Clair for known vulnerabilities
4. **Image signing** - Cosign or Notary for image integrity

### Runtime Security

1. **Non-root containers** - Run as non-root user
2. **Read-only filesystems** - Where possible
3. **Drop unnecessary capabilities** - Minimal Linux capabilities
4. **Network policies** - Restrict inter-service communication
5. **Pod security policies** - Or equivalent for container runtime

### Secrets Management

1. **Never bake secrets into images** - Use runtime injection
2. **Rotate secrets regularly** - Automated secret rotation
3. **Audit secret access** - Log and monitor secret usage
4. **Use short-lived credentials** - Where supported (IAM roles, etc.)

## Deployment Verification

### Smoke Tests

Automated smoke tests after deployment:
- Health check endpoints
- Basic authentication flow
- Critical endpoint validation
- Database connectivity check
- External service connectivity (where applicable)

### Performance Validation

Post-deployment performance checks:
- Response time validation
- Throughput verification
- Resource utilization monitoring
- Error rate tracking

### Rollback Triggers

Automatic rollback conditions:
- Health check failures
- Error rate thresholds
- Performance degradation
- Resource exhaustion
- Failed smoke tests