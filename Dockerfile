# =============================================================================
# GymSite Intelligence — FastAPI + ADK + Playwright (chromium)
#
# Build:  docker build -t gymsite-api:latest .
# Scan:   docker scout cves gymsite-api:latest --only-severity critical,high
# Run:    docker run --env-file .env -p 8000:8000 gymsite-api:latest
# =============================================================================

# Pin patched base (Python 3.12.13 + Debian bookworm). Update digest when bumping.
ARG PYTHON_IMAGE=python:3.12.13-slim-bookworm@sha256:93ab4b7fa528b25124c97bcc755415e60eb671a86b4dbe0328df2fe2d1c1193d

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System deps para Playwright + libs compartilhadas (dist-upgrade puxa patches Debian)
RUN apt-get update && apt-get -y dist-upgrade && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        libnss3 \
        libnspr4 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Cacheable layer: deps primeira (leverage Docker layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --user -r requirements.txt && \
    pip install --user --ignore-installed packaging>=24.0

# Browsers do Playwright (apenas chromium) — separate layer pra reutilizar se requirements não muda
# playwright já está em requirements.txt; usamos python -m pra garantir PATH
RUN python -m playwright install --with-deps chromium

# ═══════════════════════════════════════════════════════════════════════════
# Runtime stage — apenas o necessário pra rodar
# ═══════════════════════════════════════════════════════════════════════════
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.local/share/ms-playwright \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Runtime: dist-upgrade obrigatório — stage novo herda base sem patches do builder
RUN apt-get update && apt-get -y dist-upgrade && apt-get install -y --no-install-recommends \
        ca-certificates \
        libnspr4 \
        libnss3 \
        libatk-bridge2.0-0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (segurança)
RUN useradd -m -u 1001 appuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . /app

USER appuser

# Certify Python packages on PATH
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

# Health check melhorado (sem wget, usa curl ou Python)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://127.0.0.1:8000/health', timeout=4)" || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--workers", "2"]
