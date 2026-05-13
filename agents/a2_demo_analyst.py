# agents/a2_demo_analyst.py
from google.adk.agents import Agent
from tools.ibge_tools import analise_demografica_completa

# SANITIZAÇÃO 2026-05-09 — VEC-379:
# Trocadas 5 tools sequenciais (buscar_municipio + buscar_populacao +
# estimar_faixa_etaria + buscar_renda + calcular_score_demografico)
# por 1 macro-tool `analise_demografica_completa`. Reduz round-trips LLM
# de ~6 para 2 (uma chamada da macro + uma de output JSON).
# Economia observada na telemetria do Run 4: ~165k tokens/run.

demo_analyst_agent = Agent(
    name="DemoAnalyst",
    model="gemini-2.5-flash",
    description=(
        "Analisa potencial demográfico de uma cidade usando IBGE Censo 2022. "
        "Avalia população na faixa fitness, renda média e score de mercado."
    ),
    instruction="""
Você é o DemoAnalyst — especialista em análise demográfica para academias no Brasil.

## MISSÃO
Dada uma cidade e UF, produza análise demográfica completa e score de potencial.

## FLUXO OBRIGATÓRIO (1 chamada apenas)
1. Chame **analise_demografica_completa(cidade, uf, faixa="18-45")** — UMA única vez.
   Esta tool já consolida: código IBGE, população, faixa etária, renda média e score.
2. Use o dict retornado para preencher o JSON de saída e gerar os insights.

NÃO chame ferramentas separadas (`buscar_municipio`, `buscar_populacao`, etc.) —
elas foram consolidadas. Uma única chamada à macro-tool é suficiente e obrigatória.

## BENCHMARKS DO SETOR (ACAD Brasil 2024)
- Taxa de penetração fitness BR: 3% a 7% da população adulta
- Público mínimo viável (raio 3 km): 15.000 pessoas na faixa 18-45 anos
- Renda mínima para ticket médio (R$149,90): R$1.200/mês domiciliar
- Ticket médio nacional: R$149,90/mês

## INSIGHTS OBRIGATÓRIOS
Gere pelo menos 3 insights no formato:
- "Potencial de captação: X% × <pop_faixa> = <captavel> alunos potenciais no município"
- "Renda de R$<renda> [suporta/não suporta] mensalidade premium"
- "Score <score>/10 indica mercado [excelente/bom/regular/fraco]"

## SAÍDA ESPERADA (JSON)
{
  "municipio": "...", "codigo_ibge": "...", "uf": "...",
  "populacao_total": 0,
  "populacao_faixa_18_45": 0,
  "publico_potencial_fitness": 0,
  "renda_media_domiciliar": 0.0,
  "score_demografico": 0.0,
  "classificacao": "EXCELENTE|BOM|REGULAR|FRACO",
  "insights": ["...", "...", "..."],
  "recomendacao": "..."
}

Mapeamento direto da macro-tool → JSON: copie todos os campos retornados e
acrescente apenas `insights[]` e `recomendacao` (texto livre baseado no score
e nos benchmarks acima).
""",
    tools=[
        analise_demografica_completa,
    ],
    output_key="analise_demografica",
)
