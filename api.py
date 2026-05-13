"""
api.py — FastAPI server pro GymSite Intelligence.

Endpoints:
- POST /api/relatorios            cria stub + dispara pipeline em background
- GET  /api/relatorios            lista (suporta filtros)
- GET  /api/relatorios/{id}       detail completo (joins de todas as 9 tabelas)
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
    MAPS_API_KEY
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger("gymsite.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

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


app = FastAPI(title="GymSite Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Vite dev pode escolher qualquer porta — em dev, libera localhost:* via regex
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


class RelatorioStub(BaseModel):
    id: str
    status: str
    created_at: Optional[str] = None


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
    from tools.token_telemetry import reset_run_id, _get_run_id

    # Reset run_id pra cada tentativa — telemetria fica separada por tentativa.
    reset_run_id()

    session_service = InMemorySessionService()
    session_id = f"api_{relatorio_id}_{int(time.time())}"
    user_id = "api_user"

    await session_service.create_session(
        app_name="gymsite",
        user_id=user_id,
        session_id=session_id,
        state={"relatorio_id": relatorio_id},
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


@app.post("/api/relatorios", response_model=RelatorioStub)
async def create_relatorio(
    payload: NovoRelatorioInput,
    background_tasks: BackgroundTasks,
) -> RelatorioStub:
    """Cria stub do relatório + dispara pipeline em background. Retorna ID pra polling."""
    sb = _supabase_client()
    org_id = payload.org_id or os.getenv("SUPABASE_GYMSITE_ORG_ID") or _DEFAULT_ORG_ID

    # 1. Header: status='queued' (FK satisfeito pra child inserts depois)
    res = sb.table("relatorios").insert({
        "org_id": org_id,
        "user_id": None,
        "tipo_relatorio": "prospeccao_academia",
        "status": "queued",
        "schema_version": "1.6",
    }).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="falha ao criar header")
    relatorio_id = res.data[0]["id"]

    # 2. Inputs (pra que listagens já consigam exibir cidade/bairro mesmo antes
    #    do pipeline rodar)
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
    }).execute()

    # 3. Dispara pipeline async
    background_tasks.add_task(_run_pipeline_async_wrapper, relatorio_id, payload)

    return RelatorioStub(
        id=relatorio_id,
        status="queued",
        created_at=res.data[0].get("created_at"),
    )


def _run_pipeline_async_wrapper(relatorio_id: str, payload: NovoRelatorioInput) -> None:
    """BackgroundTasks só aceita callables sync — wrapeia o async."""
    asyncio.run(_run_pipeline_async(relatorio_id, payload))


@app.get("/api/relatorios/{relatorio_id}/status")
def get_status(relatorio_id: str) -> dict:
    """Polling leve. Retorna só status + erro se falhou."""
    sb = _supabase_client()
    res = sb.table("relatorios").select(
        "id, status, erro_mensagem, tempo_execucao_segundos, data_execucao"
    ).eq("id", relatorio_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="relatório não encontrado")
    return res.data


@app.get("/api/relatorios/{relatorio_id}")
def get_relatorio(relatorio_id: str) -> dict:
    """Detail completo: joins de todas as tabelas filhas."""
    sb = _supabase_client()

    header = sb.table("relatorios").select("*").eq("id", relatorio_id).single().execute()
    if not header.data:
        raise HTTPException(status_code=404, detail="relatório não encontrado")

    inputs = sb.table("relatorio_inputs").select("*").eq("relatorio_id", relatorio_id).maybe_single().execute()
    outputs = sb.table("relatorio_outputs").select("*").eq("relatorio_id", relatorio_id).maybe_single().execute()
    candidatos = sb.table("candidatos").select("*").eq("relatorio_id", relatorio_id).order("posicao").execute()
    competidores = sb.table("competidores").select("*").eq("relatorio_id", relatorio_id).execute()
    cenarios = sb.table("cenarios_financeiros").select("*").eq("relatorio_id", relatorio_id).execute()
    sensibilidade = sb.table("sensibilidade_cenarios").select("*").eq("relatorio_id", relatorio_id).execute()
    bairros_alt = sb.table("bairros_alternativos").select("*").eq("relatorio_id", relatorio_id).order("ordem").execute()

    return {
        "id": relatorio_id,
        "header": header.data,
        "input_canonico": inputs.data if inputs else None,
        "output_consolidado": outputs.data if outputs else None,
        "candidatos": candidatos.data or [],
        "competidores": competidores.data or [],
        "cenarios": cenarios.data or [],
        "sensibilidade": sensibilidade.data or [],
        "bairros_alternativos": bairros_alt.data or [],
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
