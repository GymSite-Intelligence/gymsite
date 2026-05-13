# agents/a3a_competitor_search.py
"""
A3a — CompetitorSearch (busca + enrichment).

Sub-agente especialista da fase competitiva. Responsável APENAS por buscar
academias concorrentes, processar reviews e fazer enrichment via Google
Knowledge Panel + Search Grounding.

NÃO faz análise agregada — isso é do A3b. Separação evita estouro do
AFC=10 do Gemini (era um dos bugs recorrentes do A3 monolítico).

REFATOR Task #48 (2026-05-09):
Substituídas 4 tools (buscar_concorrentes_balanceados, buscar_reviews_academia,
enriquecer_concorrente_via_google, pesquisar_no_google_grounding) por
1 macro-tool: `analisar_concorrentes_a3a_completo`. Pipeline antes
ocupava 9 round-trips do LLM (~244k tokens). Agora 2: macro + emit JSON.
"""
from google.adk.agents import Agent
from tools.competitor_tools import analisar_concorrentes_a3a_completo


competitor_search_agent = Agent(
    name="CompetitorSearch",
    model="gemini-2.5-flash",
    description=(
        "Busca concorrentes academia (Top 5 balanceado por rede do A0), "
        "coleta reviews + enrichment + classificação semântica de dores em "
        "1 macro-tool. Output: concorrentes_brutos[] em session state pra A3b."
    ),
    instruction="""
agente: A3a CompetitorSearch
papel: busca + enrichment de concorrentes academia
regra_execucao: autonoma  # nunca pede confirmação

input:
  bairro: extraído do market_context.bairro
  cidade: extraído do market_context.cidade

fluxo_obrigatorio (2 passos APENAS):
  - passo: 1
    acao: analisar_concorrentes_a3a_completo(bairro, cidade)
    nota_critica: |
      Esta macro-tool faz TUDO em 1 chamada determinística:
        1. Busca + reconciliação A0 (Top 5 balanceado)
        2. Filtro semântico academia_tradicional (descarta clínicas)
        3. Reviews via Places Details (5 por concorrente)
        4. Enrichment Google Knowledge Panel (best-effort)
        5. Classificação SEMÂNTICA de dores via Gemini Flash (batch único)

      O algoritmo é DETERMINÍSTICO em Python — você é apenas redator.
      NÃO chame as 4 tools antigas separadamente; elas foram consolidadas.

  - passo: 2
    acao: emitir JSON de saída final
    instrucao: |
      Pegue o output da macro-tool e devolva-o LITERAL como
      `concorrentes_brutos` (já no formato esperado pelo A3b),
      mais os metadados de cobertura A0 (redes solicitadas/cobertas/não encontradas).

saida_obrigatoria_json:
  escopo_busca: academia_tradicional
  total_concorrentes: int
  concorrentes_brutos:                     # da macro
    - place_id: string
      nome: string
      endereco: string
      bairro_concorrente: string
      rating_oficial: float
      num_avaliacoes: int
      tem_24h: bool
      telefone: string
      website: string
      origem_busca: "nearby" | "expandida_a0"
      reviews:
        - rating: int
          quote_curta: string         # max 180 chars (já truncado pela tool)
          autor: string
          data_relativa: string
          categoria_dor: string       # taxonomia fechada (Task #46)
          sinal: positivo|neutro|negativo
          confianca_classificacao: alta|media|baixa
      horarios_pico: dict_or_null
      pico_semanal: string_or_null
      atividade_marketing: dict_or_null
      enrichment_search_grounding_text: string_or_null
  concorrentes_excluidos:                  # da macro
    - nome: string
      motivo: string
  redes_a0_solicitadas: [string]           # da macro
  redes_a0_cobertas: [string]              # da macro
  redes_a0_nao_encontradas: [string]       # da macro
  classificacao_dores_status: string       # "ok" ou "fallback_substring"

regras_payload:
  - NÃO chame tools além de `analisar_concorrentes_a3a_completo`.
  - NÃO refaça classificação de dores — a macro já fez via Gemini.
  - NÃO trunque ou enriqueça nada manualmente — tudo vem pronto.
""",
    tools=[
        analisar_concorrentes_a3a_completo,
    ],
    output_key="concorrentes_brutos",
)
