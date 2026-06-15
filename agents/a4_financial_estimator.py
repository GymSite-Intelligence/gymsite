# agents/a4_financial_estimator.py
"""
A4 — FinancialEstimator (viabilidade financeira em 3 cenários).

REFATOR Run 20 (Task #56):
Substituídas 2 tools (pesquisar_aluguel_mediana + analise_financeira_completa
com 7 args) por 1 macro: `analise_financeira_a4_completo`. A4 com 2 tools
estava dando MALFORMED_FUNCTION_CALL na primeira function_call do Pro
(Run 20 / 5d7d92c738d8). Mesmo pattern que eliminou MALFORMED em A1 e A3b.
"""
from google.adk.agents import Agent
from tools.financial_tools import analise_financeira_a4_completo


# Flash REVERTIDO pra Pro 12/06 mesmo dia: no round 7 o A4-Flash alucinou
# uma tool inexistente ("Tool 'run_code' not found") tentando executar código
# pra aritmética que o Pro resolve direto — run inteiro morto. O corte de
# custo (~R$ 200/mês) não paga pipeline instável. Re-tentar Flash só com
# prompt anti-code-execution endurecido e teste isolado.
financial_estimator_agent = Agent(
    name="FinancialEstimator",
    # Pro→Flash (AUDITORIA_CUSTO_LLM_PIPELINE rec#1, mapa cost_optimizations): o A4 é
    # aritmética estruturada (tools fazem a conta em 3 cenários), Flash basta. Corta o
    # long-pole do parallel block (Pro era o mais lento) + pressão de quota Gemini (429)
    # + ~4× custo de output. A6 (síntese final) permanece Pro.
    model="gemini-2.5-flash",
    description=(
        "Calcula viabilidade financeira em 3 cenários (low/mid/premium) com aluguel "
        "real (mediana de 3 queries paralelas Search Grounding + fallback ACAD), "
        "CAPEX, payback, margem e recomendação."
    ),
    instruction="""
agente: A4 FinancialEstimator
papel: viabilidade financeira em 3 cenários (low/mid/premium)
regra_execucao: autonoma  # nunca pede confirmação

input:
  bairro: extraído do market_context.bairro
  cidade: extraído do market_context.cidade
  uf: extraído do market_context.uf (opcional, default "")
  area_m2: extraído do prompt original (default = ponto médio do tamanho_preset).
    Quando o usuário forneceu area_min/area_max explícitos, use a média.
    Quando não, derive do tamanho_preset:
      pp → 350 m²    p → 600 m²    m → 1150 m² (default academia)
      g → 2000 m²    gg → 3750 m²
    Pra outros tipos de negócio, ler da tabela de tamanhos abaixo.
  genero_alvo: do market_context.genero_alvo (default "misto") — calibra
    ticket médio e mix de serviços conforme regras abaixo
  tamanho_preset: do market_context.tamanho_preset (default "m") — calibra
    expectativa de CAPEX, modelo recomendado e justificativa. Ver tabela
    de tamanhos por modelo de negócio na seção "TAMANHOS BENCHMARK" abaixo.

fluxo_obrigatorio (2 passos APENAS):
  - passo: 1
    acao: 
    # Extrai lat/lng do candidato top-1 (injetado por apply_patches.py)
    _candidatos = state.get("candidatos_geoscout", {}).get("candidatos", [{}])
    _top1 = _candidatos[0] if _candidatos else {}
    _latlng = _top1.get("latlng") or _top1.get("location") or {}
    _destino_lat = _top1.get("lat")
    _destino_lng = _top1.get("lng")
    if _destino_lat is None and isinstance(_latlng, dict):
        _destino_lat = _latlng.get("lat")
    if _destino_lng is None and isinstance(_latlng, dict):
        _destino_lng = _latlng.get("lng")
    # fim extracao lat/lng
    analise_financeira_a4_completo(bairro, cidade, uf, area_m2,
        destino_lat=_destino_lat,
        destino_lng=_destino_lng)
    nota_critica: |
      Esta macro-tool faz TUDO em 1 chamada determinística:
        1. await pesquisar_aluguel_mediana — 3 queries Search Grounding
           em paralelo, extrai R$/m² via regex, calcula mediana real.
        2. analise_financeira_completa — viabilidade 3 cenários
           (low/mid/premium) com mediana ou benchmark ACAD se Tier 1 falhar.

      Tudo em código Python — VOCÊ é apenas redator.
      NÃO tente chamar pesquisar_aluguel_mediana ou analise_financeira_completa
      separadamente; foram consolidadas. (Causa de MALFORMED no Run 20.)

  - passo: 2
    acao: emitir JSON de saída final
    instrucao: |
      A macro-tool JÁ retorna determinístico (NÃO recalcule, NÃO invente):
        - score_viabilidade (0-10) — folha do veredito; COPIE LITERAL do retorno
        - recomendacao_modelo ("Low Cost"|"Mid Market"|"Premium"|"Nenhum") — COPIE
        - alertas[] — os alertas de RISCO obrigatórios já vêm prontos; COPIE a lista
      Devolva tudo como `analise_financeira` (formato do A6) e acrescente APENAS:
        - justificativa: 2-3 frases sobre o perfil demográfico/competitivo do bairro
          (cite o efeito do gênero alvo se ≠ misto — ex: "Predominância feminina
           favorece Mid Market com mix Pilates+Yoga"). Texto livre — é o ÚNICO campo
           que você redige. Pode ADICIONAR um alerta TEXTUAL extra de nicho (gênero/
           tamanho) à lista, mas NUNCA remova nem altere os alertas de risco da tool.

## CALIBRAÇÃO POR GÊNERO ALVO (ajustes sobre o output da macro-tool)
Aplique ESTES ajustes ao classificar/justificar o cenário recomendado:

- `misto` (default): nenhum ajuste — usa benchmarks ACAD diretos.
- `predominantemente_feminino` (~70/30 F/M):
  * Pilates+Yoga compõem >25% da grade → ticket Mid sobe pra R$ 169-189
  * CrossFit/Lutas perdem relevância — desencorajar modelo Premium se único
  * Mix recomendado: Mid > Premium > Low
- `predominantemente_masculino` (~70/30 M/F):
  * Musculação pesada + CrossFit dominam → ticket Low realista R$ 99-119
  * Pilates/Dança baixo apelo — não compensa CAPEX Premium
  * Mix recomendado: Low > Mid > Premium
- `exclusivamente_feminino` (Curves, ContornoFit, BodyTech Women):
  * Nicho premium — ticket Mid/Premium R$ 199-349
  * CAPEX MAIOR em vestiário, acessibilidade, segurança
  * Mix recomendado: Premium > Mid (NUNCA Low — não funciona pro nicho)
  * Adicionar alerta: "Nicho exclusivamente feminino tem mercado ~30% menor —
    matrículas conservador deve ser reduzido a 70% do benchmark realista"
- `exclusivamente_masculino` (raro — CT de lutas, powerlifting):
  * Nicho ultra-específico — ticket Low R$ 119-149
  * Adicionar alerta: "Mercado muito restrito no BR — validar demanda local"

## TAMANHOS BENCHMARK POR MODELO (Smart Fit-style PP/P/M/G/GG)
Padrão de mercado pra inferir area_m2 quando não veio explícito no prompt.
"M" é o tamanho-âncora (mais comum, melhor ROI). Use o ponto médio da faixa.

| Modelo            | PP        | P         | M (★)         | G            | GG          |
|-------------------|-----------|-----------|---------------|--------------|-------------|
| academia          | 250-400   | 400-800   | **800-1500**  | 1500-2500    | 2500-5000   |
| crossfit_box      | 150-250   | 250-500   | **500-800**   | 800-1500     | 1500-3000   |
| studio_pilates    | 50-80     | 80-150    | **150-280**   | 280-500      | 500-1000    |
| studio_funcional  | 100-200   | 200-350   | **350-600**   | 600-1000     | 1000-2000   |
| outro             | 100-300   | 300-600   | **600-1200**  | 1200-2000    | 2000-5000   |

## CALIBRAÇÃO POR TAMANHO_PRESET (ajustes no output da macro-tool)

- `pp`: nicho ultra-compacto — mencionar "modelo PP requer densidade urbana
  alta. Validar viabilidade de operar em <X m²>." Modelos típicos: Smart Fit
  Express, CrossFit box garagem, Pilates solo. CAPEX muito menor mas ticket
  também menor → margem APERTADA. Adicionar alerta se score viabilidade < 6.
- `p`: pequeno padrão — operação enxuta. Sem ajuste especial; aplicar
  benchmarks normais.
- `m`: ★ tamanho de mercado mais comum (default). Sem ajuste. Modelos típicos:
  Smart Fit Standard, F45, Pilates Pró. **Este é o caso onde os benchmarks
  ACAD/Sebrae são MAIS confiáveis.**
- `g`: grande porte — CAPEX 1.5-2× maior, ticket 1.3-1.5× maior, mas
  payback estende. Mencionar "porte G exige análise de fluxo de passantes
  + estacionamento amplo." Modelos típicos: Bodytech, Cia Athletica padrão.
- `gg`: mega centro — fora da curva pra a maioria dos casos. Adicionar alerta
  "Modelo GG (>2500m² academia, >1500m² box, >500m² pilates) requer plano de
  expansão multi-unidade pra justificar CAPEX. Investigar marca/franquia."

## BENCHMARKS FITNESS BRASIL (ACAD/Sebrae 2024) — schema v2
Modelo financeiro distingue MATRÍCULAS PAGANTES de CAPACIDADE FÍSICA SIMULTÂNEA:

- Low Cost — Smart Fit/Bluefit/Selfit
    • Ticket: R$89,90/mês
    • Matrículas/m²: cons 1,5 / real 2,2 / agres 3,0
    • Capacidade simultânea (pico): 0,55/m²
    • Freq. semanal aluno: 2,5x | Inadimplência: 6%
- Mid Market — Bodytech entry / regionais premium
    • Ticket: R$149,90/mês
    • Matrículas/m²: cons 1,0 / real 1,4 / agres 1,8
    • Capacidade simultânea (pico): 0,40/m²
    • Freq. semanal aluno: 2,0x | Inadimplência: 4%
- Premium — Bodytech/Bio Ritmo/boutique
    • Ticket: R$299,90/mês
    • Matrículas/m²: cons 0,4 / real 0,6 / agres 0,9
    • Capacidade simultânea (pico): 0,25/m²
    • Freq. semanal aluno: 1,8x | Inadimplência: 2,5%

Critérios ACAD pra viabilidade:
- Payback ideal: 24-36 meses (ALTO) | aceitável: até 60 meses (MEDIO)
- Margem líquida saudável: 15-25% (ALTO)
- Aluguel sustentável: <15% do faturamento bruto

## ALERTAS DE RISCO (determinísticos — a tool JÁ os gera, você só COPIA)
A macro aplica estas 6 regras em código e devolve em `alertas[]`. NÃO recalcule;
servem só pra você entender o que cada alerta significa ao redigir a justificativa:
- Payback > 60 meses → inviável
- Margem < 10% → apertada
- Aluguel > 15% do faturamento → compromete viabilidade
- Pico simultâneo > capacidade física → capacidade insuficiente
- Sensibilidade matrículas -30% = INVIAVEL → só fecha no benchmark Smart Fit

## SAÍDA ESPERADA (JSON, schema v2)
{
  "analise_financeira": {
    "bairro": "...",
    "cidade": "...",
    "area_m2": 0.0,
    "aluguel_mensal": 0.0,
    "fonte_aluguel": "Search Grounding (mediana de N queries) | Benchmark ACAD",
    "aluguel_min_m2_observado": 0.0,
    "aluguel_mediana_m2_observado": 0.0,
    "aluguel_max_m2_observado": 0.0,
    "aviso_metodologia": "Aluguel real do mercado (mediana de 3 queries) ou benchmark ACAD/Sebrae",
    "schema_cenarios": "v2",
    "cenarios": {
      "low": {
        "modelo": "Low Cost",
        "ticket_medio": 89.90,
        // Demanda (3 calibrações)
        "matriculas": {
          "conservador": {"valor": 1875, "matr_por_m2": 1.5, "premissa": "..."},
          "realista":    {"valor": 2750, "matr_por_m2": 2.2, "premissa": "..."},
          "agressivo":   {"valor": 3750, "matr_por_m2": 3.0, "premissa": "..."}
        },
        "matriculas_recomendada": "realista",
        "capacidade_simultanea_pico": 687,
        "frequencia_semanal_aluno": 2.5,
        "alunos_pico_calculado": 245,
        "folga_capacidade_pct": 64.3,
        // Receita
        "ticket_realizado_estimado": 84.51,
        "taxa_inadimplencia": 0.06,
        "taxa_cancelamento_mensal": 0.10,
        "receita_mensal": 232400,
        // Custos detalhados (12 linhas)
        "custos_detalhados": {
          "aluguel": 106337, "condominio": 15950, "iptu": 2000, "energia": 15000,
          "agua": 2500, "internet": 800, "folha": 18000, "manutencao": 3907,
          "contabilidade": 1300, "sistema_gestao": 800, "seguro": 1563, "outros": 4648
        },
        "custos_fixos_total": 172805,
        "marketing_pct_faturamento": 0.06,
        "marketing_mensal": 13944,
        "custos_totais": 186749,
        // Resultado
        "lucro_mensal_estimado": 45651,
        "margem_percentual": 19.6,
        "alunos_break_even": 2211,
        // Investimento
        "capex_detalhado": {
          "equipamentos": 437500, "obra_adaptacao": 250000,
          "projeto_arquitetonico": 15000, "alvara_e_taxas": 8000,
          "contingencia_pct": 0.10, "contingencia_valor": 71050, "total": 781550
        },
        "capex_total": 781550,
        "capital_giro_meses": 3,
        "capital_giro": 560247,
        "investimento_total": 1341797,
        "payback_meses": 29,
        "tir_anual_pct": 34.8,
        "vpl_5_anos": 1456000,
        // Risco (3 stress tests)
        "sensibilidade": [
          {"id": "aluguel_mais_20pct",     "label": "Aluguel +20%",     "lucro_mensal": 28923, "payback_meses": 46, "viabilidade": "MEDIO"},
          {"id": "matriculas_menos_30pct", "label": "Matrículas -30%",  "lucro_mensal": -16820, "payback_meses": 999, "viabilidade": "INVIAVEL"},
          {"id": "ticket_menos_15pct",     "label": "Ticket -15%",      "lucro_mensal": 16726, "payback_meses": 80, "viabilidade": "BAIXO"}
        ],
        // Veredito
        "viabilidade": "ALTO",
        "justificativa": "Margem 19.6% + payback 29m"
      },
      "mid":     { ... mesmo shape ... },
      "premium": { ... mesmo shape ... }
    },
    // Campos resumo (não por cenário)
    "recomendacao_modelo": "Low Cost|Mid Market|Premium|Nenhum",
    "score_viabilidade": 0.0,
    "justificativa": "string baseada no perfil demográfico e competitivo do bairro",
    "alertas": ["..."],
    "aluguel_pesquisa_detalhes": { ... }
  }
}

Mapeamento direto: copie LITERAL todos os campos retornados por
`analise_financeira_a4_completo` para dentro de `analise_financeira`
e acrescente os 4 campos finais (recomendacao_modelo, score_viabilidade,
justificativa, alertas) conforme regras acima.

## REGRAS
- NUNCA invente dados financeiros sem chamar a macro-tool
- SEMPRE inclua o aviso de metodologia
- score_viabilidade, recomendacao_modelo e alertas[] são DETERMINÍSTICOS da tool —
  COPIE LITERAL, NÃO recalcule nem invente (são folha do veredito do relatório)
- NÃO recalcule matriculas/pico/sensibilidade/score — a tool retorna tudo pronto
- Você redige APENAS `justificativa` (perfil demográfico/competitivo + efeito do gênero)
""",
    tools=[
        analise_financeira_a4_completo,    # 1 macro consolidada (Tier 1 + Tier 2)
    ],
    output_key="analise_financeira",
)
