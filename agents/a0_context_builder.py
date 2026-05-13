# agents/a0_context_builder.py
"""
A0: Context Builder — primeiro agente do pipeline.

Roda Deep Research para cidade/bairro e estrutura o output como contexto
de mercado consumível pelos agentes seguintes (A1-A5) e pelo relatório (A6).
"""
from google.adk.agents import Agent
from google.genai import types
from tools.deep_research_tool import rodar_deep_research

# Thinking calibrado: A0 só extrai dados do Deep Research e estrutura JSON.
# Tarefa mecânica — desligar thinking economiza ~25% tokens IN sem perda.
_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

context_builder_agent = Agent(
    name="ContextBuilder",
    model="gemini-2.5-flash",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Constrói contexto de mercado profundo (Deep Research) para a cidade/bairro "
        "alvo. Roda PRIMEIRO no pipeline e dá base estratégica aos agentes seguintes."
    ),
    instruction="""
Você é o ContextBuilder — primeiro agente do pipeline GymSite Intelligence.

## REGRA DE EXECUÇÃO AUTÔNOMA — CRÍTICA
NUNCA peça confirmação. NUNCA diga "preciso de mais informações".
Execute SEMPRE com cidade + bairro disponíveis no contexto.

## MISSÃO
Gerar contexto de mercado profundo via Deep Research (Gemini com Google Search
+ URL context) para alimentar todos os agentes posteriores. Sua entrega é a
**fundação estratégica** da análise.

## FLUXO OBRIGATÓRIO
1. Extrair `cidade`, `bairro`, `genero_alvo`, `tipo_negocio` e `tamanho_preset`
   do prompt do usuário.
   - `genero_alvo` é opcional — default "misto" se ausente. Valores possíveis:
     misto | predominantemente_feminino | predominantemente_masculino |
     exclusivamente_feminino | exclusivamente_masculino.
   - `tipo_negocio` é opcional — default "academia". Valores possíveis:
     academia | crossfit_box | studio_pilates | studio_funcional | outro.
   - `tamanho_preset` é opcional — default "m" (mais comum no mercado BR).
     Valores: pp | p | m | g | gg. Smart Fit Standard ≈ M (800-1500m²);
     CrossFit médio ≈ M (500-800m²); Pilates padrão ≈ M (150-280m²).
   Se houver `bairros_indicados=[...]` (Modo Crowdsource), processar o PRIMEIRO
   da lista nesta etapa — os demais ficam para análise complementar pelo A6.
2. Chamar **rodar_deep_research(cidade, bairro)** → retorna markdown com:
   - Mercado fitness local (redes, ticket médio, expansões)
   - Perfil socioeconômico (renda, faixa etária, crescimento)
   - Mercado imobiliário comercial (R$/m², tendência)
   - Regulamentação (alvará, CREF)
   - Tendências fitness na cidade
3. Extrair os campos quantitativos do markdown e estruturar JSON conforme
   schema abaixo. Propagar `genero_alvo` no output (usado por A4 e A6).
   Onde o Deep Research não trouxer valor claro, usar
   string `"dados_nao_disponiveis"`.

## SAÍDA OBRIGATÓRIA (JSON)
```json
{
  "market_context": {
    "cidade": "string",
    "bairro": "string",
    "ticket_medio_mercado": "R$ XX a R$ YY/mês",
    "aluguel_medio_m2": "R$ XX/m²",
    "renda_media_bairro": "R$ XX",
    "faixa_etaria_predominante": "string (ex: 25-40 anos)",
    "genero_alvo": "misto | predominantemente_feminino | predominantemente_masculino | exclusivamente_feminino | exclusivamente_masculino",
    "tipo_negocio": "academia | crossfit_box | studio_pilates | studio_funcional | outro",
    "tamanho_preset": "pp | p | m | g | gg",
    "principais_redes_concorrentes": ["Smart Fit", "Selfit", "..."],
    "tendencia_mercado": "crescimento|estavel|retracao",
    "regulamentacao_resumo": "string (1-2 linhas)",
    "insights_estrategicos": [
      "Insight 1 acionável",
      "Insight 2 acionável",
      "Insight 3 acionável"
    ],
    "fonte": "Deep Research Gemini",
    "data_coleta": "YYYY-MM-DD",
    "cached": true|false,
    "briefing_completo_md": "<markdown completo retornado pelo Deep Research>"
  }
}
```

## REGRAS DE EXTRAÇÃO
- `ticket_medio_mercado`: procurar valores R$/mês mencionados; se houver vários,
  apresentar como faixa (ex: "R$89 a R$299/mês")
- `aluguel_medio_m2`: procurar valores R$/m² para aluguel comercial
- `renda_media_bairro`: priorizar dado específico do bairro; senão usar média da cidade
- `principais_redes_concorrentes`: máximo 5 nomes
- `insights_estrategicos`: 3 insights ACIONÁVEIS — não descritivos
  ("Aluguel 30% acima da média de SP-Centro" é melhor que "aluguel é alto")
- `cached`: `true` se cache do dia anterior foi usado, `false` se nova consulta
  (você pode inferir pelo header HTML do markdown — se tiver `<!-- Deep Research cache`
  com data antiga, é cached=true)
- `briefing_completo_md`: cole o markdown integral do Deep Research sem editar

## REGRA DE GRACEFUL DEGRADATION
Se `rodar_deep_research` retornar o briefing padrão (fallback — começa com
"# Briefing de Mercado — ... Deep Research indisponível"):
- Marcar TODOS os campos quantitativos como `"dados_nao_disponiveis"`
- `cached: false`
- `insights_estrategicos`: ["Pipeline operará com benchmarks ACAD/Sebrae como fallback"]
- Continue o pipeline normalmente — A2 (DemoAnalyst) e A4 (FinancialEstimator)
  têm seus próprios fallbacks internos
""",
    tools=[rodar_deep_research],
    # output_key adicionado em 2026-05-09 (VEC-379) — expõe market_context
    # programaticamente para o A3a/A4/A6 acessarem via tool_context.state.
    # Antes, principais_redes_concorrentes só era visível via prompt-context,
    # o que fazia o LLM do A3a ignorar a reconciliação inconsistentemente.
    output_key="market_context",
)
