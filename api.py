"""
api.py — FastAPI server pro GymSite Intelligence.

Endpoints:
- POST /api/relatorios            cria stub + dispara pipeline em background
- GET  /api/relatorios            lista (suporta filtros)
- GET  /api/relatorios/{id}       detail completo (joins de todas as 9 tabelas)
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
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)
load_dotenv(_ROOT / "gymsite_intelligence" / ".env", override=False)

logger = logging.getLogger("gymsite.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

from tools.google_maps_key import warn_if_missing_maps_key

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
    from supabase import create_client
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
        if res.data:
            return res.data["id"]
    return relatorio_id


app = FastAPI(title="GymSite Intelligence API", version="1.0.0")

# CORS: dev libera localhost:* via regex; producao vem de CORS_ORIGINS (.env),
# comma-separated. Ex: CORS_ORIGINS=https://vectracargo.com.br,https://gymsite.vectracargo.com.br
_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]
if _cors_origins:
    logger.info("CORS origins from env: %s", _cors_origins)
else:
    logger.warning(
        "CORS_ORIGINS nao definida em .env — somente localhost:* via regex liberado"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    from tools.research_provider import set_a0_research_provider
    from tools.token_telemetry import reset_run_id, _get_run_id

    from tools.api_cost_tracker import current_relatorio_id
    token = current_relatorio_id.set(relatorio_id)
    try:
        set_a0_research_provider(payload.a0_research_provider or "auto")

        # Reset run_id pra cada tentativa — telemetria fica separada por tentativa.
        reset_run_id()

        session_service = InMemorySessionService()
        session_id = f"api_{relatorio_id}_{int(time.time())}"
        user_id = "api_user"

        await session_service.create_session(
            app_name="gymsite",
            user_id=user_id,
            session_id=session_id,
            state={
                "relatorio_id": relatorio_id,
                # Params estruturados acessíveis via tool_context.state em qualquer
                # tool — usado por A1 GeoScout (listings OLX+ImovelWeb filtra por
                # area_min/max) e potencialmente A4 (estacionamento, tipo_negocio).
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
            },
        )

        runner = Runner(
            agent=root_agent,
            app_name="gymsite",
            session_service=session_service,
        )

        prompt = _build_pipeline_prompt(payload)
        message = Content(role="user", parts=[Part(text=prompt)])

        async for _event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            pass

        run_id = _get_run_id()
        sb = _supabase_client()
        return _agregar_e_persistir_custos(sb, relatorio_id, run_id)
    finally:
        current_relatorio_id.reset(token)


async def _run_pipeline_async(relatorio_id: str, payload: NovoRelatorioInput) -> None:
    """Roda o pipeline GymSite em background com retry em 429.

    Quando Vertex AI retorna 429 RESOURCE_EXHAUSTED (quota minute-rate
    estourada — frequente em bairros densos como Itaipu/Niterói), tentamos
    de novo após 30s/60s/120s. Pipeline raramente falha por quota.
    Limitação: o pipeline re-roda do início — custo dobra na pior hipótese.
    """
    sb = _supabase_client()
    t0 = time.time()
    custos: dict = {}
    last_exc: BaseException | None = None

    try:
        sb.table("relatorios").update({"status": "running"}).eq("id", relatorio_id).execute()

        for tentativa, backoff in enumerate([0] + _RETRY_BACKOFFS_429):
            if backoff > 0:
                logger.warning(
                    f"pipeline {relatorio_id} hit 429 — retry {tentativa}/{len(_RETRY_BACKOFFS_429)} "
                    f"em {backoff}s"
                )
                await asyncio.sleep(backoff)
            try:
                custos = await _executar_pipeline_uma_vez(relatorio_id, payload)
                last_exc = None
                break  # sucesso
            except BaseException as e:
                if _is_429_error(e):
                    last_exc = e
                    continue  # tenta de novo após backoff
                raise  # outros erros não fazem retry

        if last_exc is not None:
            # Esgotou todas as tentativas, continua sendo 429
            raise last_exc

        elapsed = int(time.time() - t0)
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

    except BaseException as e:
        logger.error(f"pipeline {relatorio_id} falhou: {e}\n{traceback.format_exc()}")
        erro_amigavel = (
            "Pico de uso da Vertex AI — tente de novo em alguns minutos"
            if _is_429_error(e)
            else f"{type(e).__name__}: {e}"
        )
        try:
            sb.table("relatorios").update({
                "status": "failed",
                "erro_mensagem": erro_amigavel[:500],
            }).eq("id", relatorio_id).execute()
        except Exception:
            pass


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
def health() -> dict:
    return {"status": "ok", "service": "gymsite-intelligence-api"}


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
    background_tasks: BackgroundTasks,
    request: Request,
) -> RelatorioStub:
    """Cria stub do relatório + dispara pipeline em background. Retorna ID pra polling."""
    user_id, org_from_jwt = _resolve_user_and_org(request)
    try:
        relatorio_id, created_at = create_relatorio_stub(
            payload,
            org_id=payload.org_id or org_from_jwt,
            user_id=user_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    background_tasks.add_task(_run_pipeline_async_wrapper, relatorio_id, payload)

    return RelatorioStub(
        id=relatorio_id,
        status="queued",
        created_at=created_at,
    )


def _run_pipeline_async_wrapper(relatorio_id: str, payload: NovoRelatorioInput) -> None:
    """BackgroundTasks só aceita callables sync — wrapeia o async."""
    asyncio.run(_run_pipeline_async(relatorio_id, payload))


@app.get("/api/relatorios/{relatorio_id}/status")
def get_status(relatorio_id: str) -> dict:
    """Polling leve. Retorna só status + erro se falhou."""
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    res = sb.table("relatorios").select(
        "id, status, erro_mensagem, tempo_execucao_segundos, data_execucao"
    ).eq("id", rid).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="relatório não encontrado")
    return res.data


def _fetch_relatorio_payload(sb: Any, rid: str) -> dict:
    """Detail completo: joins de todas as tabelas filhas."""
    header = sb.table("relatorios").select("*").eq("id", rid).single().execute()
    if not header.data:
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


@app.get("/api/relatorios/{relatorio_id}/custos-api")
def get_relatorio_custos_api(relatorio_id: str) -> dict:
    """Breakdown de custos LLM + APIs externas (Places, SearchAPI, Geocoding)."""
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    
    # 1. Busca custos LLM
    llm_res = sb.table("relatorio_custos_agentes").select("*").eq("relatorio_id", rid).execute()
    llm_records = llm_res.data or []
    
    llm_total = sum(float(r.get("custo_brl") or 0.0) for r in llm_records)
    llm_por_agente = {}
    for r in llm_records:
        agente = r.get("agente")
        if agente:
            llm_por_agente[agente] = {
                "tokens_in": r.get("tokens_in", 0),
                "tokens_out": r.get("tokens_out", 0),
                "custo_brl": float(r.get("custo_brl") or 0.0),
                "modelo": r.get("modelo") or "",
            }
            
    # 2. Busca custos API
    # Usando try-except em caso de migração de banco pendente (fail-safe)
    api_records = []
    try:
        api_res = sb.table("relatorio_api_calls").select("*").eq("relatorio_id", rid).execute()
        api_records = api_res.data or []
    except Exception:
        pass
    
    api_total = sum(float(r.get("custo_brl") or 0.0) for r in api_records)
    api_por_sku = {}
    for r in api_records:
        sku = r.get("api_sku")
        if sku:
            slot = api_por_sku.setdefault(sku, {"calls": 0, "custo_brl": 0.0})
            slot["calls"] += r.get("num_calls", 1)
            slot["custo_brl"] = round(slot["custo_brl"] + float(r.get("custo_brl") or 0.0), 6)
            
    return {
        "llm": {
            "total_brl": round(llm_total, 4),
            "por_agente": llm_por_agente,
        },
        "api": {
            "total_brl": round(api_total, 4),
            "por_sku": api_por_sku,
        },
        "total_brl": round(llm_total + api_total, 4),
    }


@app.get("/api/relatorios/{relatorio_id}")
def get_relatorio(relatorio_id: str) -> dict:
    """Detail completo: joins de todas as tabelas filhas."""
    sb = _supabase_client()
    rid = _resolve_relatorio_uuid(sb, relatorio_id)
    return _fetch_relatorio_payload(sb, rid)


class EntranteValidacaoInput(BaseModel):
    cnpj: str = Field(..., min_length=11, max_length=18)
    validado: bool = True


@app.patch("/api/relatorios/{relatorio_id}/entrantes-cnpj/validacao")
def patch_entrante_validacao(relatorio_id: str, body: EntranteValidacaoInput) -> dict:
    """Marca contato do entrant como validado manualmente (persiste em entrantes_cnpj_90d)."""
    import re
    from datetime import datetime, timezone

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
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}.pdf"',
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
def executar_prospeccao(
    payload: ProspeccaoExecutarInput,
    background_tasks: BackgroundTasks,
) -> dict:
    """Dispara engine de cruzamento CNPJ × CNO em background."""
    def _run():
        from prospecting.engine import run_prospeccao
        return run_prospeccao(
            cidade=payload.cidade,
            uf=payload.uf,
            dias=payload.dias,
            limit=payload.limit,
            org_id=payload.org_id,
            webhook_url=payload.webhook_url,
        )

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "message": f"Prospecção iniciada para {payload.cidade}/{payload.uf}",
    }


@app.get("/api/prospeccao/oportunidades")
def list_oportunidades_prospeccao(
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    score_min: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Lista oportunidades de prospecção com filtros."""
    from prospecting.engine import list_oportunidades
    return list_oportunidades(
        cidade=cidade,
        uf=uf,
        status=status,
        prioridade=prioridade,
        score_min=score_min,
        limit=limit,
        offset=offset,
    )


@app.get("/api/prospeccao/oportunidades/{oportunidade_id}")
def get_oportunidade_prospeccao(oportunidade_id: str) -> dict:
    """Retorna detalhe de uma oportunidade."""
    from prospecting.engine import get_oportunidade
    opp = get_oportunidade(oportunidade_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
    return opp


@app.post("/api/prospeccao/oportunidades/{oportunidade_id}/webhook")
def reenviar_webhook_oportunidade(oportunidade_id: str) -> dict:
    """Reenvia webhook manualmente para o Claw."""
    from prospecting.engine import reenviar_webhook
    return reenviar_webhook(oportunidade_id)


@app.patch("/api/prospeccao/oportunidades/{oportunidade_id}/status")
def patch_status_oportunidade(
    oportunidade_id: str,
    payload: ProspeccaoStatusPatch,
) -> dict:
    """Atualiza status do pipeline de prospecção."""
    from prospecting.engine import update_status
    ok = update_status(oportunidade_id, payload.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
    return {"status": "updated", "id": oportunidade_id, "novo_status": payload.status}


@app.post("/api/prospeccao/webhook/configure")
def configurar_webhook_claw(payload: WebhookConfigureInput) -> dict:
    """Configura URL do webhook do Claw por organização."""
    sb = _supabase_client()
    try:
        sb.table("organizations").update({
            "webhook_claw_url": payload.webhook_url,
        }).eq("id", payload.org_id).execute()
        return {"status": "ok", "org_id": payload.org_id, "webhook_url": payload.webhook_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
