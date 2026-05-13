"""
offer_mapper_tool.py — macro-tool consumida pelo agente A3c CompetitorMapper.

Lê `inteligencia_competitiva.concorrentes_detalhados` do tool_context.state
(output_key do A3b), roda `competitor_offer_mapper.mapear_oferta_concorrente`
em paralelo para cada concorrente com `website`/`instagram`, e retorna o
mapeamento bruto pronto pro LLM A3c normalizar.

Por que macro-tool sem argumentos (igual A3b):
- Tools que recebem `concorrentes_detalhados` como argumento estouram
  MALFORMED_FUNCTION_CALL (payload grande no function_call).
- Lendo do state, o function_call vira `mapear_oferta_competidores_completo()`
  puro — impossível ser malformed.

Async-safe pra ADK: roda `asyncio.run()` em ThreadPoolExecutor pra isolar
do event loop do runtime ADK (que é SelectorEventLoop no Windows).
"""
import asyncio
import concurrent.futures
import json
import logging
import os
from typing import Any

from tools.competitor_offer_mapper import mapear_oferta_concorrente

logger = logging.getLogger(__name__)

MAX_CONCURRENT_FETCHES = 5
CONFIABILIDADE_MIN_SUCESSO = 0.30

# Limite de academias mapeadas por relatório. A3b entrega ~10 concorrentes;
# pegamos os primeiros N que TÊM website ou Instagram (ordem do A3b é
# preservada pra manter o ranking de relevância). Override via env var
# A3C_MAX_COMPETIDORES sem precisar deploy.
DEFAULT_MAX_COMPETIDORES = 5


def _max_competidores() -> int:
    raw = os.environ.get("A3C_MAX_COMPETIDORES", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_MAX_COMPETIDORES


def _run_async_in_thread(coro):
    """Executa coroutine em thread separada via asyncio.run() (isola loop ADK)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(coro)).result()


async def _mapear_lote_async(concorrentes: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

    async def _one(c: dict) -> dict:
        async with sem:
            return await mapear_oferta_concorrente(
                nome=c.get("nome", "?"),
                website=c.get("website") or None,
                instagram_handle=c.get("instagram") or c.get("instagram_handle"),
                place_id=c.get("place_id"),
            )

    return await asyncio.gather(*(_one(c) for c in concorrentes))


def _parse_state_intel(intel: Any) -> dict:
    """
    A3b output pode vir em 3 formas:
    - dict direto: {"concorrentes_detalhados": [...]}
    - dict com wrapper: {"inteligencia_competitiva": {"concorrentes_detalhados": [...]}}
    - string JSON com fence: ```json\\n{"inteligencia_competitiva": {...}}\\n```

    Sempre retorna o dict DESEMPACOTADO contendo `concorrentes_detalhados`
    no topo (ou {} se não conseguir parsear).
    """
    parsed: Any
    if isinstance(intel, dict):
        parsed = intel
    elif isinstance(intel, str):
        txt = intel.strip()
        if txt.startswith("```"):
            lines = txt.split("\n")
            txt = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
        try:
            parsed = json.loads(txt)
        except Exception:
            return {}
    else:
        return {}

    # Desempacota wrapper duplicado se A3b emitiu envelope com o próprio nome do output_key
    if isinstance(parsed, dict) and "inteligencia_competitiva" in parsed and isinstance(parsed["inteligencia_competitiva"], dict):
        return parsed["inteligencia_competitiva"]
    return parsed if isinstance(parsed, dict) else {}


def _chave_concorrente(c: dict, idx: int) -> str:
    return c.get("place_id") or c.get("nome") or f"idx_{idx}"


def mapear_oferta_competidores_completo(tool_context) -> dict:
    """
    Macro-tool do A3c CompetitorMapper.

    Lê `inteligencia_competitiva.concorrentes_detalhados` direto do
    `tool_context.state` (output_key do A3b) e dispara fetch paralelo
    (até 5 simultâneos) de site oficial + Instagram público pra cada
    concorrente com website ou handle.

    Returns:
        dict com:
        - mapeamento_oferta: {<chave>: OfertaMapeada.asdict()}
        - total_processados: int
        - sucessos: int (confiabilidade_fonte >= 0.30)
        - taxa_sucesso: float
        - aviso: string (opcional)
    """
    state = getattr(tool_context, "state", None)
    if state is None:
        return {"erro": "tool_context.state indisponível", "mapeamento_oferta": {}}

    intel = _parse_state_intel(state.get("inteligencia_competitiva"))
    if not intel:
        # Fallback: A3a também emite concorrentes_brutos com website em alguns casos
        brutos = state.get("concorrentes_brutos")
        if isinstance(brutos, list):
            concorrentes = brutos
        else:
            concorrentes = []
    else:
        concorrentes = intel.get("concorrentes_detalhados", [])
        if not isinstance(concorrentes, list):
            concorrentes = []

    # Filtra os que TÊM website ou IG (ordem do A3b preservada = ranking
    # de relevância) e limita a MAX_COMPETIDORES pra controlar latência e
    # custo de API externa (Outscraper).
    todos_elegiveis = [
        c for c in concorrentes
        if isinstance(c, dict) and (c.get("website") or c.get("instagram") or c.get("instagram_handle"))
    ]
    limite = _max_competidores()
    elegiveis = todos_elegiveis[:limite]
    ignorados_por_limite = len(todos_elegiveis) - len(elegiveis)

    if not elegiveis:
        return {
            "mapeamento_oferta": {},
            "total_processados": len(concorrentes),
            "sucessos": 0,
            "taxa_sucesso": 0.0,
            "aviso": "nenhum concorrente com website ou instagram_handle",
        }

    try:
        resultados = _run_async_in_thread(_mapear_lote_async(elegiveis))
    except Exception as exc:
        logger.exception("offer_mapper falhou no lote")
        return {
            "mapeamento_oferta": {},
            "total_processados": len(elegiveis),
            "sucessos": 0,
            "taxa_sucesso": 0.0,
            "erro": f"lote_falhou:{type(exc).__name__}:{exc}",
        }

    mapeamento: dict[str, dict] = {}
    sucessos = 0
    for idx, (c, r) in enumerate(zip(elegiveis, resultados)):
        chave = _chave_concorrente(c, idx)
        mapeamento[chave] = r
        if r.get("confiabilidade_fonte", 0) >= CONFIABILIDADE_MIN_SUCESSO:
            sucessos += 1

    total = len(elegiveis)
    resultado = {
        "mapeamento_oferta": mapeamento,
        "total_processados": total,
        "sucessos": sucessos,
        "taxa_sucesso": round(sucessos / total, 2) if total else 0.0,
        "ignorados_sem_fonte": len(concorrentes) - len(todos_elegiveis),
        "ignorados_por_limite_top_n": ignorados_por_limite,
        "limite_aplicado": limite,
    }

    # Persistência defensiva no state: se LLM falhar em emitir output_key
    # (bug Flash observado em runs c05c9059/bdab58e1/d5cb8f29), normalizamos
    # `mapeamento_oferta` em formato canônico AQUI e setamos `oferta_concorrentes`
    # direto. LLM ainda tem chance de sobrescrever no turno seguinte com versão
    # melhorada, mas o piso mínimo está garantido.
    try:
        normalizado = {}
        for chave, raw in mapeamento.items():
            if not isinstance(raw, dict):
                continue
            conf = float(raw.get("confiabilidade_fonte") or 0)
            conf_label = "alta" if conf >= 0.7 else ("media" if conf >= 0.4 else "baixa")
            mensais = []
            for p in (raw.get("precos_encontrados") or []):
                periodo = (p.get("periodo") or "").lower()
                if "mes" in periodo or "mensal" in periodo:
                    try:
                        mensais.append(float(p.get("valor_brl")))
                    except (TypeError, ValueError):
                        pass
            faixa = {"plano_mensal_min": min(mensais), "plano_mensal_max": max(mensais)} if mensais else None
            fontes = []
            if raw.get("fonte_url_ok"):       fontes.append("website")
            if raw.get("fonte_instagram_ok"): fontes.append("instagram")
            normalizado[chave] = {
                "nome": raw.get("nome"),
                "modalidades": raw.get("modalidades_keywords") or [],
                "diferenciais": raw.get("diferenciais_keywords") or [],
                "faixa_preco_brl": faixa,
                "fontes": fontes,
                "confiabilidade_oferta": conf_label,
                "observacoes": "" if conf > 0 else "sem evidência",
                "_persistido_pela_macro": True,
            }
        state["oferta_concorrentes"] = {
            "oferta_concorrentes": normalizado,
            "total_processados": total,
            "sucessos": sucessos,
            "taxa_sucesso": resultado["taxa_sucesso"],
        }
    except Exception as exc:
        logger.exception("offer_mapper falhou ao popular state defensivo")

    return resultado
