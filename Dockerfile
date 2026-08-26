FROM python:3.11-slim

# Playwright/Chromium em path fixo (legível pelo user app — P3.1 Hetzner).
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright \
    HOME=/app

RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    fonts-liberation libnss3 libxss1 libasound2 \
    # WeasyPrint (HTML/CSS → PDF de produção): Pango/cairo/gdk-pixbuf + fontes.
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev \
    shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/.cache/ms-playwright && playwright install chromium

# SHA do código bakeado na imagem → /api/version mostra versão em prod.
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
COPY . .

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --home-dir /app --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data/cno \
    && chown -R app:app /app /data/cno

USER app

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Cloud Run: non-root quebrava "Container import" (6 canários 2026). Prod = Hetzner Docker
# — canário P3.1 validado 2026-08-26 (uid 1000, Playwright, /health, cno_data writable).
