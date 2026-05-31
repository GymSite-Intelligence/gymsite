# backend_improvements.py — Production-ready middleware & observability for FastAPI
"""
Stack integrado: JSON logging, HTTP cache headers, Prometheus-style metrics,
graceful shutdown, request tracing (X-Request-ID), e Supabase connection pooling.

Uso: importar e injetar no api.py (ver seção INTEGRAÇÃO abaixo).
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import json
import logging
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ════════════════════════════════════════════════════════════════════════════
# 1. Structured Logging (JSON) — Grafana-ready
# ════════════════════════════════════════════════════════════════════════════

REQUEST_ID_CTX: contextvars.ContextVar[str] = contextvars.ContextVar("request_id")
USER_ID_CTX: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """Emite logs como JSON estruturado pra ingestão em Loki / Grafana Cloud."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        # Contexto da request (injetado via middleware)
        try:
            log_data["request_id"] = REQUEST_ID_CTX.get()
        except LookupError:
            pass
        try:
            uid = USER_ID_CTX.get()
            if uid:
                log_data["user_id"] = uid
        except LookupError:
            pass
        return json.dumps(log_data, default=str, ensure_ascii=False)


def setup_json_logging(log_level: str = "INFO") -> logging.Logger:
    """Substitui logging.basicConfig por handler JSON no logger raiz da aplicação."""
    logger = logging.getLogger("gymsite.api")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Evita handlers duplicados se função for chamada mais de uma vez
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


# ════════════════════════════════════════════════════════════════════════════
# 2. Response Caching Middleware — Cache-Control automático
# ════════════════════════════════════════════════════════════════════════════

class CachingMiddleware(BaseHTTPMiddleware):
    """Adiciona Cache-Control headers em GET endpoints baseado em padrões de rota."""

    CACHE_PATTERNS: dict[str, tuple[str, int]] = {
        "/health": ("public", 60),
        "/api/metrics": ("public", 15),
        "/api/relatorios": ("private", 300),
        "/api/relatorios/{id}/pdf": ("private", 3600),
        "/api/relatorios/{id}/custos-api": ("private", 300),
        "/api/relatorios/{id}/status": ("private", 30),
        "/api/custos": ("private", 900),
        "/api/canais/status": ("public", 60),
        "/api/prospeccao/oportunidades": ("private", 300),
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if request.method != "GET":
            return response

        path = request.url.path
        for pattern, (cache_type, max_age) in self.CACHE_PATTERNS.items():
            if _match_route_pattern(path, pattern):
                response.headers["Cache-Control"] = f"{cache_type}, max-age={max_age}"
                response.headers["Vary"] = "Accept-Encoding, Authorization"
                break

        return response


def _match_route_pattern(path: str, pattern: str) -> bool:
    """Matching simples: /api/relatorios/{id} bate com /api/relatorios/123."""
    import re

    regex = pattern.replace("{id}", r"[^/]+")
    return bool(re.match(f"^{regex}$", path))


# ════════════════════════════════════════════════════════════════════════════
# 3. Metrics Middleware — Prometheus-compatible (text/plain endpoint)
# ════════════════════════════════════════════════════════════════════════════

class MetricsMiddleware(BaseHTTPMiddleware):
    """Coleta latência e throughput por rota; expõe via /api/metrics."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.request_count: dict[str, int] = {}
        self.request_duration: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path = request.url.path
        key = f"{method}:{path}"

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        async with self._lock:
            self.request_count[key] = self.request_count.get(key, 0) + 1
            self.request_duration.setdefault(key, []).append(duration)

        # Headers de telemetria no response
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        req_id = request.headers.get("X-Request-ID")
        if req_id:
            response.headers["X-Request-ID"] = req_id

        return response

    def get_metrics(self) -> dict[str, Any]:
        """Retorna métricas agregadas (count, avg, p95, p99)."""
        metrics: dict[str, Any] = {}
        for key, count in self.request_count.items():
            durations = sorted(self.request_duration.get(key, []))
            avg = sum(durations) / len(durations) if durations else 0.0
            p95 = _percentile(durations, 0.95)
            p99 = _percentile(durations, 0.99)
            metrics[key] = {
                "count": count,
                "avg_duration_sec": round(avg, 4),
                "p95_duration_sec": round(p95, 4),
                "p99_duration_sec": round(p99, 4),
            }
        return metrics

    def render_prometheus(self) -> str:
        """Formata métricas em texto Prometheus (openmetrics)."""
        lines: list[str] = [
            "# HELP gymsite_request_total Total requests",
            "# TYPE gymsite_request_total counter",
        ]
        for key, count in self.request_count.items():
            method, path = key.split(":", 1)
            lines.append(
                f'gymsite_request_total{{method="{method}",path="{path}"}} {count}'
            )

        lines.extend([
            "# HELP gymsite_request_duration_seconds Request duration",
            "# TYPE gymsite_request_duration_seconds summary",
        ])
        for key in self.request_count:
            durations = sorted(self.request_duration.get(key, []))
            if not durations:
                continue
            method, path = key.split(":", 1)
            avg = sum(durations) / len(durations)
            p95 = _percentile(durations, 0.95)
            lines.append(
                f'gymsite_request_duration_seconds{{method="{method}",path="{path}",quantile="0.5"}} '
                f"{avg:.4f}"
            )
            lines.append(
                f'gymsite_request_duration_seconds{{method="{method}",path="{path}",quantile="0.95"}} '
                f"{p95:.4f}"
            )

        return "\n".join(lines) + "\n"


def _percentile(sorted_data: list[float], q: float) -> float:
    """Percentil linear simples (data já ordenada)."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    idx = q * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


# ════════════════════════════════════════════════════════════════════════════
# 4. Request Tracing Middleware — X-Request-ID + context logging
# ════════════════════════════════════════════════════════════════════════════

class TracingMiddleware(BaseHTTPMiddleware):
    """Gera / propaga X-Request-ID e injeta no contexto de logging."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}_{id(request):x}"

        token_req = REQUEST_ID_CTX.set(request_id)

        # Tenta extrair user_id do JWT (caso presente)
        auth = request.headers.get("authorization", "")
        user_id: str | None = None
        if auth.lower().startswith("bearer "):
            user_id = _extract_user_id_from_jwt(auth[7:])
        token_usr = USER_ID_CTX.set(user_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            REQUEST_ID_CTX.reset(token_req)
            USER_ID_CTX.reset(token_usr)


def _extract_user_id_from_jwt(token: str) -> str | None:
    """Decodifica payload do JWT (sem verificação de assinatura) pra extrair sub."""
    try:
        import base64

        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        # Pad base64
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("sub") or data.get("user_id")
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════════════
# 5. Graceful Shutdown — drena tasks pendentes no SIGTERM/SIGINT
# ════════════════════════════════════════════════════════════════════════════

class GracefulShutdownManager:
    """Rastreia tasks e aguarda conclusão antes de encerrar."""

    def __init__(self, timeout_sec: int = 30) -> None:
        self.timeout_sec = timeout_sec
        self._pending: set[asyncio.Task[Any]] = set()
        self._shutdown_event = asyncio.Event()

    def register(self, task: asyncio.Task[Any]) -> None:
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    def create_task(self, coro: Awaitable[Any]) -> asyncio.Task[Any]:
        """Wrapper seguro: registra task no shutdown manager."""
        task = asyncio.create_task(coro)
        self.register(task)
        return task

    async def drain(self) -> None:
        """Aguarda tasks pendentes ou timeout."""
        if not self._pending:
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._pending, return_exceptions=True),
                timeout=self.timeout_sec,
            )
        except asyncio.TimeoutError:
            remaining = [t for t in self._pending if not t.done()]
            logging.getLogger("gymsite.api").warning(
                f"Graceful shutdown timeout: {len(remaining)} tasks forcadas"
            )
            for t in remaining:
                t.cancel()

    def handle_signal(self, signame: str) -> None:
        logging.getLogger("gymsite.api").info(f"Sinal {signame} recebido — iniciando graceful shutdown")
        self._shutdown_event.set()

    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()


def _register_signal_handlers(shutdown_manager: GracefulShutdownManager) -> None:
    """Registra SIGTERM/SIGINT de forma cross-platform."""
    loop = asyncio.get_running_loop()

    # SIGINT (Ctrl+C) — não suportado no Windows ProactorEventLoop
    try:
        loop.add_signal_handler(signal.SIGINT, shutdown_manager.handle_signal, "SIGINT")
    except (ValueError, NotImplementedError):
        pass

    # SIGTERM — não suportado no Windows
    if sys.platform != "win32":
        try:
            loop.add_signal_handler(signal.SIGTERM, shutdown_manager.handle_signal, "SIGTERM")
        except (ValueError, NotImplementedError):
            pass


def make_lifespan(shutdown_manager: GracefulShutdownManager):
    """Factory que retorna o lifespan async generator pro FastAPI."""

    async def lifespan(app: FastAPI):
        logger = logging.getLogger("gymsite.api")
        logger.info("GymSite API iniciando...")
        _register_signal_handlers(shutdown_manager)

        yield

        logger.info("GymSite API encerrando gracefully...")
        await shutdown_manager.drain()
        logger.info("GymSite API encerrado")

    return lifespan


# ════════════════════════════════════════════════════════════════════════════
# 6. Supabase Connection Pooling (async-safe)
# ════════════════════════════════════════════════════════════════════════════

class SupabaseClientPool:
    """Pool leve de clients Supabase com borrow/release."""

    def __init__(self, url: str, key: str, pool_size: int = 5) -> None:
        self.url = url
        self.key = key
        self.pool_size = pool_size
        self._clients: list[Any] = []
        self._available: asyncio.Queue[Any] = asyncio.Queue(maxsize=pool_size)
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        from supabase import create_client

        for _ in range(self.pool_size):
            client = create_client(self.url, self.key)
            self._clients.append(client)
            await self._available.put(client)
        self._initialized = True

    async def get_client(self, timeout_sec: float = 5.0) -> Any:
        try:
            return await asyncio.wait_for(self._available.get(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout adquirindo client do pool Supabase")

    async def release_client(self, client: Any) -> None:
        await self._available.put(client)

    @asynccontextmanager
    async def acquire(self):
        client = await self.get_client()
        try:
            yield client
        finally:
            await self.release_client(client)


# ════════════════════════════════════════════════════════════════════════════
# 7. INSTRUÇÕES DE INTEGRAÇÃO NO api.py
# ════════════════════════════════════════════════════════════════════════════

"""
INTEGRAÇÃO (cópia direta no api.py):

# --- imports ---
from backend_improvements import (
    setup_json_logging,
    CachingMiddleware,
    MetricsMiddleware,
    TracingMiddleware,
    GracefulShutdownManager,
    make_lifespan,
)

# --- logging (substitui basicConfig) ---
logger = setup_json_logging(os.getenv("LOG_LEVEL", "INFO"))

# --- shutdown manager ---
_shutdown_mgr = GracefulShutdownManager(timeout_sec=30)

# --- app com lifespan ---
app = FastAPI(
    title="GymSite Intelligence API",
    version="1.0.0",
    lifespan=make_lifespan(_shutdown_mgr),
)

# --- middlewares (ORDEM: tracing → metrics → caching → CORS) ---
# CORS já existe; adicione os novos ANTES do CORS:
app.add_middleware(TracingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(CachingMiddleware)
# ... app.add_middleware(CORSMiddleware, ...)  # existente

# --- métricas (adicione perto do /health) ---
_metrics_mw: MetricsMiddleware | None = None

@app.get("/api/metrics")
def get_metrics() -> Response:
    if _metrics_mw is None:
        raise HTTPException(status_code=503, detail="Metrics middleware não inicializado")
    return Response(
        content=_metrics_mw.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )

# Para capturar a instância do MetricsMiddleware, use um pequeno hack
# logo após app.add_middleware:
#   _metrics_mw = app.user_middleware[-1].cls(...)  # não recomendado
# Melhor: injete via dependency ou acesse app.state.

# Alternativa simples (usada na prática):
# Crie a instância do MetricsMiddleware explicitamente e passe pro add_middleware
# usando a sintaxe do Starlette:
#   from starlette.middleware import Middleware
#   metrics_mw = MetricsMiddleware(app)
# Porém FastAPI facilita via app.state:
"""
