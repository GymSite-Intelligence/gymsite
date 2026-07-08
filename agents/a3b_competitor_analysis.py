# agents/a3b_competitor_analysis.py
"""
A3b — CompetitorAnalysis (agregação + scores + posicionamento) — DETERMINÍSTICO (sem LLM).

Recebe `concorrentes_brutos` do A3a (via state) e produz `inteligencia_competitiva`
(gaps, dores nominadas, counter-programming, saturação, score_concorrencia).

REFATOR determinização (2026-06): A3b era LlmAgent cujo trabalho era CHAMAR a macro
`analisar_concorrentes_completo` (que calcula TUDO) e RE-EMITIR o JSON de volta +
2 campos de texto. O LLM não produzia número — só re-digitava o output da macro,
e o fazia mal: dropava campos (`tipos`, `telefone`, `website`), exigindo um
after_agent_callback determinístico (`_a3b_filtrar_concorrentes`) + `validar_lenient`
pra consertar. Pior: re-enviar o payload grande causava MALFORMED_FUNCTION_CALL /
OUT=0 (histórico de regressões 05/2026) — A3b era "estruturalmente sensível".

Agora é BaseAgent: roda a macro direto, grava o envelope VERBATIM e sintetiza
`posicionamento_recomendado` + `resumo_executivo` por TEMPLATE determinístico (mesmos
fatos da macro, zero número novo). Mata a classe de crash (sem function_call do LLM,
impossível malformar), zera custo-token e elimina o conserto pós-LLM (a macro JÁ
filtra bairro/tipo inline).

NOTA: a tradução de reviews EN→PT (único enriquecimento real que o LLM fazia) saiu
do caminho determinístico — reviews ficam no idioma original com `categoria_dor`. Se
quiser PT, religar via narrador opcional (Claude headless + guardrail), como A6/A9.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.competitor_tools import (
    analisar_concorrentes_completo,
    filtrar_concorrentes_bairro_tipo,
    _parse_market_context,
)

_ERRO_ENVELOPE = {
    "inteligencia_competitiva": {
        "concorrentes_detalhados": [],
        "dores_dominantes": [],
        "servicos_nao_oferecidos": [],
        "oportunidades_rankeadas": [],
        "score_oportunidade_mercado": 0.0,
        "melhor_avaliada": {"nome": "N/A", "rating": 0},
        "pior_avaliada": {"nome": "N/A", "rating": 0},
    },
    "estrategia_counter_programming": {
        "picos_compartilhados": [],
        "vales_compartilhados": [],
        "estrategias_acionaveis": [],
        "concorrentes_com_dados": 0,
    },
    "nivel_saturacao": "BAIXO",
    "rating_medio_concorrentes": 0.0,
    "score_concorrencia": 7.0,
}


class _StateShim:
    """tool_context mínimo — a macro só lê `.state`."""

    __slots__ = ("state",)

    def __init__(self, state):
        self.state = state


def _topo(seq, *chaves):
    """1º item da lista; se dict, tenta as `chaves` em ordem; senão o próprio item."""
    if not isinstance(seq, list) or not seq:
        return None
    it = seq[0]
    if isinstance(it, dict):
        for k in chaves:
            v = it.get(k)
            if v:
                return v
        return None
    return it


def _sintetizar_textos(envelope: dict) -> tuple[str, str]:
    """Monta posicionamento_recomendado + resumo_executivo por TEMPLATE, a partir dos
    fatos que a macro já calculou. Determinístico: nenhum número/fato novo, só os do
    envelope. Mesmo papel do antigo texto-livre do LLM, sem alucinação."""
    ic = envelope.get("inteligencia_competitiva")
    ic = ic if isinstance(ic, dict) else {}
    dores = ic.get("dores_dominantes") or []
    servicos = ic.get("servicos_nao_oferecidos") or []
    opps = ic.get("oportunidades_rankeadas") or []
    melhor = ic.get("melhor_avaliada") or {}
    n = len(ic.get("concorrentes_detalhados") or [])
    sat = envelope.get("nivel_saturacao") or "—"
    score = envelope.get("score_concorrencia")

    top_dor = _topo(dores, "dor")
    top_serv = _topo(servicos, "servico", "nome")
    top_opp = _topo(opps, "titulo", "oportunidade", "nome")

    # Resumo executivo (3 frases no máx., só fato do envelope)
    partes = [f"{n} concorrentes analisados, saturação {sat}"]
    if isinstance(score, (int, float)):
        partes[0] += f" (score de concorrência {score})"
    if top_dor:
        partes.append(f"Dor dominante dos alunos: {top_dor}")
    if melhor.get("nome") and melhor.get("nome") != "N/A":
        partes.append(f"Melhor avaliada: {melhor.get('nome')} ({melhor.get('rating')}★)")
    resumo_executivo = ". ".join(partes) + "."

    # Posicionamento recomendado (a partir do gap). Nome de categoria interna
    # (atendimento_ruim) NUNCA vaza pro cliente — humanizar antes de frasear.
    def _humano(s) -> str:
        return str(s or "").replace("_", " ").strip()

    rec = []
    if top_serv:
        rec.append(f"Gap de oferta: {_humano(top_serv)}")
    if top_dor:
        rec.append(f"atacar a dor \"{_humano(top_dor)}\" que os concorrentes não resolvem")
    if top_opp:
        rec.append(f"explorar {_humano(top_opp)}")
    posicionamento_recomendado = (
        "; ".join(rec).capitalize() + "."
        if rec
        else "Sem gap dominante mapeado — posicionar por qualidade de execução e atendimento."
    )
    return posicionamento_recomendado, resumo_executivo


def _filtrar_envelope(envelope: dict, state: dict) -> None:
    """Filtro determinístico AUTORITATIVO sobre `concorrentes_detalhados` (in-place):
    dropa vizinho-de-bairro, off-type e CLOSED. A macro já filtra bairro/tipo no bruto,
    mas isto reforça sobre o envelope final (+ CLOSED) e governa a tabela do A6. Era o
    after_agent_callback `_a3b_filtrar_concorrentes` no LlmAgent; agora roda inline, sem
    LLM no meio pra re-emitir/dropar. Best-effort: nunca derruba."""
    try:
        ic = envelope.get("inteligencia_competitiva")
        inner = ic if isinstance(ic, dict) else {}
        lista = inner.get("concorrentes_detalhados")
        if not isinstance(lista, list) or not lista:
            return
        mc = _parse_market_context(state.get("market_context"))
        mci = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
        ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
        bairro = (state.get("bairro") or ip.get("bairro")
                  or (mci.get("bairro") if isinstance(mci, dict) else "") or "")
        tipo = (ip.get("tipo_negocio") or (mci.get("tipo_negocio") if isinstance(mci, dict) else "")
                or "academia")
        inner["concorrentes_detalhados"] = filtrar_concorrentes_bairro_tipo(
            lista, bairro=bairro, tipo_negocio=tipo
        )
    except Exception:
        pass


def _mesclar_servicos_na_oferta(envelope: dict, oferta_out: dict) -> None:
    """FUSÃO A3c: mescla as modalidades mapeadas (site+IG via SearchAPI) em
    `servicos_oferecidos` de CADA concorrente. Esse é o campo que o A9 `_gaps_reais`
    lê pra computar o GAP da ERRC. Sem o merge, serviço que o concorrente tem (mas só
    aparece no site, não no IG/search) fica de fora → vira gap FALSO → ERRC manda
    'CRIAR' algo que já existe → relatório furado. In-place, best-effort."""
    mp = (oferta_out or {}).get("oferta_concorrentes") or {}
    if not isinstance(mp, dict) or not mp:
        return
    ic = envelope.get("inteligencia_competitiva")
    inner = ic if isinstance(ic, dict) else {}
    for i, c in enumerate(inner.get("concorrentes_detalhados") or []):
        if not isinstance(c, dict):
            continue
        chave = c.get("place_id") or c.get("nome") or f"idx_{i}"
        of = mp.get(chave)
        if not isinstance(of, dict):  # fallback: casa por nome
            of = next((v for v in mp.values()
                       if isinstance(v, dict) and v.get("nome") == c.get("nome")), None)
        if not isinstance(of, dict):
            continue
        atuais = {s for s in (c.get("servicos_oferecidos") or []) if s}
        novos = {m for m in (of.get("modalidades") or []) if m}
        c["servicos_oferecidos"] = sorted(atuais | novos)


class CompetitorAnalysisAgent(BaseAgent):
    """A3b+A3c FUNDIDO, determinístico: agrega (dores/gaps/score) + mapeia oferta
    (serviços/planos via SearchAPI) e mescla os serviços por concorrente. Grava
    inteligencia_competitiva (com serviços completos) + oferta_concorrentes."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        try:
            envelope: dict[str, Any] = analisar_concorrentes_completo(_StateShim(state))
            if not isinstance(envelope, dict) or "erro" in envelope:
                raise ValueError(envelope.get("erro") if isinstance(envelope, dict) else "macro retornou não-dict")
        except Exception as e:  # nunca derruba o pipeline — A6 lida com envelope vazio
            print(f"[A3b determinístico] falha: {type(e).__name__}: {e}")
            envelope = {**_ERRO_ENVELOPE, "aviso": f"{type(e).__name__}: {e}"}

        _filtrar_envelope(envelope, state)
        pos, resumo = _sintetizar_textos(envelope)
        envelope["posicionamento_recomendado"] = pos
        envelope["resumo_executivo"] = resumo

        # ── FUSÃO A3c: mapeia oferta (determinístico, SearchAPI) + mescla serviços ──
        oferta_out: dict[str, Any] = {}
        try:
            from tools.offer_mapper_tool import mapear_oferta_competidores_completo

            # state-shim com o envelope pronto (a macro lê concorrentes_detalhados dele)
            tmp = dict(state)
            tmp["inteligencia_competitiva"] = envelope
            mapear_oferta_competidores_completo(_StateShim(tmp))  # seta tmp['oferta_concorrentes']
            oferta_out = tmp.get("oferta_concorrentes") or {}
            _mesclar_servicos_na_oferta(envelope, oferta_out)
        except Exception as e:  # oferta é best-effort — nunca derruba a análise
            print(f"[A3b fusão oferta] {type(e).__name__}: {e}")

        # Validação leniente do contrato (best-effort — só loga divergência).
        try:
            from models.pipeline_schemas import InteligenciaCompetitiva, validar_lenient

            inner = envelope.get("inteligencia_competitiva")
            validar_lenient(
                InteligenciaCompetitiva,
                inner if isinstance(inner, dict) else envelope,
                agente="A3b",
            )
        except Exception:
            pass

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={
                "inteligencia_competitiva": envelope,
                "oferta_concorrentes": oferta_out,
            }),
        )


competitor_analysis_agent = CompetitorAnalysisAgent(
    name="CompetitorAnalysis",
    description=(
        "A3b determinístico (sem LLM): roda analisar_concorrentes_completo (gaps, dores, "
        "saturação, score, distribuição) e grava inteligencia_competitiva no state. "
        "Sintetiza posicionamento+resumo por template. Substitui o LlmAgent-eco que "
        "crashava com MALFORMED_FUNCTION_CALL e exigia conserto pós-LLM."
    ),
)
