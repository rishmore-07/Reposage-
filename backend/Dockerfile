# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests
COPY pyproject.toml requirements.lock ./

# Install uv and dependencies into an isolated prefix
RUN pip install uv && \
    uv pip install --system --prefix=/install -r requirements.lock

# ── Stage 2: Production runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS production

# Security: run as non-root user
RUN groupadd -r reposage && useradd -r -g reposage reposage

WORKDIR /app

# Install runtime-only system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=reposage:reposage . .

# Switch to non-root user
USER reposage

# Health check — hits the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Production entrypoint: gunicorn with UvicornWorker for async support
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--keepalive", "5", \
     "--log-level", "info"]
