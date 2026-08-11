# agents/a0_context_builder.py
"""
A0: Context Builder — primeiro agente do pipeline.

Act-on A0 bundle-only (2026-07-16): Deep Research / Kimi FORA das tools.
Qualitativo = market_bundle; quantitativo = CNPJ/CNO + fatos_competicao_local.
Sem interpretação além dos dados retornados pelas tools.

Slim-down (2026-08-11): tool responses enviadas ao LLM são slim; o state guarda
snapshot completo em `a0_tool_snapshots` e o after_agent re-hidrata CNPJ/CNO.
"""
from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any

from google.adk.models.llm_response import LlmResponse
from google.genai import types
from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0
from tools.context_slimmer import slim_market_context_for_prompt
from tools.local_market_facts import fatos_competicao_local
from tools.market_bundle import carregar_market_bundle

logger = logging.getLogger("gymsite.a0")

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=1024),
)

# NVIDIA 131k: Parangaba estourou em loop A0 (~30 turns). Cap defensivo.
MAX_A0_LLM_CALLS = 12
MAX_A0_REPEATED_TOOL = 3

# Literais de REFERÊNCIA do schema no prompt (## SAÍDA). Sem market_bundle, o LLM às
# vezes ecoa o esqueleto verbatim em vez de escrever "dados_nao_disponiveis"
# (§DEGRADAÇÃO). Bug Pirapora: "crescimento|estavel|retracao" e "fato+fonte N"
# vazaram até o PDF do cliente. Guardrail determinístico, mesmo espírito do override
# CNPJ: texto exibido não nasce da boca do LLM.
_ESQUELETO_TENDENCIA = "crescimento|estavel|retracao"
_ESQUELETO_DATA_COLETA = "YYYY-MM-DD"
_ESQUELETO_INSIGHT_RE = re.compile(r"^\s*fato\+fonte\s*\d*\s*$", re.IGNORECASE)


def _sanear_esqueleto_a0(inner: dict) -> bool:
    """Troca literais do schema por vazio/dados_nao_disponiveis. Retorna True se mudou.

    Só casa o literal EXATO do esqueleto — nunca um valor real ('estavel', um insight
    com fonte). Não inventa dado: o oposto, remove o placeholder que fingia ser dado.
    """
    mudou = False
    if str(inner.get("tendencia_mercado") or "").strip() == _ESQUELETO_TENDENCIA:
        inner["tendencia_mercado"] = "dados_nao_disponiveis"
        mudou = True
    if str(inner.get("data_coleta") or "").strip() == _ESQUELETO_DATA_COLETA:
        inner["data_coleta"] = ""
        mudou = True
    ins = inner.get("insights_estrategicos")
    if isinstance(ins, list):
        limpos = [i for i in ins if not _ESQUELETO_INSIGHT_RE.match(str(i))]
        if len(limpos) != len(ins):
            inner["insights_estrategicos"] = limpos
            mudou = True
    return mudou


def _garantir_locais_a0(inner: dict, ip: dict) -> bool:
    """P115: repor cidade/bairro/uf do input se o consolidado omitiu (envelope parcial).

    Visível: `a0_envelope_rehidratado_de_input` quando veio do input; `a0_envelope_incompleto`
    + `a0_envelope_faltantes` se ainda faltar após a tentativa (não inventa além do input).
    """
    mudou = False
    rehidratados: list[str] = []
    for k in ("cidade", "bairro", "uf"):
        atual = str(inner.get(k) or "").strip()
        fonte = str((ip or {}).get(k) or "").strip()
        if not atual and fonte:
            inner[k] = fonte
            rehidratados.append(k)
            mudou = True
    faltantes = [k for k in ("cidade", "bairro", "uf") if not str(inner.get(k) or "").strip()]
    if rehidratados:
        inner["a0_envelope_rehidratado_de_input"] = True
        inner["a0_envelope_campos_rehidratados"] = rehidratados
        mudou = True
    if faltantes:
        inner["a0_envelope_incompleto"] = True
        inner["a0_envelope_faltantes"] = faltantes
        mudou = True
    elif inner.pop("a0_envelope_incompleto", None) is not None:
        inner.pop("a0_envelope_faltantes", None)
        mudou = True
    return mudou


def _a0_override_cnpj_numeros(callback_context):
    """Override DETERMINÍSTICO dos números CNPJ no market_context.

    A0 é LlmAgent (consolida bundle + tools), mas o LLM NÃO pode produzir
    número — a instrução manda "Copiar metricas_objetivas", e copiar via LLM arrisca
    transcrição errada/arredondamento sem guardrail. Este callback RE-RODA a tool
    determinística `dados_parque_cnpj_para_a0` e sobrescreve os campos numéricos do CNPJ
    + pluga `arvore_2x2_parque` (que o schema de saída do LLM dropava). Número = sempre da
    tool (banco), nunca da boca do LLM. Mesmo padrão do override do A9. Campos
    qualitativos vêm do market_bundle (não de DR).

    Best-effort: nunca derruba. _attach_telemetry encadeia ANTES do otel/state_dump.
    """
    try:
        from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0
        from tools.competitor_tools import _parse_market_context

        st = callback_context.state
        mc = _parse_market_context(st.get("market_context"))
        tem_envelope = isinstance(mc.get("market_context"), dict)
        inner = mc.get("market_context") if tem_envelope else mc
        if not isinstance(inner, dict):
            return None

        # Saneamento do esqueleto: roda ANTES e INDEPENDENTE do CNPJ — é o caminho do
        # Pirapora (bundle ausente). Persiste mesmo se a tool CNPJ falhar depois.
        mudou = _sanear_esqueleto_a0(inner)

        ip = st.get("input_params") if isinstance(st.get("input_params"), dict) else {}
        # P115: envelope sem cidade/bairro/uf (Parangaba NVIDIA) quebra A2/A9 em silêncio.
        if _garantir_locais_a0(inner, ip):
            mudou = True
            if inner.get("a0_envelope_incompleto"):
                st["a0_envelope_incompleto"] = True
                st["a0_envelope_faltantes"] = list(inner.get("a0_envelope_faltantes") or [])

        cidade = (ip.get("cidade") or inner.get("cidade") or "").strip()
        uf = (ip.get("uf") or inner.get("uf") or "").strip()
        bairro = (ip.get("bairro") or inner.get("bairro") or "").strip()

        if cidade:
            snaps = st.get("a0_tool_snapshots") if isinstance(st.get("a0_tool_snapshots"), dict) else {}
            snap = snaps.get("dados_parque_cnpj_para_a0")
            if isinstance(snap, dict) and snap.get("status") == "ok":
                tool = snap
            else:
                tool = dados_parque_cnpj_para_a0(cidade, uf, dias=90, bairro=bairro)
            if isinstance(tool, dict) and tool.get("status") == "ok":
                m = tool.get("metricas_objetivas") or {}
                ind = tool.get("indicadores_derivados") or {}

                inner["parque_ativo_total"] = m.get("parque_ativo_total")
                inner["parque_comercial_total"] = m.get("parque_comercial_total")
                inner["academias_ativas_cidade_cnpj"] = m.get("parque_ativo_total")
                inner["novos_cnpj_fitness_90d"] = m.get("novos_cnpj_fitness_90d")
                inner["excluidos_saude_clinica"] = m.get("excluidos_saude_clinica")
                inner["pendentes_validacao"] = m.get("pendentes_validacao")
                inner["composicao_parque"] = m.get("composicao_parque") or {}
                inner["novas_unidades_90d_por_segmento"] = m.get("novas_unidades_90d_por_segmento") or {}
                inner["serie_aberturas_anual"] = m.get("serie_aberturas_anual") or {}
                inner["arvore_2x2_parque"] = tool.get("arvore_2x2_parque")  # plug: o LLM dropava
                inner["arvore_oferta"] = tool.get("arvore_oferta")
                inner["redes"] = tool.get("redes")
                inner["baixas_cnpj_fitness_90d"] = m.get("baixas_cnpj_fitness_90d")
                inner["baixas_cnpj_fitness_q"] = m.get("baixas_cnpj_fitness_q")
                inner["entrantes_cnpj_fitness_q"] = m.get("entrantes_cnpj_fitness_q")
                inner["saldo_oferta_q"] = m.get("saldo_oferta_q")
                inner["pressao_oferta_q"] = m.get("pressao_oferta_q")
                inner["janela_q_label"] = m.get("janela_q_label")
                inner["cnpj_as_of"] = m.get("as_of")
                inner["fatos_parque_cnpj"] = {
                    "fonte": "RFB CNPJ Aberto",
                    "metricas": m,
                    "indicadores_derivados": ind,
                    "cruzamento_cno": tool.get("cruzamento_cno") or {},
                    "lacunas": tool.get("lacunas_conhecidas") or [],
                }
                inner["_cnpj_override"] = "deterministico_tool"
                mudou = True

        if mudou:
            if tem_envelope:
                mc["market_context"] = inner
                st["market_context"] = mc
            else:
                st["market_context"] = inner
    except Exception:
        pass
    return None


def _tool_name(tool: Any) -> str:
    return (
        getattr(tool, "name", None)
        or getattr(tool, "__name__", None)
        or type(tool).__name__
    )


def _loc_from_state(state: Any) -> dict[str, str]:
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    mc = state.get("market_context")
    inner = {}
    if isinstance(mc, dict):
        inner = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
    if not isinstance(inner, dict):
        inner = {}
    return {
        "cidade": (ip.get("cidade") or inner.get("cidade") or "").strip(),
        "bairro": (ip.get("bairro") or inner.get("bairro") or "").strip(),
        "uf": (ip.get("uf") or inner.get("uf") or "").strip(),
        "genero_alvo": str(ip.get("genero_alvo") or inner.get("genero_alvo") or "misto"),
        "tipo_negocio": str(ip.get("tipo_negocio") or inner.get("tipo_negocio") or "academia"),
        "tamanho_preset": str(ip.get("tamanho_preset") or inner.get("tamanho_preset") or "m"),
    }


def _build_minimal_market_context(state: Any, motivo: str) -> dict:
    loc = _loc_from_state(state)
    return {
        "market_context": {
            **loc,
            "ticket_medio_mercado": "dados_nao_disponiveis",
            "aluguel_medio_m2": "dados_nao_disponiveis",
            "renda_media_bairro": "dados_nao_disponiveis",
            "faixa_etaria_predominante": "dados_nao_disponiveis",
            "principais_redes_concorrentes": [],
            "tendencia_mercado": "dados_nao_disponiveis",
            "regulamentacao_resumo": "dados_nao_disponiveis",
            "insights_estrategicos": [
                f"A0 degradado ({motivo}) — números CNPJ serão preenchidos deterministicamente."
            ],
            "fonte": "a0_fail_soft",
            "a0_degraded": True,
            "a0_degradation_motivo": motivo,
            "briefing_completo_md": "",
        }
    }


def _a0_failsoft_llm_response(state: Any, motivo: str) -> LlmResponse:
    try:
        state["a0_degraded"] = True
        state["a0_degradation_motivo"] = motivo
    except Exception:
        pass
    payload = _build_minimal_market_context(state, motivo)
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=json.dumps(payload, ensure_ascii=False))],
        ),
        turn_complete=True,
        custom_metadata={"a0_degraded": True, "motivo": motivo},
    )


def _a0_after_tool_slim(tool, args, tool_context, tool_response):
    """Persiste tool response COMPLETA no state; devolve versão slim ao LLM."""
    try:
        name = _tool_name(tool)
        st = tool_context.state
        hist = list(st.get("_a0_tool_call_history") or [])
        hist.append(name)
        st["_a0_tool_call_history"] = hist[-30:]

        if not isinstance(tool_response, dict):
            return None

        snaps = st.get("a0_tool_snapshots")
        if not isinstance(snaps, dict):
            snaps = {}
        # Snapshot before slim — state keeps full payload for after_agent / A4-A6.
        snaps[name] = deepcopy(tool_response) if isinstance(tool_response, dict) else tool_response
        st["a0_tool_snapshots"] = snaps

        slim = slim_market_context_for_prompt(tool_response)
        slim["_slim_for_prompt"] = True
        slim["_tool"] = name
        return slim
    except Exception:
        logger.warning("A0 after_tool slim falhou — LLM recebe payload original", exc_info=True)
        return None


def _a0_before_model_callback(callback_context, llm_request):
    """Loop detection: aborta com fail-soft se A0 girar demais ou repetir tool."""
    try:
        st = callback_context.state
        n = int(st.get("_a0_llm_calls") or 0) + 1
        st["_a0_llm_calls"] = n

        if n > MAX_A0_LLM_CALLS:
            motivo = f"a0_max_llm_calls:{n}"
            logger.error("A0 loop/cap: %s — degradando", motivo)
            return _a0_failsoft_llm_response(st, motivo)

        hist = list(st.get("_a0_tool_call_history") or [])
        if len(hist) >= MAX_A0_REPEATED_TOOL:
            last = hist[-MAX_A0_REPEATED_TOOL:]
            if len(set(last)) == 1:
                motivo = f"a0_repeated_tool:{last[0]}"
                logger.error("A0 loop tool: %s — degradando", motivo)
                return _a0_failsoft_llm_response(st, motivo)
    except Exception:
        logger.warning("A0 before_model loop guard falhou", exc_info=True)
    return None


def _a0_on_model_error_callback(callback_context, llm_request, error):
    """Fail-soft em estouro de contexto (NVIDIA 131k) e erros irrecuperáveis."""
    msg = str(error or "").lower()
    is_overflow = any(
        kw in msg
        for kw in (
            "context",
            "token",
            "length",
            "overflow",
            "exceeded",
            "131072",
            "max_tokens",
            "maximum context",
        )
    )
    if not is_overflow:
        return None
    st = getattr(callback_context, "state", {}) or {}
    motivo = f"context_overflow:{type(error).__name__}"
    logger.error("A0 context overflow — degradando: %s", error)
    return _a0_failsoft_llm_response(st, motivo)


from tools.agent_factory import build_llm_agent
context_builder_agent = build_llm_agent(
    name="ContextBuilder",
    model="gemini-3.6-flash",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Constrói contexto de mercado (market_bundle + fatos CNPJ/CNO) "
        "sem Deep Research/Kimi e sem inferências além das tools."
    ),
    instruction="""
Você é o ContextBuilder — primeiro agente do pipeline GymSite Intelligence.

## REGRA ZERO — SEM INTERPRETAÇÃO INVENTADA
- Se a tool não retornou o dado, use `"dados_nao_disponiveis"` ou omita o campo.
- PROIBIDO: achismos, "parece que", oportunidades/riscos sem fonte explícita.
- PROIBIDO a palavra **estoque** — use **parque ativo** (unidades no CNPJ) e
  **aberturas recentes** / **fluxo de aberturas** (novas unidades 90d).
- Você **consolida e cruza fatos** das tools; não é consultor criativo.
- PROIBIDO chamar Deep Research / Kimi — tools removidas (Act-on A0 bundle-only).

## FLUXO
1. Extrair cidade, bairro, uf, genero_alvo, tipo_negocio, tamanho_preset.
2. **`carregar_market_bundle(cidade, bairro, uf)` primeiro** — se retornar briefing com
   `<!-- market_bundle` (sem `status=missing`), use como `briefing_completo_md` e preencha
   ticket/tendência/demografia a partir do texto.
3. Se bundle `missing` ou lacuna de campo qualitativo → use `"dados_nao_disponiveis"`
   nesse campo e **siga**. NÃO existe fallback de pesquisa web no A0.
   Renda: A2/`renda_bairro`. Concorrência detalhada: A3a. Aluguel viabilidade: A4 MRLR.
4. `dados_parque_cnpj_para_a0(cidade, uf, dias=90, bairro=bairro)` — fatos CNPJ + CNO.
5. `fatos_competicao_local(cidade, bairro, uf)` — marcas no raio via OSM (se geocode ok), salvo cache/skip.
6. **Consolide a resposta final** como o objeto JSON do schema abaixo (texto puro —
   NÃO é function call). Tools permitidas e **somente estas três**:
   `carregar_market_bundle`, `dados_parque_cnpj_para_a0`, `fatos_competicao_local`.
   PROIBIDO inventar tools (`montar_json_*`, `write_*`, `save_*`, etc.).
   Bundle → ticket, tendência (qualitativo).
   `principais_redes_concorrentes` = **somente** `redes_detectadas_osm` da tool local.
   Se a tool local falhar ou retornar lista vazia, use `[]` — **não** invente redes.
   Tool CNPJ → números e composição. Tool CNO → área m² só onde houver match.

## SAÍDA (JSON)
O schema abaixo é REFERÊNCIA de estrutura. Sua resposta final deve ser SOMENTE o
objeto JSON — sem markdown, sem fence ```, começando por { e terminando por }.
```json
{
  "market_context": {
    "cidade": "",
    "bairro": "",
    "uf": "",
    "ticket_medio_mercado": "",
    "aluguel_medio_m2": "",
    "renda_media_bairro": "",
    "faixa_etaria_predominante": "",
    "genero_alvo": "misto",
    "tipo_negocio": "academia",
    "tamanho_preset": "m",
    "principais_redes_concorrentes": [],
    "tendencia_mercado": "crescimento|estavel|retracao",
    "regulamentacao_resumo": "",
    "insights_estrategicos": ["fato+fonte 1", "fato+fonte 2", "fato+fonte 3"],
    "parque_ativo_total": 0,
    "parque_comercial_total": 0,
    "novos_cnpj_fitness_90d": 0,
    "excluidos_saude_clinica": 0,
    "pendentes_validacao": 0,
    "composicao_parque": {},
    "novas_unidades_90d_por_segmento": {},
    "academias_ativas_cidade_cnpj": 0,
    "serie_aberturas_anual": {},
    "fatos_parque_cnpj": {
      "fonte": "RFB CNPJ Aberto",
      "metricas": {},
      "indicadores_derivados": {},
      "cruzamento_cno": {},
      "lacunas": []
    },
    "fonte_entrantes": "",
    "fonte": "market_bundle + CNPJ/CNO (tools)",
    "data_coleta": "YYYY-MM-DD",
    "cached": false,
    "briefing_completo_md": ""
  }
}
```

## REGRAS CNPJ (tool)
- Copiar `metricas_objetivas` nos campos escalares correspondentes.
- `fatos_parque_cnpj.metricas` = cópia estruturada das métricas.
- `fatos_parque_cnpj.indicadores_derivados` = só o que a tool calculou
  (ex.: taxa_renovacao_parque_90d_pct, segmento_dominante_parque).
- Se `divergencia_parque_vs_aberturas=true`, registrar em `fatos_parque_cnpj`
  como fato ("parque dominado por X; aberturas 90d por Y") — sem recomendar ação.

## REGRAS CNO (tool, se pasta disponível)
- `cruzamento_cno` = resumo_match + até 5 entrantes com `area_m2_obra` preenchida.
- Capacidade alunos = benchmark MATRICULADOS_POR_M2 do pipeline (já na tool).
- Se `sem_obra` > 0, listar em `lacunas` — não estimar m² por chute.

## INSIGHTS
- Cada insight = 1 frase com **fonte** entre parênteses: (market_bundle), (CNPJ), (CNO), (OSM).
- Pelo menos 1 insight deve citar número CNPJ.
- Sem palavra "estoque". Sem inventar ticket/tendência se bundle ausente.

## DEGRADAÇÃO
- Bundle missing → campos qualitativos `dados_nao_disponiveis`; CNPJ/OSM ainda preenchem se ok.
- CNPJ indisponível → lacunas explicam; não inventar parque.
""",
    tools=[
        carregar_market_bundle,
        dados_parque_cnpj_para_a0,
        fatos_competicao_local,
    ],
    output_key="market_context",
    after_tool_callback=_a0_after_tool_slim,
    before_model_callback=_a0_before_model_callback,
    on_model_error_callback=_a0_on_model_error_callback,
    after_agent_callback=_a0_override_cnpj_numeros,
)
