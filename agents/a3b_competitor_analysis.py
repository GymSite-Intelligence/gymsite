# agents/a3b_competitor_analysis.py
"""
A3b — CompetitorAnalysis (agregação + scores + posicionamento).

Sub-agente especialista da fase competitiva. Recebe `concorrentes_brutos`
do A3a (via session state output_key) e produz:
- inteligencia_competitiva (gaps, dores nominadas, oportunidades)
- estrategia_counter_programming (picos/vales)
- score_concorrencia (saturação numérica)
- posicionamento_recomendado

NÃO faz busca — isso é do A3a.
"""
from google.adk.agents import Agent
from google.genai import types
from tools.competitor_tools import analisar_concorrentes_completo

# HISTÓRICO DE REGRESSÕES OUT=0 — A3b é estruturalmente sensível:
#
# 2026-05-08 (Flash + thinking_budget=8192) — OUT=0, A6 não rodou.
#   Hipótese inicial: budget consumiu output. Foi engano.
#
# 2026-05-09 manhã (Pro, dynamic default) — OUT=0 reproduzido em Pro.
#   Hipótese: AFC limit / payload size. Parcialmente correto.
#
# 2026-05-09 tarde — bug de `rating_geral=None` corrigido em
#   `competitor_tools.py:267`, mas OUT=0 continuou.
#
# 2026-05-09 fim de tarde — telemetria com `finish_reason` revelou
#   MALFORMED_FUNCTION_CALL. CAUSA RAIZ REAL:
#   o LLM tentava reenviar `concorrentes_brutos` (com 5+ concorrentes,
#   cada um carregando `enrichment_search_grounding_text` de 1k+ chars)
#   como argumento de `analisar_gap_competitivo`. O payload corrompia
#   o function_call, Gemini retornava MALFORMED, A3b emitia OUT=0.
#
# FIX 2026-05-09 (VEC-380): substituir 4 tools que recebiam payload
# por 1 macro-tool que LÊ DO STATE — `analisar_concorrentes_completo`.
# Function_call vira `analisar_concorrentes_completo()` sem args =>
# impossível ser malformed. A3b vira "redator" que pega o output da
# macro e adiciona `posicionamento_recomendado` + `resumo_executivo`.
_GENERATE_CONFIG = types.GenerateContentConfig()

competitor_analysis_agent = Agent(
    name="CompetitorAnalysis",
    model="gemini-2.5-flash-lite",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Análise agregada de concorrentes: gaps de mercado, dores dominantes "
        "(com nominação), counter-programming (picos/vales), saturação e score. "
        "Lê concorrentes_brutos do session state (output do A3a) via macro-tool."
    ),
    instruction="""
agente: A3b CompetitorAnalysis
papel: análise agregada + scores + posicionamento
regra_execucao: autonoma  # nunca pede confirmação

input:
  fonte: session_state.concorrentes_brutos (gerado pelo A3a)
  acesso: via macro-tool (NUNCA passar como argumento explícito)

fluxo_obrigatorio (2 passos APENAS):
  - passo: 1
    acao: analisar_concorrentes_completo()
    nota_critica: |
      Chame SEM ARGUMENTOS. A macro-tool lê concorrentes_brutos
      direto do state. Tentar passar payload em argumento causa
      MALFORMED_FUNCTION_CALL — bug histórico documentado.
      O nome da tool é EXATAMENTE `analisar_concorrentes_completo` —
      NUNCA adicione prefixo como `default_api.` ou namespace algum
      (run 56d17ea0 morreu com "Tool 'default_api.analisar_concorrentes_completo'
      not found").
    output: dict com inteligencia_competitiva + estrategia_counter_programming
            + nivel_saturacao + rating_medio_concorrentes + score_concorrencia
  - passo: 2
    acao: emitir JSON de saída final
    instrucao: |
      Pegue o output da macro-tool, adicione 2 campos textuais novos
      (posicionamento_recomendado, resumo_executivo) e retorne o JSON
      consolidado conforme `saida_obrigatoria_json` abaixo.

regras_traducao:
  - Reviews vêm do Google Maps frequentemente em INGLÊS (autores estrangeiros)
  - O relatório final é em PT-BR — para CADA review em outro idioma,
    inclua a versão traduzida em concorrentes_detalhados[].reviews_traduzidas
  - Manter o nome do autor sem traduzir (nomes próprios)
  - Indicar idioma original entre colchetes
  - Exemplo:
      ANTES: "Lost almost 2 hours trying to follow ridiculous registration rules..."
      DEPOIS: "Perdi quase 2 horas tentando seguir regras de cadastro ridículas..." [original em inglês]

saida_obrigatoria_json:
  inteligencia_competitiva:
    concorrentes_detalhados:  # PRESERVE TODOS os campos do slim + reviews_traduzidas
      - nome: string                          # da macro
        endereco: string                      # da macro - NÃO omita
        bairro_concorrente: string            # da macro - NÃO omita
        rating_geral: float                   # da macro
        num_avaliacoes: int                   # da macro
        tem_24h: bool                         # da macro - NÃO omita
        telefone: string                      # da macro - NÃO omita (vem do Places API)
        website: string                       # da macro - NÃO omita (vem do Places API)
        horarios_pico: dict_or_null           # da macro
        reviews_traduzidas:                   # ENRIQUECIDO pelo LLM
          - quote_pt_br: string
            quote_original: string
            idioma_original: string  # "inglês"|"espanhol"|"português"
            autor: string
            rating: int
            data_relativa: string
            categoria_dor: string
    dores_dominantes: [{dor, mencoes, mencionado_por:[{academia, vezes}]}]  # da macro
    servicos_nao_oferecidos: [string]   # da macro
    oportunidades_rankeadas: [...]      # da macro
    score_oportunidade_mercado: float    # da macro
    melhor_avaliada: {nome, rating}      # da macro
    pior_avaliada: {nome, rating}        # da macro
  estrategia_counter_programming:        # da macro
    picos_compartilhados: [...]
    vales_compartilhados: [...]
    estrategias_acionaveis: [...]
    concorrentes_com_dados: int
  nivel_saturacao: BAIXO|MEDIO|ALTO|SATURADO  # da macro
  rating_medio_concorrentes: float            # da macro
  score_concorrencia: float                   # OBRIGATORIO numerico — da macro
  distribuicao_geografica:                    # OBRIGATORIO — copiar literal da macro
    - bairro: string                          # ex: "Aldeota"
      count: int                              # quantos concorrentes nesse bairro
      academias: [string]                     # nomes das academias
  total_concorrentes_analisados: int          # da macro
  posicionamento_recomendado: string  # NOVO — texto livre baseado nos gaps
  resumo_executivo: string             # NOVO — max 3 frases

regras_payload:
  - NÃO chame `analisar_gap_competitivo`, `analisar_picos_competitivos`,
    `classificar_saturacao` ou `calcular_score_concorrencia` separadamente.
    Foram consolidadas em `analisar_concorrentes_completo`.
  - NÃO passe `concorrentes_brutos` ou qualquer payload grande como argumento.
  - NÃO omita campos do slim em `concorrentes_detalhados`. Copie LITERAL os
    campos `endereco`, `bairro_concorrente`, `tem_24h`, `telefone`, `website`,
    `horarios_pico` do output da macro-tool — só adicione `reviews_traduzidas`
    por cima. Esses contatos vão pro CRM e o relatório fica capenga sem eles.
""",
    tools=[
        analisar_concorrentes_completo,
    ],
    output_key="inteligencia_competitiva",
)


def _a3b_filtrar_concorrentes(callback_context, *args, **kwargs):
    """Filtro AUTORITATIVO pós-A3b: o LLM re-emite a lista (e às vezes dropa `tipos`);
    aqui dropamos vizinho-de-bairro + off-type (CrossFit/Artes Marciais em 'academia')
    DETERMINISTICAMENTE no inteligencia_competitiva — governa a tabela competidores, os
    cards do A6 e o markdown (todos leem essa chave). Best-effort, nunca derruba."""
    try:
        from tools.competitor_tools import (
            _parse_market_context,
            filtrar_concorrentes_bairro_tipo,
        )

        st = callback_context.state
        ic = st.get("inteligencia_competitiva")
        ic = ic if isinstance(ic, dict) else _parse_market_context(ic)
        if not isinstance(ic, dict):
            return None
        inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
        lista = inner.get("concorrentes_detalhados") if isinstance(inner, dict) else None
        if not isinstance(lista, list) or not lista:
            return None
        mc = _parse_market_context(st.get("market_context"))
        mci = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
        ip = st.get("input_params") if isinstance(st.get("input_params"), dict) else {}
        bairro = (st.get("bairro") or ip.get("bairro")
                  or (mci.get("bairro") if isinstance(mci, dict) else "") or "")
        tipo = (ip.get("tipo_negocio") or (mci.get("tipo_negocio") if isinstance(mci, dict) else "")
                or "academia")
        inner["concorrentes_detalhados"] = filtrar_concorrentes_bairro_tipo(
            lista, bairro=bairro, tipo_negocio=tipo
        )
        st["inteligencia_competitiva"] = ic
    except Exception:
        pass
    return None


competitor_analysis_agent.after_agent_callback = _a3b_filtrar_concorrentes
