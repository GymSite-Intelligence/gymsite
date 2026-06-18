# agents/a3c_competitor_mapper.py
"""
A3c — CompetitorMapper (enriquece concorrentes com oferta real).

Roda DEPOIS do A3b CompetitorAnalysis. Visita site oficial + Instagram
público de cada concorrente top 10, extrai modalidades / faixa de preço /
diferenciais via keyword matching (offer_mapper) + normalização LLM.

Modo SHADOW (default 2026-05-12): output `oferta_concorrentes` é gravado
no state mas A6 ReportConsolidator NÃO consome ainda. Validar acurácia
em 5 relatórios antes de ativar feature flag A3C_ENFORCE no A6.

Motivação: relatório `abd16249-fb4e-42a8-b371-83855c95099f` (Niterói/Itaipu)
recomendou "explorar piscina + área kids visto a ausência local" — mas
Tio Sam tem AMBOS no site oficial. Sem A3c, A6 deduz ausência por silêncio
nos reviews. Com A3c, A6 saberá que Tio Sam tem `piscina + area_kids` e
filtrará a recomendação.

Custo estimado: ~R$ 0,20/relatório (Gemini Flash 2.5, ~5k tokens input).
"""
from google.adk.agents import Agent
from google.genai import types

from tools.offer_mapper_tool import mapear_oferta_competidores_completo


# ─── Fallback callback (mesmo padrão A5 ContactHunter) ──────────────────────
# Bug observado em 2026-05-12 (run bdab58e1): LLM Flash chamou a macro-tool
# corretamente (input 101k tokens), mas no 2º turno emitiu apenas 53 tokens
# ao invés de ~5k pro JSON canônico. Resultado: `oferta_concorrentes` vazio
# no state, persistência null em competidores.oferta_mapeada.
#
# Fix: callback after_agent que, quando state vazio, executa a macro-tool
# direto e normaliza sem LLM (keywords detectadas → estrutura canônica).

def _confianca_label(conf_fonte: float) -> str:
    if conf_fonte >= 0.7:
        return "alta"
    if conf_fonte >= 0.4:
        return "media"
    return "baixa"


def _faixa_preco_mensal(precos: list[dict]) -> dict | None:
    """Filtra preços com período mensal e retorna {min, max} ou None."""
    mensais = []
    for p in precos or []:
        periodo = (p.get("periodo") or "").lower()
        if "mes" in periodo or "mensal" in periodo:
            try:
                mensais.append(float(p.get("valor_brl")))
            except (TypeError, ValueError):
                pass
    if not mensais:
        return None
    return {"plano_mensal_min": min(mensais), "plano_mensal_max": max(mensais)}


def _normalizar_oferta_basica(raw: dict) -> dict:
    """Converte OfertaMapeada bruta em formato canônico (sem LLM)."""
    conf = float(raw.get("confiabilidade_fonte") or 0)
    fontes = []
    if raw.get("fonte_url_ok"):
        fontes.append("website")
    if raw.get("fonte_instagram_ok"):
        fontes.append("instagram")
    obs = ""
    if conf == 0:
        obs = "sem evidência (site/IG falharam ou sem fonte)"
    elif conf < 0.4:
        obs = "baixa cobertura textual — sinais escassos"
    return {
        "nome": raw.get("nome"),
        "modalidades": raw.get("modalidades_keywords") or [],
        "diferenciais": raw.get("diferenciais_keywords") or [],
        "faixa_preco_brl": _faixa_preco_mensal(raw.get("precos_encontrados") or []),
        "fontes": fontes,
        "confiabilidade_oferta": _confianca_label(conf),
        "observacoes": obs,
        "_fallback_sem_llm": True,
    }


def _a3c_after_agent_fallback(callback_context):
    """
    Fallback após A3c: se LLM não emitiu `oferta_concorrentes`, executa a
    macro-tool direto e normaliza sem LLM. Garante persistência defensiva.

    Compositor: também chama state_dump no fim (substitui o callback que
    o _attach_telemetry colocaria).
    """
    state = getattr(callback_context, "state", None)

    if state is not None and not state.get("oferta_concorrentes"):
        try:
            class _Ctx:
                pass
            ctx = _Ctx()
            ctx.state = state
            macro_out = mapear_oferta_competidores_completo(ctx)
            mapeamento = macro_out.get("mapeamento_oferta", {}) or {}
            normalizado = {
                k: _normalizar_oferta_basica(v)
                for k, v in mapeamento.items()
                if isinstance(v, dict)
            }
            state["oferta_concorrentes"] = {
                "oferta_concorrentes": normalizado,
                "total_processados": macro_out.get("total_processados", 0),
                "sucessos": macro_out.get("sucessos", 0),
                "taxa_sucesso": macro_out.get("taxa_sucesso", 0.0),
                "fallback_executado_no_callback": True,
            }
        except Exception:
            import logging
            logging.getLogger("gymsite.a3c").warning(
                "A3c fallback falhou — oferta_concorrentes ficará vazio (shadow, não bloqueia)",
                exc_info=True,
            )

    # Preserva state_dump da telemetria existente
    try:
        from tools.state_diagnostics import after_agent_state_dump
        after_agent_state_dump(callback_context)
    except Exception:
        pass

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=1024),
)

from tools.agent_factory import build_llm_agent
competitor_mapper_agent = build_llm_agent(
    name="CompetitorMapper",
    model="gemini-2.5-flash",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Visita site oficial + Instagram público dos concorrentes top 10 "
        "(via macro-tool) e produz `oferta_concorrentes` normalizado: "
        "modalidades, faixa de preço e diferenciais REAIS. Modo SHADOW — "
        "A6 ainda não consome o output."
    ),
    instruction="""
agente: A3c CompetitorMapper
papel: enriquecer concorrentes_detalhados com oferta real (site + Instagram)
regra_execucao: autonoma

input:
  fonte: session_state.inteligencia_competitiva.concorrentes_detalhados (do A3b)
  acesso: via macro-tool (NUNCA passar como argumento explícito)

fluxo_obrigatorio (2 passos APENAS):
  - passo: 1
    acao: mapear_oferta_competidores_completo()
    nota_critica: |
      Chame SEM ARGUMENTOS. A macro lê concorrentes_detalhados direto do
      state, dispara fetch paralelo (max 5 simultâneos) de site oficial +
      Instagram público, e retorna mapeamento bruto com keywords detectadas
      + raw_texto + raw_meta_description.
    output: dict com `mapeamento_oferta`, `total_processados`, `sucessos`,
            `taxa_sucesso`

  - passo: 2
    acao: emitir JSON canônico de saída
    instrucao: |
      Pra cada concorrente em `mapeamento_oferta`, NORMALIZE os dados
      brutos em um JSON canônico. Use APENAS o que o `raw_texto` /
      `raw_meta_description` / `modalidades_keywords` suportam — NÃO
      INFIRA modalidades ausentes do texto. Se `confiabilidade_fonte` < 0.3
      ou `raw_texto` vazio, marque `confiabilidade_oferta: "baixa"` e deixe
      modalidades vazias (preserva o registro mas sinaliza incerteza).

regras_extracao:
  modalidades_canonicas_validas:
    - musculacao
    - piscina
    - area_kids
    - crossfit
    - pilates
    - yoga
    - spinning
    - lutas
    - funcional
    - danca
    - personal
    - avaliacao_fisica
    - estetica
    - natacao
  diferenciais_canonicos_validos:
    - ar_condicionado
    - horario_24h
    - estacionamento
    - wifi
    - vestiario_premium
    - app
    - personal_incluso
    - diaria
    - biometria
  regras_de_evidencia:
    - Cite uma modalidade APENAS se o texto bruto tem evidência LITERAL
      (palavra ou sinônimo direto). Não use inferência por contexto.
    - Faixa de preço: APENAS se `precos_encontrados[]` tem itens. Se vazio,
      retorne `faixa_preco_brl: null`.
    - `plano_mensal_min`/`max` derivam de itens com período "mes"/"mensal".
      Ignore "diaria" e "anual" pra esses campos.
    - Se houver apenas 1 preço mensal, min=max=esse valor.
    - confiabilidade_oferta:
        alta:  confiabilidade_fonte >= 0.7
        media: 0.4 <= confiabilidade_fonte < 0.7
        baixa: confiabilidade_fonte < 0.4 OU raw_texto vazio
  observacoes:
    - Max 200 chars.
    - Cite EVIDÊNCIA literal quando relevante (ex: "site menciona 'piscina
      semi-olímpica climatizada'").

saida_obrigatoria_json:
  oferta_concorrentes:                  # dict; chave = place_id ou nome
    "<chave_concorrente>":
      nome: string
      modalidades: [string]            # subset modalidades_canonicas_validas
      faixa_preco_brl:                 # null se sem preço mensal detectado
        plano_mensal_min: float_or_null
        plano_mensal_max: float_or_null
      diferenciais: [string]           # subset diferenciais_canonicos_validos
      fontes: [string]                 # ["website"] | ["instagram"] | ambos
      confiabilidade_oferta: string    # "alta" | "media" | "baixa"
      observacoes: string              # max 200 chars
  total_processados: int               # copiar da macro
  sucessos: int                        # copiar da macro
  taxa_sucesso: float                  # copiar da macro

regras_payload:
  - NÃO chame `mapear_oferta_concorrente` direto. Use SEMPRE a macro.
  - NÃO invente modalidades fora de `modalidades_canonicas_validas`.
  - NÃO faça "dedução por silêncio" (ex: "não tem piscina porque não
    menciona no texto"). Silêncio = sem evidência, não = ausência.
  - NÃO copie `raw_texto` ou `raw_meta_description` no output final —
    eles são input pra você normalizar, não pra propagar.
""",
    tools=[
        mapear_oferta_competidores_completo,
    ],
    output_key="oferta_concorrentes",
    after_agent_callback=_a3c_after_agent_fallback,
)
