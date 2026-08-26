# syntax=docker/dockerfile:1
# Manifest-list digest for python:3.11-slim (2025-08-25). OS CVEs patched in RUN apt-get upgrade below.
ARG PYTHON_IMAGE=python:3.11-slim@sha256:be1575ed968de893bd54f4c56315ff7c4736ce522c1bca08fd521731aafc0d76

FROM ${PYTHON_IMAGE} AS builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && pip install --no-cache-dir --upgrade \
        "pip>=25.3" "wheel>=0.46.2" "setuptools>=79.0.1" "jaraco.context>=6.1.0" \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /usr/local/lib/python3.11/site-packages/setuptools \
              /usr/local/lib/python3.11/site-packages/setuptools-*.dist-info \
    && pip install --no-cache-dir "setuptools>=84.0.0" "wheel>=0.46.2" \
    && rm -rf /usr/local/lib/python3.11/site-packages/setuptools/_vendor

FROM ${PYTHON_IMAGE}

# System Chromium via apt — skip Playwright browser download (~400MB, CI disk blow-up).
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
    HOME=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation libnss3 libxss1 libasound2 \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /var/tmp/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

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
