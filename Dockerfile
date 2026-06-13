FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    fonts-liberation libnss3 libxss1 libasound2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ── Hardening non-root (semgrep missing-user) — RISCO ACEITO ──────────────────
# Tentativas USER non-root (chown -R / chmod / browsers em ~/.cache) TODAS deram
# "Container import failed" no Cloud Run — específico desta imagem ~940MB com a
# árvore do Chromium em ownership não-root (a versão root, mesmo tamanho, importa;
# o frontend nginx-unprivileged ~50MB importa). Verificado via 6 canários no-traffic.
# Mitigação: Cloud Run isola cada container em sandbox gVisor (root do container ≠
# root do host), reduzindo o risco do finding. Reabrir se migrar a imagem (ex.: base
# mcr.microsoft.com/playwright ou separar o scraper em serviço próprio menor).
