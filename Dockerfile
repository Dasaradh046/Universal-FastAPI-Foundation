# Stage 1: Build
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir setuptools wheel
RUN pip install --no-cache-dir -e .

# Stage 2: Runtime
FROM python:3.13-slim AS runtime

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m appuser

# Copy installed package and dependencies from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app /app/app

# Copy JWT key files if they exist
COPY --from=builder /app/keys /app/keys 2>/dev/null || true

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]