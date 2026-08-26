FROM python:3.11-slim

# System Chromium via apt — skip Playwright browser download (~400MB, CI disk blow-up).
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
    HOME=/app

RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    fonts-liberation libnss3 libxss1 libasound2 \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev \
    shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
