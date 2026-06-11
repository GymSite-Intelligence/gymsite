"""
api.py — FastAPI server pro GymSite Intelligence.

Endpoints:
- POST /api/relatorios            cria stub + dispara pipeline em background
- GET  /api/relatorios            lista (suporta filtros)
- GET  /api/relatorios/{id}       detail completo (joins de todas as 9 tabelas)
- GET  /api/relatorios/{id}/mapa-mercado   pins concorrentes + heat entrantes (município)
- GET  /api/relatorios/{id}/pdf   PDF estruturado (layout=classic|executive|data_room)
- GET  /api/relatorios/{id}/status   polling leve do status

O pipeline é invocado via Google ADK Runner em background task. O `relatorio_id`
do stub criado pré-pipeline é injetado no session state, e o callback do A6
faz UPDATE em vez de INSERT no Supabase.

Dev:
    uvicorn api:app --reload --port 8000

Variáveis de ambiente (.env):
    SUPABASE_URL                  https://<ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY     chave service_role (RLS bypass)
    SUPABASE_GYMSITE_ORG_ID       UUID da org (default fixo se ausente)
    GEMINI_API_KEY / GOOGLE_API_KEY
    GOOGLE_MAPS_API_KEY  (Places New, Geocoding, pipeline)
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from tools.supabase_client import load_create_client

create_client = load_create_client()  # type: ignore[assignment]

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend_improvements import (
    setup_json_logging,
    CachingMiddleware,
    MetricsMiddleware,
    TracingMiddleware,
    GracefulShutdownManager,
    _register_signal_handlers,
)
from tools.redis_rate_limit import RateLimitMiddleware
from tools.redis_cache import RedisCacheMiddleware
from tools.redis_queue import RedisQueue, gymsite_worker
from tools.redis_pubsub import notify_relatorio_pronto, notify_prospeccao_pronta
from tools.relatorio_completeness import EMPTY_REPORT_MSG, validate_relatorio_has_content
from pydantic import BaseModel, Field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)
load_dotenv(_ROOT / "gymsite_intelligence" / ".env", override=False)

logger = setup_json_logging(os.getenv("LOG_LEVEL", "INFO"))

from tools.google_maps_key import warn_if_missing_maps_key
from tools.telemetry import span

warn_if_missing_maps_key()

_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail="Supabase não configurado (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY ausentes em .env)",
        )
    return create_client(url, key)


_UUID_RE = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _resolve_relatorio_uuid(sb, relatorio_id: str) -> str:
    """Aceita UUID ou adk_run_id legado (`rpt_*`)."""
    import re

    if re.match(_UUID_RE, relatorio_id, re.I):
        return relatorio_id
    if relatorio_id.startswith("rpt_"):
        res = (
            sb.table("relatorios")
            .select("id")
            .eq("adk_run_id", relatorio_id)
            .maybe_single()
            .execute()
        )
        if res and res.data:
            return res.data["id"]
    return relatorio_id


_STALE_PIPELINE_HOURS = int(os.getenv("PIPELINE_STALE_HOURS", "6"))
# Layer 3: órfãos running/queued sem output — default 35 min (< PIPELINE_STALE_HOURS).
_PIPELINE_ORPHAN_MINUTES = int(os.getenv("PIPELINE_ORPHAN_MINUTES", "35"))
_PIPELINE_WALL_BUFFER_MIN = int(os.getenv("PIPELINE_WALL_BUFFER_MIN", "5"))
_STALE_MSG = (
    "Pipeline interrompido (restart do servidor ou timeout). "
    "Use «Gerar novamente» para reprocessar."
)

# Teto de wall-clock por execução (fila + retries 429 + ADK). Default 30 min.
# Não substitui resume parcial do ADK — apenas evita runs de 50+ min.
_PIPELINE_MAX_WALL_SEC = int(os.getenv("PIPELINE_MAX_WALL_SEC", "1800"))
_PIPELINE_HEARTBEAT_SEC = int(os.getenv("PIPELINE_HEARTBEAT_SEC", "60"))


class PipelineWallTimeoutError(TimeoutError):
    """Pipeline excedeu PIPELINE_MAX_WALL_SEC (inclui backoff de 429)."""

    def __init__(self) -> None:
        max_min = max(1, _PIPELINE_MAX_WALL_SEC // 60)
        super().__init__(
            f"Pipeline excedeu o tempo máximo ({max_min} min). "
            "Use «Gerar novamente»; fora do horário de pico costuma ser mais rápido."
        )


def _pipeline_wall_remaining_sec(t0: float) -> float:
    return max(0.0, float(_PIPELINE_MAX_WALL_SEC) - (time.time() - t0))


def _ensure_pipeline_wall_clock(t0: float) -> None:
    if _pipeline_wall_remaining_sec(t0) <= 0:
        raise PipelineWallTimeoutError()


def _pipeline_stale_cutoff() -> datetime:
    """updated_at anterior a este instante => candidato a órfão (Layer 3)."""
    from datetime import timedelta

    wall_hours = _PIPELINE_MAX_WALL_SEC / 3600.0 + _PIPELINE_WALL_BUFFER_MIN / 60.0
    hours_floor = max(float(_STALE_PIPELINE_HOURS), wall_hours)
    age = min(
        timedelta(hours=hours_floor),
        timedelta(minutes=_PIPELINE_ORPHAN_MINUTES),
    )
    return datetime.now(timezone.utc) - age


def _mark_pipeline_failed(
    sb,
    relatorio_id: str,
    *,
    elapsed: int,
    erro_mensagem: str,
) -> None:
    try:
        sb.table("relatorios").update({
            "status": "failed",
            "erro_mensagem": erro_mensagem[:500],
            "tempo_execucao_segundos": elapsed,
        }).eq("id", relatorio_id).execute()
    except Exception:
        pass


def _recover_stale_running_reports(sb, *, relatorio_id: str | None = None) -> int:
    """Marca como failed relatórios running/queued órfãos (sem output)."""
    rid_uuid: str | None = None
    if relatorio_id:
        rid_uuid = _resolve_relatorio_uuid(sb, relatorio_id)

    try:
        rpc_params: dict[str, Any] = {"p_orphan_minutes": _PIPELINE_ORPHAN_MINUTES}
        if rid_uuid:
            rpc_params["p_relatorio_id"] = rid_uuid
        rpc_res = sb.rpc("recover_stale_running_reports", rpc_params).execute()
        n = int(rpc_res.data) if rpc_res.data is not None else 0
        if n:
            logger.warning(
                "recover_stale_running_reports (RPC): %d órfão(s)%s",
                n,
                f" incl. {rid_uuid}" if rid_uuid else "",
            )
        return n
    except Exception as rpc_err:
        logger.debug("recover_stale_running_reports RPC indisponível: %s", rpc_err)

    cutoff = _pipeline_stale_cutoff()
    cutoff_iso = cutoff.isoformat()
    try:
        q = (
            sb.table("relatorios")
            .select("id, status, updated_at")
            .in_("status", ["running", "queued"])
            .lt("updated_at", cutoff_iso)
        )
        if rid_uuid:
            q = q.eq("id", rid_uuid)
        rows = q.execute().data or []
        recovered = 0
        for row in rows:
            rid = row["id"]
            out = (
                sb.table("relatorio_outputs")
                .select("relatorio_id")
                .eq("relatorio_id", rid)
                .limit(1)
                .execute()
            )
            if out.data:
                continue
            sb.table("relatorios").update({
                "status": "failed",
                "erro_mensagem": _STALE_MSG,
            }).eq("id", rid).execute()
            recovered += 1
            logger.warning("relatório órfão recuperado: %s (era %s)", rid, row.get("status"))
        return recovered
    except Exception as e:
        logger.error("recover_stale_running_reports falhou: %s", e, exc_info=True)
        return 0


def _recover_done_empty_reports(sb, *, relatorio_id: str | None = None) -> int:
    """Marca como failed relatórios done sem conteúdo persistido (outputs ausentes/vazios)."""
    rid_uuid: str | None = None
    if relatorio_id:
        rid_uuid = _resolve_relatorio_uuid(sb, relatorio_id)

    try:
        q = sb.table("relatorios").select("id, status").eq("status", "done")
        if rid_uuid:
            q = q.eq("id", rid_uuid)
        rows = q.execute().data or []
        recovered = 0
        for row in rows:
            rid = row["id"]
            ok, err = validate_relatorio_has_content(sb, rid)
            if ok:
                continue
            sb.table("relatorios").update({
                "status": "failed",
                "erro_mensagem": (err or EMPTY_REPORT_MSG)[:500],
            }).eq("id", rid).execute()
            recovered += 1
            logger.warning(
                "relatório done sem conteúdo recuperado: %s — %s",
                rid,
                err,
            )
        return recovered
    except Exception as e:
        logger.error("recover_done_empty_reports falhou: %s", e, exc_info=True)
        return 0


async def _touch_relatorio_heartbeat(sb, relatorio_id: str) -> None:
    """Atualiza updated_at (via trigger) enquanto o pipeline ADK está ativo."""
    try:
        sb.table("relatorios").update({"status": "running"}).eq(
            "id", relatorio_id
        ).eq("status", "running").execute()
    except Exception as e:
        logger.debug("heartbeat %s: %s", relatorio_id, e)


async def _pipeline_heartbeat_loop(
    sb,
    relatorio_id: str,
    stop: asyncio.Event,
) -> None:
    interval = max(15, _PIPELINE_HEARTBEAT_SEC)
    while not stop.is_set():
        await _touch_relatorio_heartbeat(sb, relatorio_id)
        try:
            await asyncio.wait_for(stop.wait(), timeout=float(interval))
            return
        except asyncio.TimeoutError:
            continue


# Observability + graceful shutdown
_shutdown_mgr = GracefulShutdownManager(timeout_sec=30)
_metrics_mw_instance: MetricsMiddleware | None = None
_queue: RedisQueue | None = None


class _CapturedMetricsMiddleware(MetricsMiddleware):
    """Captures the middleware instance so /api/metrics can read from it."""
    def __init__(self, app):
        super().__init__(app)
        global _metrics_mw_instance
        _metrics_mw_instance = self


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan com graceful shutdown + RedisQueue worker."""
    logger.info("GymSite API iniciando...")
    _register_signal_handlers(_shutdown_mgr)

    try:
        from tools._genai_client import is_vertex_mode

        if is_vertex_mode():
            creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            if creds and not os.path.isfile(creds):
                logger.error(
                    "GOOGLE_APPLICATION_CREDENTIALS=%s não encontrado — pipeline ADK vai falhar",
                    creds,
                )
        else:
            gkey = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
            if gkey.startswith("AQ."):
                logger.error(
                    "GOOGLE_API_KEY formato AQ.* inválido para pipeline ADK (401). "
                    "Use AIzaSy... de https://aistudio.google.com/apikey ou Vertex."
                )
            elif not gkey:
                logger.warning("GOOGLE_API_KEY ausente — agentes Gemini falharão")
    except Exception as e:
        logger.warning("Gemini auth startup check skip: %s", e)

    global _queue
    _queue = RedisQueue(gymsite_worker)
    worker_task = asyncio.create_task(_queue.start_worker())
    _shutdown_mgr.register(worker_task)

    try:
        n = _recover_stale_running_reports(_supabase_client())
        if n:
            logger.info("Recuperados %d relatório(s) running/queued órfãos", n)
    except Exception as e:
        logger.warning("Startup stale recovery skip: %s", e)

    try:
        from tools.token_telemetry import prune_tokens_csv

        removed = prune_tokens_csv()
        if removed:
            logger.info("Telemetria CSV: %d linha(s) antiga(s) removida(s)", removed)
    except Exception as e:
        logger.warning("Telemetria CSV retention skip: %s", e)

    yield

    logger.info("GymSite API encerrando gracefully...")
    if _queue:
        _queue.stop()
    await _shutdown_mgr.drain()
    logger.info("GymSite API encerrado")


app = FastAPI(
    title="GymSite Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

from backend.routers.parceiros_admin import router as parceiros_admin_router
from backend.routers.execucao import router as execucao_router

app.include_router(parceiros_admin_router)
app.include_router(execucao_router)

# CORS: dev libera localhost:* via regex; producao vem de CORS_ORIGINS (.env),
# comma-separated. Ex: CORS_ORIGINS=https://vectracargo.com.br,https://gymsite.vectracargo.com.br
_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
] + ["https://vectracargo.com.br", "https://www.vectracargo.com.br"]
if _cors_origins:
    logger.info("CORS origins from env: %s", _cors_origins)
else:
    logger.warning(
        "CORS_ORIGINS nao definida em .env — somente localhost:* via regex liberado"
    )

# Regex extras: localhost dev + Cloudflare Pages (preview hash.gymsite-3p0.pages.dev)
_cors_origin_regex = (
    r"http://localhost:\d+"
    r"|https://([a-z0-9-]+\.)*gymsite-3p0\.pages\.dev"
)

# Middleware stack — último add_middleware = mais externo (roda primeiro).
# CORS deve ser o mais externo para OPTIONS/preflight responder antes de rate limit/cache.
app.add_middleware(_CapturedMetricsMiddleware)
app.add_middleware(CachingMiddleware)
app.add_middleware(RedisCacheMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Request-ID", "X-Process-Time", "X-RateLimit-Remaining", "X-Cache"],
)


# ════════════════════════════════════════════════════════════════════════════
# Schemas Pydantic
# ════════════════════════════════════════════════════════════════════════════

class NovoRelatorioInput(BaseModel):
    cidade: str
    uf: Optional[str] = None
    bairro: str
    area_m2_min: int = Field(ge=50, le=10000)
    area_m2_max: int = Field(ge=50, le=10000)
    tamanho_preset: str = "m"
    publico_alvo: str = "25-40"
    genero_alvo: str = "misto"
    tipo_negocio: str = "academia"
    estacionamento_obrigatorio: bool = True
    bairros_indicados: list[str] = []
    org_id: Optional[str] = None
    a0_research_provider: Optional[str] = Field(
        default="auto",
        description="Provedor A0: gemini | kimi | auto",
    )


class RelatorioStub(BaseModel):
    id: str
    status: str
    created_at: Optional[str] = None


class PlacesAutocompleteInput(BaseModel):
    input: str
    municipio: str = ""
    uf: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None


class CanalProbeInput(BaseModel):
    """Parâmetros mínimos para probes Run now (formulário novo relatório)."""
    cidade: str
    bairro: str
    uf: Optional[str] = None
    tipo_negocio: str = "academia"
    publico_alvo: str = "premium"
    raio_metros: int = Field(default=3000, ge=500, le=15000)


# ════════════════════════════════════════════════════════════════════════════
# Pipeline runner — invoca ADK programaticamente em background
# ════════════════════════════════════════════════════════════════════════════

_RETRY_BACKOFFS_429 = [30, 60, 120]  # segundos entre tentativas


def _is_429_error(exc: BaseException) -> bool:
    """Detecta 429 RESOURCE_EXHAUSTED em qualquer profundidade de exception tree.

    Pipeline ADK propaga via BaseExceptionGroup (TaskGroup); o erro real
    fica dentro do `.exceptions`. Buscamos recursivamente.
    """
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_429_error(sub) for sub in exc.exceptions)
    name = type(exc).__name__
    msg = str(exc).lower()
    if "resourceexhausted" in name.lower():
        return True
    return "429" in msg or "resource_exhausted" in msg


async def _executar_pipeline_uma_vez(relatorio_id: str, payload: NovoRelatorioInput) -> dict:
    """Executa o pipeline ADK e persiste custos. Retorna summary."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part
    from gymsite_intelligence.agent import root_agent
    from tools.enrichment_cache import (
        inject_cache_context,
        reset_pipeline_enrichment_context,
        set_pipeline_enrichment_context,
    )
    from tools.market_bundle import inject_market_bundle_context
    from tools.research_provider import set_a0_research_provider
    from tools.token_telemetry import reset_run_id, _get_run_id

    from tools.api_cost_tracker import current_relatorio_id
    token = current_relatorio_id.set(relatorio_id)
    enrichment_cv_token = None
    try:
        with span("pipeline.adk.run", relatorio_id=relatorio_id, cidade=payload.cidade):
            set_a0_research_provider(payload.a0_research_provider or "auto")

            # Reset run_id pra cada tentativa — telemetria fica separada por tentativa.
            reset_run_id()

            uf = (payload.uf or "CE")[:2]
            enrichment_ctx = inject_cache_context(
                payload.cidade,
                payload.bairro,
                uf,
                {},
                area_min=payload.area_m2_min,
                area_max=payload.area_m2_max,
            )
            enrichment_ctx = inject_market_bundle_context(
                payload.cidade,
                payload.bairro,
                uf,
                enrichment_ctx,
            )
            enrichment_cv_token = set_pipeline_enrichment_context(enrichment_ctx)
            if enrichment_ctx.get("skip_tools"):
                logger.info(
                    "enrichment cache hit cache_key=%s skip_tools=%s",
                    enrichment_ctx.get("cache_key"),
                    enrichment_ctx.get("skip_tools"),
                )

            session_service = InMemorySessionService()
            session_id = f"api_{relatorio_id}_{int(time.time())}"
            user_id = "api_user"

            session_state: dict = {
                "relatorio_id": relatorio_id,
                "input_params": {
                    "cidade": payload.cidade,
                    "uf": payload.uf,
                    "bairro": payload.bairro,
                    "area_m2_min": payload.area_m2_min,
                    "area_m2_max": payload.area_m2_max,
                    "tamanho_preset": payload.tamanho_preset,
                    "tipo_negocio": payload.tipo_negocio,
                    "publico_alvo": payload.publico_alvo,
                    "genero_alvo": payload.genero_alvo,
                    "estacionamento_obrigatorio": payload.estacionamento_obrigatorio,
                    "a0_research_provider": payload.a0_research_provider or "auto",
                },
            }
            for key in (
                "local_market_summary",
                "cache_key",
                "skip_tools",
                "enrichment_cache",
                "enrichment_cache_fresh",
                "market_bundle",
                "market_bundle_available",
                "market_bundle_fresh",
                "market_bundle_briefing_md",
                "skip_deep_research",
                "market_bundle_partial",
            ):
                if key in enrichment_ctx:
                    session_state[key] = enrichment_ctx[key]

            await session_service.create_session(
                app_name="gymsite",
                user_id=user_id,
                session_id=session_id,
                state=session_state,
            )

            runner = Runner(
                agent=root_agent,
                app_name="gymsite",
                session_service=session_service,
            )

            prompt = _build_pipeline_prompt(payload)
            message = Content(role="user", parts=[Part(text=prompt)])

            sb = _supabase_client()
            hb_stop = asyncio.Event()
            hb_task = asyncio.create_task(
                _pipeline_heartbeat_loop(sb, relatorio_id, hb_stop)
            )

            # ADK pode ignorar asyncio.CancelledError enquanto tools síncronas /
            # thread pool rodam — o teto global em _run_pipeline_async cancela a
            # task; Layer 3 (_recover_stale_running_reports) corrige status no DB.
            try:
                async for _event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=message,
                ):
                    pass
            finally:
                hb_stop.set()
                hb_task.cancel()
                try:
                    await hb_task
                except asyncio.CancelledError:
                    pass

            run_id = _get_run_id()
            return _agregar_e_persistir_custos(sb, relatorio_id, run_id)
    finally:
        if enrichment_cv_token is not None:
            reset_pipeline_enrichment_context(enrichment_cv_token)
        current_relatorio_id.reset(token)


async def _run_pipeline_async(relatorio_id: str, payload: NovoRelatorioInput) -> None:
    """Roda o pipeline GymSite em background com retry em 429.

    Layer 1: envelope global de wall-clock (PIPELINE_MAX_WALL_SEC) com cancel da
    task — evita runs de 40+ min com status preso em running.

    Quando Vertex AI retorna 429 RESOURCE_EXHAUSTED (quota minute-rate
    estourada — frequente em bairros densos como Itaipu/Niterói), tentamos
    de novo após 30s/60s/120s. Pipeline raramente falha por quota.
    Limitação: o pipeline re-roda do início — custo dobra na pior hipótese.
    """
    sb = _supabase_client()
    t0 = time.time()
    try:
        sb.table("relatorios").update({"status": "running"}).eq("id", relatorio_id).execute()
    except Exception:
        pass

    body = asyncio.create_task(_run_pipeline_async_body(relatorio_id, payload, sb, t0))
    try:
        await asyncio.wait_for(body, timeout=float(_PIPELINE_MAX_WALL_SEC))
    except asyncio.TimeoutError:
        if not body.done():
            body.cancel()
            try:
                await body
            except (asyncio.CancelledError, Exception):
                pass
        elapsed = int(time.time() - t0)
        err = PipelineWallTimeoutError()
        logger.error(
            "pipeline %s excedeu wall-clock global (%ss): %s",
            relatorio_id,
            elapsed,
            err,
        )
        _mark_pipeline_failed(sb, relatorio_id, elapsed=elapsed, erro_mensagem=str(err))


async def _run_pipeline_async_body(
    relatorio_id: str,
    payload: NovoRelatorioInput,
    sb,
    t0: float,
) -> None:
    """Corpo do pipeline (retries 429 + ADK). Cancelável pelo envelope Layer 1."""
    custos: dict = {}
    last_exc: BaseException | None = None

    try:
        for tentativa, backoff in enumerate([0] + _RETRY_BACKOFFS_429):
            _ensure_pipeline_wall_clock(t0)
            if backoff > 0:
                logger.warning(
                    f"pipeline {relatorio_id} hit 429 — retry {tentativa}/{len(_RETRY_BACKOFFS_429)} "
                    f"em {backoff}s"
                )
                await asyncio.sleep(min(backoff, _pipeline_wall_remaining_sec(t0)))
                _ensure_pipeline_wall_clock(t0)
            try:
                remaining = _pipeline_wall_remaining_sec(t0)
                custos = await asyncio.wait_for(
                    _executar_pipeline_uma_vez(relatorio_id, payload),
                    timeout=remaining,
                )
                last_exc = None
                break  # sucesso
            except asyncio.TimeoutError:
                raise PipelineWallTimeoutError() from None
            except BaseException as e:
                if _is_429_error(e):
                    last_exc = e
                    continue  # tenta de novo após backoff
                raise  # outros erros não fazem retry

        if last_exc is not None:
            raise last_exc

        elapsed = int(time.time() - t0)
        ok_content, empty_err = validate_relatorio_has_content(sb, relatorio_id)
        if not ok_content:
            logger.error(
                "pipeline %s concluiu ADK sem conteúdo persistido: %s",
                relatorio_id,
                empty_err,
            )
            _mark_pipeline_failed(
                sb,
                relatorio_id,
                elapsed=elapsed,
                erro_mensagem=empty_err or EMPTY_REPORT_MSG,
            )
            return

        sb.table("relatorios").update({
            "status": "done",
            "tempo_execucao_segundos": elapsed,
            "tokens_total": custos.get("tokens_total"),
            "custo_brl": custos.get("custo_brl_total"),
        }).eq("id", relatorio_id).execute()
        logger.info(
            f"pipeline {relatorio_id} done em {elapsed}s — "
            f"tokens={custos.get('tokens_total')} custo=R$ {custos.get('custo_brl_total', 0):.4f}"
        )
        try:
            await notify_relatorio_pronto(relatorio_id, payload.cidade, status="done")
        except Exception as e:
            logger.warning(f"Falha ao notificar relatório pronto: {e}")

    except asyncio.CancelledError:
        raise
    except BaseException as e:
        logger.error(f"pipeline {relatorio_id} falhou: {e}\n{traceback.format_exc()}")
        elapsed = int(time.time() - t0)
        if isinstance(e, PipelineWallTimeoutError):
            erro_amigavel = str(e)
        elif _is_429_error(e):
            erro_amigavel = (
                "Pico de uso da Vertex AI — tente de novo em alguns minutos"
            )
        else:
            erro_amigavel = f"{type(e).__name__}: {e}"
        _mark_pipeline_failed(sb, relatorio_id, elapsed=elapsed, erro_mensagem=erro_amigavel)


def _agregar_e_persistir_custos(sb, relatorio_id: str, run_id: str | None) -> dict:
    """
    Lê o CSV de telemetria filtrando pelo run_id, agrega via pricing.py e:
      1. Persiste 1 linha por agente em relatorio_custos_agentes (UPSERT)
      2. Adiciona linha sintética "PlacesAPI" com custo das chamadas pra
         popular_times lib (1 call Places Details legacy por concorrente)
      3. Retorna o summary {tokens_total, custo_brl_total, por_agente}

    Falha silenciosa: se algo der errado, retorna dict vazio — não interrompe
    o fluxo de `done`. Custo é nice-to-have, não bloqueante.
    """
    if not run_id:
        return {}
    try:
        import csv
        from tools.pricing import aggregate_run_costs
        from tools.token_telemetry import CSV_PATH

        if not CSV_PATH.exists():
            return {}

        with CSV_PATH.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [r for r in reader if r.get("run_id") == run_id]

        if not rows:
            return {}

        summary = aggregate_run_costs(rows)

        # Custo Places API em standby (VEC-424) — popular_times_tool
        # não está sendo chamado, então não há custo Places legacy.
        # Quando LocalAPI for integrada, reativar contabilidade aqui.

        # Persiste por agente — UPSERT idempotente (re-execuções não duplicam).
        records = [
            {
                "relatorio_id": relatorio_id,
                "agente": agente,
                "modelo": dados.get("model") or "",
                "tokens_in": dados.get("tokens_in", 0),
                "tokens_out": dados.get("tokens_out", 0),
                "custo_brl": dados.get("custo_brl", 0.0),
            }
            for agente, dados in summary.get("por_agente", {}).items()
        ]

        if records:
            sb.table("relatorio_custos_agentes") \
              .upsert(records, on_conflict="relatorio_id,agente") \
              .execute()

        # Agrega custos de APIs externas gravados
        api_total = 0.0
        try:
            api_res = sb.table("relatorio_api_calls").select("custo_brl").eq("relatorio_id", relatorio_id).execute()
            if api_res.data:
                api_total = sum(float(r.get("custo_brl") or 0.0) for r in api_res.data)
        except Exception:
            pass

        # Soma o custo de API ao total geral do relatório
        summary["custo_brl_total"] = round(summary.get("custo_brl_total", 0.0) + api_total, 4)

        return summary
    except Exception as e:
        logger.warning(f"falha ao persistir custos do relatorio {relatorio_id}: {e}")
        return {}


def _contar_places_api_calls(sb, relatorio_id: str) -> int:
    """Retorna nº estimado de chamadas Places API legacy desse relatório.

    Heurística: 1 chamada por concorrente (popular_times lib). Cache 7d
    significa que segundo run no mesmo bairro NÃO conta — mas como o
    tracker é simples, assumimos 1 por concorrente. Em produção, evoluir
    pra um counter real no popular_times_tool gravado em log/state.
    """
    try:
        res = sb.table("competidores").select("place_id").eq("relatorio_id", relatorio_id).execute()
        return len(res.data or [])
    except Exception:
        return 0


def _build_pipeline_prompt(p: NovoRelatorioInput) -> str:
    """Prompt estruturado pro root_agent — força delegação imediata ao pipeline.

    Formato espelha o frontend `buildPipelinePayload`. O root_agent foi
    instruído (instruction em gymsite_intelligence/agent.py:148-154) a fazer
    transfer_to_agent("GymSitePipeline") em prompts deste formato.
    """
    uf_str = f"/{p.uf}" if p.uf else ""
    estac = "sim" if p.estacionamento_obrigatorio else "não"
    # Modo "cidade inteira" — sentinela acordada com o frontend pra evitar
    # migração de coluna NOT NULL no banco. A1 GeoScout interpreta isso como
    # "varrer todos os bairros do município, sem restrição".
    cidade_inteira = (p.bairro or "").strip().lower() == "(cidade inteira)"
    escopo = (
        f"em toda a cidade de {p.cidade}{uf_str} (sem restrição de bairro)"
        if cidade_inteira
        else f"em {p.bairro}, {p.cidade}{uf_str}"
    )
    lines = [
        f"Análise de viabilidade para {p.tipo_negocio.replace('_', ' ')} "
        f"{escopo}.",
        "Parâmetros:",
        f"- area_min: {p.area_m2_min} m²",
        f"- area_max: {p.area_m2_max} m²",
        f"- tamanho_preset: {p.tamanho_preset}",
        f"- publico_alvo: {p.publico_alvo}",
        f"- genero_alvo: {p.genero_alvo}",
        f"- tipo_negocio: {p.tipo_negocio}",
        f"- estacionamento_obrigatorio: {estac}",
    ]
    if p.bairros_indicados:
        lines.append(f"- bairros_indicados: {', '.join(p.bairros_indicados)}")
    lines.append("")
    lines.append("Rode o pipeline completo (GymSitePipeline) com esses parâmetros.")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health(probe: bool = False) -> dict:
    """
  Liveness + componentes críticos.
  ?probe=1 — ping Supabase (útil em deploy/CI; evite em probes de alta frequência).
    """
    from tools.health_components import health_payload

    return health_payload(probe_supabase=probe)


@app.get("/api/metrics")
def get_metrics() -> Response:
    """Métricas Prometheus-compatible (latência, throughput por rota)."""
    if _metrics_mw_instance is None:
        raise HTTPException(status_code=503, detail="Metrics middleware não inicializado")
    return Response(
        content=_metrics_mw_instance.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/health/maps")
def health_maps() -> dict:
    """Diagnóstico Google Maps + status do fallback OSM."""
    from tools.maps_health import check_google_maps
    from tools.maps_fallback import fallback_habilitado

    diag = check_google_maps()
    return {
        "service": "gymsite-intelligence-api",
        "google_maps": diag,
        "fallback_osm_enabled": fallback_habilitado(),
        "pipeline_unblocked": diag.get("ok") or fallback_habilitado(),
    }


@app.get("/api/geocode/bairro")
def geocode_bairro_endpoint(
    bairro: str,
    cidade: str,
    uf: str | None = None,
) -> dict:
    """Centro aproximado do bairro (mapa de relatórios — não pin de imóvel)."""
    from tools.maps_tools import geocode_endereco

    parts = [p.strip() for p in (bairro, cidade, uf or "", "Brasil") if p and p.strip()]
    endereco = ", ".join(parts)
    return geocode_endereco(endereco)


@app.get("/api/geocode/cidade")
def geocode_cidade_endpoint(cidade: str, uf: str | None = None) -> dict:
    """Centro do município — bounds iniciais do mapa no viewer (não Brasil)."""
    from tools.mapa_mercado import _geocode_cidade

    return _geocode_cidade(cidade, (uf or "").strip())


@app.get("/api/maps/street-view")
def maps_street_view_proxy(
    lat: float,
    lng: float,
    w: int = 640,
    h: int = 400,
):
    """Proxy Street View Static — chave Google só no servidor."""
    from fastapi.responses import Response
    from tools.maps_street_view import build_street_view_google_url
    from tools.google_maps_key import get_google_maps_api_key

    if not get_google_maps_api_key():
        raise HTTPException(status_code=503, detail="GOOGLE_MAPS_API_KEY ausente")
    url = build_street_view_google_url(lat, lng, width=w, height=h)
    try:
        import httpx

        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get(url)
        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Street View HTTP {r.status_code}",
            )
        ctype = r.headers.get("content-type") or "image/jpeg"
        return Response(content=r.content, media_type=ctype)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/config/maps-js")
def maps_js_config_endpoint() -> dict:
    """
    Config para Maps JavaScript API (heatmap /mapa).
    Chave permanece server-side — mesmo padrão do proxy places-autocomplete.
    """
    from tools.maps_js_config import maps_js_config

    return maps_js_config()


@app.post("/api/places-autocomplete")
def places_autocomplete_endpoint(body: PlacesAutocompleteInput) -> dict:
    """
    Proxy Google Places (New) para autocomplete de bairros.
    Usado pelo frontend em /relatorios/new — chave só no servidor.
    """
    from tools.places_autocomplete import places_autocomplete

    return places_autocomplete(
        input_text=body.input,
        municipio=body.municipio,
        uf=body.uf,
        lat=body.lat,
        lng=body.lng,
    )


def _resolve_user_and_org(request: Request) -> tuple[str | None, str]:
    """Extrai user_id e org_id do JWT (Authorization: Bearer)."""
    default_org = os.getenv("SUPABASE_GYMSITE_ORG_ID") or _DEFAULT_ORG_ID
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None, default_org

    token = auth[7:].strip()
    if not token:
        return None, default_org

    try:
        sb = _supabase_client()
        user_resp = sb.auth.get_user(token)
        user = user_resp.user if user_resp else None
        if not user:
            return None, default_org

        mem = (
            sb.table("organization_members")
            .select("org_id")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        org_id = mem.data[0]["org_id"] if mem.data else default_org
        return user.id, org_id
    except Exception as e:
        logger.warning("Falha ao resolver user/org do JWT: %s", e)
        return None, default_org


def _user_org_ids(sb, user_id: str) -> list[str]:
    """Retorna todas as org_ids que o usuário pertence."""
    if not user_id:
        return []
    try:
        mem = sb.table("organization_members").select("org_id").eq("user_id", user_id).execute()
        return [str(r["org_id"]) for r in (mem.data or [])]
    except Exception:
        return []


def _require_authenticated(request: Request) -> tuple[str, str]:
    """Exige JWT válido; retorna (user_id, org_id)."""
    user_id, org_id = _resolve_user_and_org(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user_id, org_id


def _require_org_access(request: Request, org_id: str) -> str:
    """Exige que o usuário pertença à org informada."""
    user_id, _ = _require_authenticated(request)
    sb = _supabase_client()
    orgs = _user_org_ids(sb, user_id)
    if org_id not in orgs:
        raise HTTPException(status_code=403, detail="Sem permissão para esta organização")
    return user_id


def _assert_relatorio_access(request: Request, sb, rid: str, access_code: str | None = None) -> None:
    """Se JWT presente, valida org do relatório (espelha RLS Supabase).
    Se access_code presente, valida com o access_code do relatório e permite acesso."""
    
    if access_code:
        res = sb.table("relatorios").select("access_code").eq("id", rid).maybe_single().execute()
        row = res.data if res else None
        if not row:
            raise HTTPException(status_code=404, detail="relatório não encontrado")
        
        db_code = row.get("access_code")
        if not db_code or str(db_code) != access_code:
            raise HTTPException(status_code=403, detail="access_code inválido ou não autorizado")
            
        from datetime import datetime, timezone
        sb.table("relatorios").update({"access_code_used_at": datetime.now(timezone.utc).isoformat()}).eq("id", rid).execute()
        return

    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return
    user_id, _ = _require_authenticated(request)
    res = (
        sb.table("relatorios")
        .select("org_id")
        .eq("id", rid)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    row = res.data if res else None
    if not row:
        raise HTTPException(status_code=404, detail="relatório não encontrado")
    org_id = str(row.get("org_id") or "")
    if not org_id:
        return
    orgs = _user_org_ids(sb, user_id)
    if org_id not in orgs:
        raise HTTPException(status_code=403, detail="Sem permissão para este relatório")


def _assert_oportunidade_access(request: Request, oportunidade_id: str) -> dict:
    """Carrega oportunidade e valida org do usuário."""
    from prospecting.engine import get_oportunidade

    user_id, org_id = _require_authenticated(request)
    opp = get_oportunidade(oportunidade_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
    opp_org = opp.get("org_id")
    if opp_org:
        sb = _supabase_client()
        orgs = _user_org_ids(sb, user_id)
        if str(opp_org) not in orgs:
            raise HTTPException(status_code=403, detail="Sem permissão")
    return opp


def create_relatorio_stub(
    payload: NovoRelatorioInput,
    *,
    org_id: str | None = None,
    user_id: str | None = None,
) -> tuple[str, str | None]:
    """
    Cria header + inputs no Supabase (status=queued).
    Retorna (relatorio_id, created_at).
    Usado pela API HTTP e pelo CLI — garante FK antes do pipeline gravar outputs.
    """
    sb = _supabase_client()
    resolved_org = org_id or payload.org_id or os.getenv("SUPABASE_GYMSITE_ORG_ID") or _DEFAULT_ORG_ID

    res = sb.table("relatorios").insert({
        "org_id": resolved_org,
        "user_id": user_id,
        "tipo_relatorio": "prospeccao_academia",
        "status": "queued",
        "schema_version": "1.6",
    }).execute()
    if not res.data:
        raise RuntimeError("falha ao criar header do relatório")
    relatorio_id = res.data[0]["id"]
    created_at = res.data[0].get("created_at")

    sb.table("relatorio_inputs").insert({
        "relatorio_id": relatorio_id,
        "cidade": payload.cidade,
        "uf": (payload.uf or "")[:2] or None,
        "bairro": payload.bairro,
        "area_m2_min": payload.area_m2_min,
        "area_m2_max": payload.area_m2_max,
        "tamanho_preset": payload.tamanho_preset,
        "publico_alvo": payload.publico_alvo,
        "genero_alvo": payload.genero_alvo,
        "tipo_negocio": payload.tipo_negocio,
        "estacionamento_obrigatorio": payload.estacionamento_obrigatorio,
        "bairros_indicados": payload.bairros_indicados,
        "a0_research_provider": (payload.a0_research_provider or "auto")[:16],
    }).execute()

    return relatorio_id, created_at


@app.post("/api/relatorios", response_model=RelatorioStub)
async def create_relatorio(
    payload: NovoRelatorioInput,
    request: Request,
) -> RelatorioStub:
    """Cria stub do relatório + enfileira pipeline no Redis. Retorna ID pra polling."""
    with span("api.relatorios.create", cidade=payload.cidade, uf=payload.uf):
        user_id, org_from_jwt = _resolve_user_and_org(request)
        try:
            relatorio_id, created_at = create_relatorio_stub(
                payload,
                org_id=payload.org_id or org_from_jwt,
                user_id=user_id,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        if _queue is None:
            raise HTTPException(status_code=503, detail="Task queue não inicializado")

        await _queue.enqueue({
            "type": "pipeline",
            "relatorio_id": relatorio_id,
            "payload": payload.model_dump(),
        })

        return RelatorioStub(
            id=relatorio_id,
            status="queued",
            created_at=created_at,
        )


@app.get("/api/relatorios/{relatorio_id}/status")
def get_status(relatorio_id: str) -> dict:
    """Polling leve. Retorna só status + erro se falhou."""
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    _recover_stale_running_reports(sb, relatorio_id=rid)
    _recover_done_empty_reports(sb, relatorio_id=rid)
    res = (
        sb.table("relatorios")
        .select("id, status, erro_mensagem, tempo_execucao_segundos, data_execucao")
        .eq("id", rid)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not res or not res.data:
        raise HTTPException(status_code=404, detail="relatório não encontrado")
    return res.data


def _fetch_relatorio_payload(sb: Any, rid: str) -> dict:
    """Detail completo: joins de todas as tabelas filhas."""
    header = (
        sb.table("relatorios")
        .select("*")
        .eq("id", rid)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not header or not header.data:
        raise HTTPException(status_code=404, detail="relatório não encontrado")

    inputs = sb.table("relatorio_inputs").select("*").eq("relatorio_id", rid).maybe_single().execute()
    outputs = sb.table("relatorio_outputs").select("*").eq("relatorio_id", rid).maybe_single().execute()
    candidatos = sb.table("candidatos").select("*").eq("relatorio_id", rid).order("posicao").execute()
    competidores = sb.table("competidores").select("*").eq("relatorio_id", rid).execute()
    cenarios = sb.table("cenarios_financeiros").select("*").eq("relatorio_id", rid).execute()
    sensibilidade = sb.table("sensibilidade_cenarios").select("*").eq("relatorio_id", rid).execute()
    bairros_alt = sb.table("bairros_alternativos").select("*").eq("relatorio_id", rid).order("ordem").execute()
    validacao = (
        sb.table("validacoes")
        .select("*")
        .eq("relatorio_id", rid)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    return {
        "id": rid,
        "header": header.data,
        "input_canonico": inputs.data if inputs else None,
        "output_consolidado": outputs.data if outputs else None,
        "candidatos": candidatos.data or [],
        "competidores": competidores.data or [],
        "cenarios": cenarios.data or [],
        "sensibilidade": sensibilidade.data or [],
        "bairros_alternativos": bairros_alt.data or [],
        "validacao_a8": (validacao.data or [None])[0],
    }


@app.get("/api/relatorios/{relatorio_id}")
def get_relatorio(relatorio_id: str, request: Request, access_code: str | None = None) -> dict:
    """Detail completo: joins de todas as tabelas filhas."""
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    _assert_relatorio_access(request, sb, rid, access_code=access_code)
    _recover_done_empty_reports(sb, relatorio_id=rid)
    return _fetch_relatorio_payload(sb, rid)


@app.get("/api/relatorios/{relatorio_id}/mapa-mercado")
def get_mapa_mercado(relatorio_id: str, request: Request) -> dict:
    """
    Pins + heat de concorrentes e entrantes CNPJ (90d) no município do relatório.
    Geocodifica entrantes sem lat (cap 25). Não persiste coords no JSON do output.
    Cache Redis 5 min (middleware). JWT opcional — se presente, valida org (RLS).
    """
    from tools.mapa_mercado import build_mapa_mercado_payload

    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    _assert_relatorio_access(request, sb, rid)
    payload = _fetch_relatorio_payload(sb, rid)
    inp = payload.get("input_canonico") or {}
    out = payload.get("output_consolidado") or {}
    cidade = (inp.get("cidade") or out.get("cidade_efetiva") or "").strip()
    uf = (inp.get("uf") or "").strip()
    bairro = (inp.get("bairro") or "").strip()
    if not cidade:
        raise HTTPException(status_code=400, detail="cidade ausente no relatório")

    top = (payload.get("candidatos") or [])[:1]
    site_lat = site_lng = None
    if top and isinstance(top[0], dict):
        try:
            site_lat = float(top[0]["lat"]) if top[0].get("lat") is not None else None
            site_lng = float(top[0]["lng"]) if top[0].get("lng") is not None else None
        except (TypeError, ValueError):
            site_lat = site_lng = None

    return build_mapa_mercado_payload(
        cidade=cidade,
        uf=uf,
        bairro=bairro,
        competidores=payload.get("competidores") or [],
        entrantes_block=out.get("entrantes_cnpj_90d"),
        site_lat=site_lat,
        site_lng=site_lng,
    )


class EntranteValidacaoInput(BaseModel):
    cnpj: str = Field(..., min_length=11, max_length=18)
    validado: bool = True


@app.patch("/api/relatorios/{relatorio_id}/entrantes-cnpj/validacao")
def patch_entrante_validacao(relatorio_id: str, body: EntranteValidacaoInput) -> dict:
    """Marca contato do entrant como validado manualmente (persiste em entrantes_cnpj_90d)."""
    import re

    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    cnpj_limpo = re.sub(r"\D", "", body.cnpj)
    if len(cnpj_limpo) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido")

    out_res = (
        sb.table("relatorio_outputs")
        .select("entrantes_cnpj_90d")
        .eq("relatorio_id", rid)
        .maybe_single()
        .execute()
    )
    block = (out_res.data or {}).get("entrantes_cnpj_90d") if out_res.data else None
    if not isinstance(block, dict):
        raise HTTPException(status_code=404, detail="entrantes_cnpj_90d não encontrado")

    entrantes = block.get("entrantes") or []
    found = False
    now = datetime.now(timezone.utc).isoformat()
    for ent in entrantes:
        if not isinstance(ent, dict):
            continue
        ecnpj = re.sub(r"\D", "", str(ent.get("cnpj") or ""))
        if ecnpj == cnpj_limpo:
            ent["contato_validado"] = body.validado
            ent["contato_validado_em"] = now if body.validado else None
            ent["contato_validado_por"] = "usuario_ui" if body.validado else None
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="CNPJ não está na lista de entrantes")

    block["entrantes"] = entrantes
    sb.table("relatorio_outputs").update({"entrantes_cnpj_90d": block}).eq(
        "relatorio_id", rid
    ).execute()
    return {"ok": True, "cnpj": cnpj_limpo, "contato_validado": body.validado}


class EntranteEnriquecerInput(BaseModel):
    cnpj: str = Field(..., min_length=11, max_length=18)
    usar_apollo: bool = True


class EntrantesProspeccaoInput(BaseModel):
    cnpjs: list[str] = Field(..., min_length=1)
    cidade: str = "Fortaleza"
    uf: str = "CE"


@app.post("/api/relatorios/{relatorio_id}/entrantes-cnpj/enriquecer")
def post_entrante_enriquecer(relatorio_id: str, body: EntranteEnriquecerInput) -> dict:
    """
    Enriquece um entrante (ReceitaWS + Apollo opcional) e persiste em entrantes_cnpj_90d.
    Disparo manual — não roda no pipeline A6.
    """
    import re

    from tools.cnpj_enrichment import enriquecer_entrante_unico

    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    cnpj_limpo = re.sub(r"\D", "", body.cnpj)
    if len(cnpj_limpo) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido")

    out_res = (
        sb.table("relatorio_outputs")
        .select("entrantes_cnpj_90d")
        .eq("relatorio_id", rid)
        .maybe_single()
        .execute()
    )
    block = (out_res.data or {}).get("entrantes_cnpj_90d") if out_res.data else None
    if not isinstance(block, dict):
        raise HTTPException(status_code=404, detail="entrantes_cnpj_90d não encontrado")

    entrantes = block.get("entrantes") or []
    idx = None
    ent_raw: dict | None = None
    for i, ent in enumerate(entrantes):
        if not isinstance(ent, dict):
            continue
        ecnpj = re.sub(r"\D", "", str(ent.get("cnpj") or ""))
        if ecnpj == cnpj_limpo:
            idx = i
            ent_raw = ent
            break
    if ent_raw is None or idx is None:
        raise HTTPException(status_code=404, detail="CNPJ não está na lista de entrantes")

    enriched, meta = enriquecer_entrante_unico(
        ent_raw,
        usar_apollo=body.usar_apollo,
        max_receita=1,
        forcar_receita=True,
    )
    entrantes[idx] = enriched
    block["entrantes"] = entrantes
    meta_prev = block.get("enriquecimento_meta")
    if not isinstance(meta_prev, dict):
        meta_prev = {}
    meta_prev[f"manual_{cnpj_limpo}"] = meta
    block["enriquecimento_meta"] = meta_prev

    sb.table("relatorio_outputs").update({"entrantes_cnpj_90d": block}).eq(
        "relatorio_id", rid
    ).execute()
    return {"ok": True, "cnpj": cnpj_limpo, "entrante": enriched, "meta": meta}


@app.post("/api/relatorios/{relatorio_id}/entrantes-cnpj/prospeccao")
def post_entrantes_para_prospeccao(
    request: Request,
    relatorio_id: str,
    body: EntrantesProspeccaoInput,
) -> dict:
    """
    Envia CNPJs selecionados no relatório para a área de prospecção
    (oportunidades_prospeccao), mesmo sem match CNO.
    """
    import re

    user_id, _ = _require_authenticated(request)
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    _assert_relatorio_access(request, sb, rid)

    # Usa o org_id do relatório (não do usuário) para manter consistência
    rel_row = (
        sb.table("relatorios")
        .select("org_id")
        .eq("id", rid)
        .maybe_single()
        .execute()
    )
    org_id = str(rel_row.data["org_id"]) if rel_row.data and rel_row.data.get("org_id") else None
    if not org_id:
        raise HTTPException(status_code=400, detail="Relatório sem org_id associado")

    out_res = (
        sb.table("relatorio_outputs")
        .select("entrantes_cnpj_90d")
        .eq("relatorio_id", rid)
        .maybe_single()
        .execute()
    )
    block = (out_res.data or {}).get("entrantes_cnpj_90d") if out_res.data else None
    if not isinstance(block, dict):
        raise HTTPException(status_code=404, detail="entrantes_cnpj_90d não encontrado")

    entrantes = block.get("entrantes") or []
    cnpj_idx: dict[str, dict] = {}
    for ent in entrantes:
        if not isinstance(ent, dict):
            continue
        ecnpj = re.sub(r"\D", "", str(ent.get("cnpj") or ""))
        if len(ecnpj) == 14:
            cnpj_idx[ecnpj] = ent

    inseridos: list[str] = []
    ignorados: list[str] = []
    erros: list[dict] = []

    for cnpj_raw in body.cnpjs:
        cnpj_limpo = re.sub(r"\D", "", cnpj_raw)
        if len(cnpj_limpo) != 14:
            erros.append({"cnpj": cnpj_raw, "motivo": "CNPJ inválido"})
            continue

        ent = cnpj_idx.get(cnpj_limpo)
        if not ent:
            erros.append({"cnpj": cnpj_limpo, "motivo": "CNPJ não encontrado no relatório"})
            continue

        # Endereço
        endereco_raw = (ent.get("endereco") or "").strip()
        numero = ""
        logradouro = endereco_raw
        if "," in endereco_raw:
            parts = [p.strip() for p in endereco_raw.rsplit(",", 1)]
            logradouro, numero = parts[0], parts[1]

        # Contato
        socio = ent.get("socio_administrador") or {}
        email = ent.get("email_socio_administrador") or ent.get("email_empresa")
        telefone = ent.get("telefone_socio_administrador") or ent.get("telefone_empresa")
        tel_digits = re.sub(r"\D", "", telefone or "")

        row = {
            "org_id": org_id,
            "cnpj": cnpj_limpo,
            "cidade": body.cidade,
            "uf": body.uf,
            "razao_social": ent.get("razao_social"),
            "nome_fantasia": ent.get("nome_fantasia") or ent.get("nome_exibicao"),
            "segmento_operacao": ent.get("segmento_operacao"),
            "data_inicio_atividade": ent.get("data_abertura"),
            "endereco_cnpj": {
                "logradouro": logradouro or None,
                "numero": numero or None,
                "bairro": ent.get("bairro"),
                "cidade": body.cidade,
                "uf": body.uf,
            },
            "contato_cnpj": {
                "decision_maker": socio.get("nome") if isinstance(socio, dict) else None,
                "cargo": "Sócio-administrador",
                "email": email,
                "telefone": telefone,
                "whatsapp_link": f"https://wa.me/55{tel_digits}" if tel_digits else None,
            },
            "score_match": None,
            "motivo_match": "manual_relatorio",
            "status": "novo",
            "prioridade": "media",
        }

        try:
            # Upsert baseado em cnpj + cno null (mesma semântica do engine)
            existing = (
                sb.table("oportunidades_prospeccao")
                .select("id")
                .eq("cnpj", cnpj_limpo)
                .is_("cno", "null")
                .limit(1)
                .execute()
            )
            if existing.data:
                sb.table("oportunidades_prospeccao").update(row).eq("id", existing.data[0]["id"]).execute()
                ignorados.append(cnpj_limpo)
            else:
                sb.table("oportunidades_prospeccao").insert(row).execute()
                inseridos.append(cnpj_limpo)
        except Exception as e:
            logger.warning("Erro ao enviar CNPJ %s para prospecção: %s", cnpj_limpo, e)
            erros.append({"cnpj": cnpj_limpo, "motivo": f"Erro no Supabase: {e}"})

    return {
        "ok": True,
        "relatorio_id": rid,
        "org_id": org_id,
        "inseridos": inseridos,
        "atualizados": ignorados,
        "erros": erros,
        "total_enviados": len(inseridos) + len(ignorados),
    }


def _persistir_sync_apollo(sb, oportunidade_id: str, result: dict, log_atual: list) -> None:
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc).isoformat()
    update = {
        "apollo_sync_status": result.get("sync_status", "failed"),
        "apollo_person_id": result.get("apollo_person_id"),
        "apollo_account_id": result.get("apollo_account_id"),
        "apollo_sync_error": result.get("erro"),
        "apollo_enrichment_log": (log_atual or []) + [{
            "timestamp": agora,
            "ok": result.get("ok", False),
            "enriched": bool(result.get("enriched")),
        }],
    }
    if result.get("sync_status") == "synced":
        update["apollo_synced_at"] = agora
    sb.table("oportunidades_prospeccao").update(update).eq("id", oportunidade_id).execute()


@app.post("/api/prospeccao/oportunidades/{oportunidade_id}/sync-apollo")
def post_sync_apollo_oportunidade(
    request: Request, oportunidade_id: str, force: bool = False
) -> dict:
    """Sincroniza UMA oportunidade com o Apollo.io (gatilho manual — consome créditos)."""
    from services.apollo_crm_sync import sync_oportunidade

    _require_authenticated(request)
    sb = _supabase_client()
    row = (
        sb.table("oportunidades_prospeccao")
        .select("*")
        .eq("id", oportunidade_id)
        .maybe_single()
        .execute()
    )
    if not row or not row.data:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

    result = sync_oportunidade(row.data, force=force)
    if result.get("skipped"):
        return {"ok": True, "skipped": True, "motivo": result.get("motivo")}

    _persistir_sync_apollo(sb, oportunidade_id, result, row.data.get("apollo_enrichment_log"))
    return {
        "ok": result.get("ok", False),
        "sync_status": result.get("sync_status"),
        "apollo_person_id": result.get("apollo_person_id"),
        "apollo_account_id": result.get("apollo_account_id"),
        "erro": result.get("erro"),
    }


@app.post("/api/prospeccao/sync-apollo")
def post_sync_apollo_pendentes(request: Request, limite: int = 20) -> dict:
    """Sincroniza oportunidades pendentes com o Apollo.io em lote (gatilho manual)."""
    from services.apollo_crm_sync import sync_oportunidade

    _require_authenticated(request)
    limite = max(1, min(limite, 50))
    sb = _supabase_client()
    rows = (
        sb.table("oportunidades_prospeccao")
        .select("*")
        .eq("apollo_sync_status", "pending")
        .order("updated_at", desc=True)
        .limit(limite)
        .execute()
    )
    pendentes = rows.data or []

    synced, failed = 0, 0
    erros = []
    for opp in pendentes:
        try:
            result = sync_oportunidade(opp)
            _persistir_sync_apollo(sb, opp["id"], result, opp.get("apollo_enrichment_log"))
            if result.get("sync_status") == "synced":
                synced += 1
            else:
                failed += 1
                erros.append({"id": opp["id"], "erro": result.get("erro")})
        except Exception as e:
            failed += 1
            erros.append({"id": opp.get("id"), "erro": str(e)})
            logger.warning("Sync Apollo falhou para oportunidade %s: %s", opp.get("id"), e)

    return {
        "ok": True,
        "total_pendentes": len(pendentes),
        "sincronizados": synced,
        "falhas": failed,
        "erros": erros,
    }


@app.get("/api/relatorios/{relatorio_id}/pdf")
def get_relatorio_pdf(relatorio_id: str, layout: str = "classic") -> Any:
    """PDF estruturado do relatório (ReportLab + gráficos)."""
    from fastapi.responses import Response

    from pdf import LayoutId, generate_relatorio_pdf
    from pdf.adapters import relatorio_from_api_payload

    try:
        layout_id = LayoutId(layout)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"layout inválido (use: classic, executive, data_room): {layout}",
        ) from e

    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    payload = _fetch_relatorio_payload(sb, rid)
    status = (payload.get("header") or {}).get("status")
    if status and status != "done":
        raise HTTPException(
            status_code=400,
            detail=f"relatório ainda não está pronto (status={status})",
        )

    model = relatorio_from_api_payload(payload)
    pdf_bytes = generate_relatorio_pdf(model, layout=layout_id)
    slug = f"gymsite-{model.bairro}-{model.cidade}".replace(" ", "-")
    slug = "".join(c if c.isalnum() or c in "-_" else "" for c in slug)[:48] or "relatorio"
    # ASCII-safe fallback + RFC 5987 encoding for non-ASCII chars
    from urllib.parse import quote
    slug_ascii = slug.encode("ascii", "ignore").decode("ascii") or "relatorio"
    slug_utf8 = quote(slug, safe="-_")
    dispo = (
        f'attachment; filename="{slug_ascii}.pdf"; '
        f"filename*=UTF-8''{slug_utf8}.pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": dispo,
            "Cache-Control": "private, max-age=300",
        },
    )


def _run_canal_probe(canal: str, body: CanalProbeInput) -> dict:
    from tools.canais_probe import probe_cnpj, probe_kimi, probe_osm, probe_places

    cidade = body.cidade.strip()
    bairro = body.bairro.strip()
    uf = (body.uf or "")[:2]
    if not cidade or not bairro:
        raise HTTPException(status_code=400, detail="cidade e bairro são obrigatórios")

    runners = {
        "places": lambda: probe_places(bairro, cidade, uf, raio_metros=body.raio_metros),
        "osm": lambda: probe_osm(bairro, cidade, uf, raio_metros=body.raio_metros),
        "cnpj": lambda: probe_cnpj(bairro, cidade, uf),
        "kimi": lambda: probe_kimi(
            cidade,
            bairro,
            tipo_negocio=body.tipo_negocio,
            publico_alvo=body.publico_alvo,
            force_refresh=True,
        ),
    }
    fn = runners.get(canal)
    if not fn:
        raise HTTPException(status_code=404, detail=f"canal desconhecido: {canal}")

    try:
        return fn()
    except Exception as e:
        logger.exception("canal %s falhou: %s", canal, e)
        return {
            "canal": canal,
            "ok": False,
            "erro": f"{type(e).__name__}: {e}",
        }


@app.post("/api/canais/places")
def canal_places(body: CanalProbeInput) -> dict:
    """Run now — Google Places (geocode + nearby gym)."""
    return _run_canal_probe("places", body)


@app.post("/api/canais/osm")
def canal_osm(body: CanalProbeInput) -> dict:
    """Run now — OpenStreetMap / Overpass (ignora Places)."""
    return _run_canal_probe("osm", body)


@app.post("/api/canais/cnpj")
def canal_cnpj(body: CanalProbeInput) -> dict:
    """Run now — parque CNPJ fitness no bairro (RFB / Supabase)."""
    return _run_canal_probe("cnpj", body)


@app.post("/api/canais/kimi-research")
def canal_kimi_research(body: CanalProbeInput) -> dict:
    """Run now — Kimi / OpenClaw (5 pesquisas paralelas → cache markdown A0)."""
    return _run_canal_probe("kimi", body)


@app.get("/api/canais/status")
def canais_status() -> dict:
    """Diagnóstico rápido dos canais (sem executar probe pesado)."""
    from tools.kimi_research import _openclaw_configured, kimi_provider_ativo
    from tools.maps_health import check_google_maps
    from tools.maps_fallback import fallback_habilitado

    maps = check_google_maps()
    return {
        "kimi_provider_ativo": kimi_provider_ativo(),
        "openclaw_configured": _openclaw_configured(),
        "maps_ok": maps.get("ok"),
        "maps_fallback": fallback_habilitado(),
        "google_maps": maps,
    }


@app.get("/api/relatorios/{relatorio_id}/custos-api")
def get_relatorio_custos_api(relatorio_id: str) -> dict:
    """Retorna o breakdown de custos de LLM e APIs externas do relatório."""
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    
    # 1. Obter os custos dos agentes (LLM)
    llm_por_agente = {}
    llm_total = 0.0
    try:
        res_agents = sb.table("relatorio_custos_agentes").select("agente, modelo, tokens_in, tokens_out, custo_brl").eq("relatorio_id", rid).execute()
        if res_agents.data:
            for row in res_agents.data:
                agente = row["agente"]
                custo = float(row["custo_brl"] or 0.0)
                llm_por_agente[agente] = {
                    "modelo": row["modelo"] or "",
                    "tokens_in": int(row["tokens_in"] or 0),
                    "tokens_out": int(row["tokens_out"] or 0),
                    "custo_brl": custo
                }
                llm_total += custo
    except Exception as e:
        logger.warning(f"Erro ao buscar custos de agentes: {e}")

    # 2. Obter os custos das APIs
    api_por_sku = {}
    api_total = 0.0
    try:
        res_apis = sb.table("relatorio_api_calls").select("api_sku, num_calls, custo_brl").eq("relatorio_id", rid).execute()
        if res_apis.data:
            for row in res_apis.data:
                sku = row["api_sku"]
                calls = int(row["num_calls"] or 0)
                custo = float(row["custo_brl"] or 0.0)
                if sku in api_por_sku:
                    api_por_sku[sku]["calls"] += calls
                    api_por_sku[sku]["custo_brl"] += custo
                else:
                    api_por_sku[sku] = {
                        "calls": calls,
                        "custo_brl": custo
                    }
                api_total += custo
    except Exception as e:
        logger.warning(f"Erro ao buscar custos de APIs: {e}")

    # 3. Retornar estrutura esperada pelo frontend
    return {
        "llm": {
            "total_brl": round(llm_total, 4),
            "por_agente": llm_por_agente
        },
        "api": {
            "total_brl": round(api_total, 4),
            "por_sku": api_por_sku
        },
        "total_brl": round(llm_total + api_total, 4)
    }


@app.get("/api/custos/optimizations")
def get_custos_optimizations(dias: int = 30) -> dict:
    """Retorna sugestões de otimização de custo baseadas no tokens_pipeline.csv."""
    from tools.cost_optimizations import gerar_optimizacoes
    with span("api.custos.optimizations", dias=dias):
        return gerar_optimizacoes(dias=dias)


# ── Propostas de Otimização — Governança de Custo ──────────────────────────

from pydantic import BaseModel

class PropostaCreateInput(BaseModel):
    tipo: str
    agente: str
    modelo_atual: str = ""
    modelo_sugerido: str = ""
    titulo: str
    descricao: str
    economia_brl_estimada: float = 0.0
    severidade: str = "media"
    referencia_dados: dict | None = None


class PropostaUpdateInput(BaseModel):
    status: str
    justificativa: str = ""
    resultado_observacao: str = ""
    economia_brl_real: float | None = None


@app.get("/api/custos/propostas")
def list_propostas_otimizacao(request: Request, status: str | None = None) -> list[dict]:
    """Lista propostas de otimização da org do usuário autenticado."""
    user_id, _ = _require_authenticated(request)
    sb = _supabase_client()
    orgs = _user_org_ids(sb, user_id)
    if not orgs:
        return []

    q = sb.table("otimizacoes_custo").select("*").in_("org_id", orgs).order("criado_em", desc=True)
    if status:
        q = q.eq("status", status)
    res = q.execute()
    return res.data or []


@app.post("/api/custos/propostas")
def criar_proposta_otimizacao(request: Request, body: PropostaCreateInput) -> dict:
    """Cria uma proposta de otimização para a org do usuário autenticado."""
    user_id, _ = _require_authenticated(request)
    sb = _supabase_client()
    orgs = _user_org_ids(sb, user_id)
    if not orgs:
        raise HTTPException(status_code=403, detail="Usuário sem org")

    record = {
        "org_id": orgs[0],
        "criado_por": user_id,
        "tipo": body.tipo,
        "agente": body.agente,
        "modelo_atual": body.modelo_atual,
        "modelo_sugerido": body.modelo_sugerido,
        "titulo": body.titulo,
        "descricao": body.descricao,
        "economia_brl_estimada": body.economia_brl_estimada,
        "severidade": body.severidade,
        "referencia_dados": body.referencia_dados,
    }
    res = sb.table("otimizacoes_custo").insert(record).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Falha ao criar proposta")
    return res.data[0]


@app.patch("/api/custos/propostas/{proposta_id}")
def atualizar_proposta_otimizacao(
    request: Request, proposta_id: str, body: PropostaUpdateInput
) -> dict:
    """Atualiza status de uma proposta (aprovar, rejeitar, implementar)."""
    user_id, _ = _require_authenticated(request)
    sb = _supabase_client()

    # Busca proposta para validar permissão
    res_get = (
        sb.table("otimizacoes_custo")
        .select("*")
        .eq("id", proposta_id)
        .maybe_single()
        .execute()
    )
    if not res_get or not res_get.data:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    proposta = res_get.data
    orgs = _user_org_ids(sb, user_id)
    if str(proposta["org_id"]) not in orgs:
        raise HTTPException(status_code=403, detail="Sem permissão")

    update: dict = {"status": body.status}
    now = datetime.now(timezone.utc).isoformat()

    if body.status == "aprovada":
        update["aprovado_por"] = user_id
        update["aprovado_em"] = now
        update["justificativa_aprovacao"] = body.justificativa
    elif body.status == "implementada":
        update["implementado_por"] = user_id
        update["implementado_em"] = now
        update["resultado_observacao"] = body.resultado_observacao
        if body.economia_brl_real is not None:
            update["economia_brl_real"] = body.economia_brl_real
    elif body.status == "rejeitada":
        update["justificativa_aprovacao"] = body.justificativa

    res = sb.table("otimizacoes_custo").update(update).eq("id", proposta_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Falha ao atualizar proposta")
    return res.data[0]


@app.get("/api/relatorios")
def list_relatorios(
    cidade: Optional[str] = None,
    veredito: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Lista resumida usando a view v_relatorios_resumo."""
    sb = _supabase_client()
    q = sb.table("v_relatorios_resumo").select("*").order("created_at", desc=True).limit(limit)
    if cidade:
        q = q.ilike("cidade", f"%{cidade}%")
    if veredito:
        q = q.eq("veredito", veredito)
    if since:
        q = q.gte("created_at", since)
    res = q.execute()
    return res.data or []


# ════════════════════════════════════════════════════════════════════════════
# Prospecção CNPJ × CNO → Claw
# ════════════════════════════════════════════════════════════════════════════

class ProspeccaoExecutarInput(BaseModel):
    cidade: str
    uf: str = "CE"
    dias: int = 90
    limit: int = 500
    org_id: Optional[str] = None
    webhook_url: Optional[str] = None


class ProspeccaoStatusPatch(BaseModel):
    status: str = Field(..., pattern=r"^(novo|qualificado|webhook_enviado|engajado|fechado|descartado)$")


class WebhookConfigureInput(BaseModel):
    org_id: str
    webhook_url: str


@app.post("/api/prospeccao/executar")
async def executar_prospeccao(
    request: Request,
    payload: ProspeccaoExecutarInput,
) -> dict:
    """Enfileira engine de cruzamento CNPJ × CNO no Redis."""
    _, org_id = _require_authenticated(request)
    with span("api.prospeccao.executar", cidade=payload.cidade, uf=payload.uf):
        if _queue is None:
            raise HTTPException(status_code=503, detail="Task queue não inicializado")

        await _queue.enqueue({
            "type": "prospeccao",
            "kwargs": {
                "cidade": payload.cidade,
                "uf": payload.uf,
                "dias": payload.dias,
                "limit": payload.limit,
                "org_id": payload.org_id or org_id,
                "webhook_url": payload.webhook_url,
            },
        })
        return {
            "status": "started",
            "message": f"Prospecção enfileirada para {payload.cidade}/{payload.uf}",
        }


@app.get("/api/prospeccao/oportunidades")
def list_oportunidades_prospeccao(
    request: Request,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    score_min: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Lista oportunidades de prospecção com filtros."""
    _, org_id = _require_authenticated(request)
    from prospecting.engine import list_oportunidades
    return list_oportunidades(
        org_id=org_id,
        cidade=cidade,
        uf=uf,
        status=status,
        prioridade=prioridade,
        score_min=score_min,
        limit=limit,
        offset=offset,
    )


@app.get("/api/prospeccao/oportunidades/{oportunidade_id}")
def get_oportunidade_prospeccao(request: Request, oportunidade_id: str) -> dict:
    """Retorna detalhe de uma oportunidade."""
    return _assert_oportunidade_access(request, oportunidade_id)


@app.post("/api/prospeccao/oportunidades/{oportunidade_id}/webhook")
def reenviar_webhook_oportunidade(request: Request, oportunidade_id: str) -> dict:
    """Reenvia webhook manualmente para o Claw."""
    _assert_oportunidade_access(request, oportunidade_id)
    from prospecting.engine import reenviar_webhook
    return reenviar_webhook(oportunidade_id)


@app.patch("/api/prospeccao/oportunidades/{oportunidade_id}/status")
def patch_status_oportunidade(
    request: Request,
    oportunidade_id: str,
    payload: ProspeccaoStatusPatch,
) -> dict:
    """Atualiza status do pipeline de prospecção."""
    _assert_oportunidade_access(request, oportunidade_id)
    from prospecting.engine import update_status, OportunidadeNotFoundError, WebhookDeliveryError
    try:
        update_status(oportunidade_id, payload.status)
        return {"status": "updated", "id": oportunidade_id, "novo_status": payload.status}
    except OportunidadeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WebhookDeliveryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao atualizar status: {str(e)}")


@app.post("/api/prospeccao/webhook/configure")
def configurar_webhook_claw(request: Request, payload: WebhookConfigureInput) -> dict:
    """Configura URL do webhook do Claw por organização."""
    _require_org_access(request, payload.org_id)
    sb = _supabase_client()
    try:
        sb.table("organizations").update({
            "webhook_claw_url": payload.webhook_url,
        }).eq("id", payload.org_id).execute()
        return {"status": "ok", "org_id": payload.org_id, "webhook_url": payload.webhook_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Tinker Bot Assistente ──────────────────────────────────────────────────

class AssistenteChatInput(BaseModel):
    pergunta: str
    relatorio_id: str | None = None


class AssistenteChatOutput(BaseModel):
    resposta: str


@app.post("/api/assistente/chat", response_model=AssistenteChatOutput)
async def assistente_chat(request: Request, payload: AssistenteChatInput) -> AssistenteChatOutput:
    """Endpoint do GymSite Assistant — responde perguntas usando Tinker SamplingClient.

    Requer autenticação JWT. Opcionalmente aceita um relatorio_id para
    contextualizar a resposta em um relatório específico.
    """
    user_id, _ = _require_authenticated(request)

    # Lazy imports — evita quebra no startup se tinker não estiver instalado
    try:
        from services.tinker_bot import chat_async
        from services.tinker_context import build_contexto_chat
    except ImportError as e:
        logger.error("Tinker SDK não instalado. Rode: uv pip install tinker")
        raise HTTPException(status_code=503, detail="Serviço de assistente indisponível. Tinker SDK não instalado.")

    try:
        contexto = build_contexto_chat(
            user_id=user_id,
            pergunta=payload.pergunta,
            relatorio_id=payload.relatorio_id,
        )
        resposta = await chat_async(
            prompt_text=contexto,
            max_tokens=1024,
            temperature=0.7,
        )
        return AssistenteChatOutput(resposta=resposta)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro no Tinker Bot: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro no assistente: {str(e)}")


# ── Agente de IA Conversacional ────────────────────────────────────────────

class ConversarInput(BaseModel):
    mensagem: str
    session_id: str | None = None


class ConversarOutput(BaseModel):
    session_id: str
    intencao: str
    slots: dict[str, Any]
    slots_faltando: list[str]
    resposta: str
    relatorio_id: str | None = None
    status: str


@app.post("/api/assistente/conversar", response_model=ConversarOutput)
async def assistente_conversar(request: Request, payload: ConversarInput) -> ConversarOutput:
    """Endpoint do Agente de IA Especialista em Fitness — fluxo conversacional.

    Substitui o formulário tradicional por slot-filling via chat natural.
    Quando todos os slots são preenchidos, cria stub e dispara pipeline A0-A9.
    """
    from services.conversational_engine import processar_mensagem
    from services.chat_state import atualizar_sessao

    user_id, org_from_jwt = _require_authenticated(request)

    try:
        resultado = processar_mensagem(
            user_id=user_id,
            mensagem=payload.mensagem,
            session_id=payload.session_id,
        )
    except Exception as e:
        logger.exception("Erro no ConversationalEngine: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro no agente: {str(e)}")

    intencao = resultado.get("intencao", "indefinido")

    # Fallback para chat Q&A (pergunta_simples / status_relatorio)
    if intencao in ("pergunta_simples", "status_relatorio"):
        try:
            from services.tinker_bot import chat_async
            from services.tinker_context import build_contexto_chat
            contexto = build_contexto_chat(
                user_id=user_id,
                pergunta=payload.mensagem,
                relatorio_id=resultado.get("relatorio_id"),
            )
            resposta_qa = await chat_async(prompt_text=contexto, max_tokens=1024, temperature=0.7)
            resultado["resposta"] = resposta_qa
        except Exception:
            logger.warning("Fallback QA falhou para intencao=%s", intencao)
            resultado["resposta"] = (
                "Entendo sua pergunta. Para que eu possa responder com precisão, "
                "poderia confirmar se você está perguntando sobre um relatório específico?"
            )

    # Quando pronto, criar stub e disparar pipeline
    if resultado.get("status") == "pronto_para_pipeline":
        slots = resultado.get("slots", {})
        try:
            rel_input = NovoRelatorioInput(
                cidade=slots.get("cidade", ""),
                uf=slots.get("uf") or None,
                bairro=slots.get("bairro", ""),
                area_m2_min=int(slots.get("area_m2_min", 800)),
                area_m2_max=int(slots.get("area_m2_max", 1500)),
                tamanho_preset=slots.get("tamanho_preset", "m"),
                publico_alvo=slots.get("publico_alvo", "25-40"),
                genero_alvo=slots.get("genero_alvo", "misto"),
                tipo_negocio=slots.get("tipo_negocio", "academia"),
                estacionamento_obrigatorio=bool(slots.get("estacionamento_obrigatorio", True)),
                bairros_indicados=[],
                org_id=org_from_jwt,
                a0_research_provider="auto",
            )
            relatorio_id, _ = create_relatorio_stub(
                rel_input,
                org_id=org_from_jwt,
                user_id=user_id,
            )
            if _queue is None:
                raise RuntimeError("Task queue não inicializado")
            await _queue.enqueue({
                "type": "pipeline",
                "relatorio_id": relatorio_id,
                "payload": rel_input.model_dump(),
            })
            atualizar_sessao(
                resultado["session_id"],
                relatorio_id=relatorio_id,
                status="pipeline_rodando",
            )
            resultado["relatorio_id"] = relatorio_id
            resultado["status"] = "pipeline_rodando"
        except Exception as e:
            logger.exception("Erro ao criar relatório do chat: %s", e)
            raise HTTPException(status_code=500, detail=f"Erro ao iniciar relatório: {str(e)}")

    return ConversarOutput(
        session_id=resultado["session_id"],
        intencao=resultado["intencao"],
        slots=resultado.get("slots", {}),
        slots_faltando=resultado.get("slots_faltando", []),
        resposta=resultado.get("resposta", ""),
        relatorio_id=resultado.get("relatorio_id"),
        status=resultado.get("status", "coletando_slots"),
    )


# Preflight catch-all — garante 204 mesmo se o router não capturar
@app.options("/{path:path}")
async def preflight_catchall(path: str) -> None:
    return None

