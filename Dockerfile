# =============================================================================
# Stage 1: Builder
# Install all dependencies (including dev tools used during build if any).
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies needed by some Python packages (e.g., bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first to leverage Docker layer caching.
# If pyproject.toml hasn't changed, the pip install layer is reused.
COPY pyproject.toml .

# Install all production dependencies into a prefix we can copy later.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]" --target /install


# =============================================================================
# Stage 2: Runtime image
# Minimal image with only production dependencies.
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local/lib/python3.12/site-packages

# Copy application source
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup alembic.ini .

USER appuser

EXPOSE 8000

# Healthcheck: call the /health endpoint every 30 seconds.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
