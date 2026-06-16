# A9 — Skills Recomendadas para o Relatório

> Skills sugeridas para habilitar o agente A9 (positioning_strategist) a emitir um relatório PDF estruturado com competências de **consultor de academias + marketing + financeiro**. Ancorado na arquitetura real de agentes (A0–A9) e na pasta `.agents/skills` (que hoje contém apenas skills de Supabase/Postgres — nenhuma skill de domínio fitness ainda). Complementa `docs/A9_REPORT_DESIGN.md`, `docs/A9_DATA_CONFIDENCE.md`, `docs/A9_CONFIDENCE_BADGES_SPEC.md` e `docs/A9_CHARTS_TABLES_SPEC.md`.

## Contexto da arquitetura

O pipeline já produz os insumos; o A9 consolida e posiciona:
- **A0** context · **A1** geoscout · **A2** demo_analyst · **A3/A3a/A3b/A3c** competitor intel
- **A4** financial_estimator · **A5** contact_hunter · **A6** report_consolidator
- **A7** market_research · **A8** validator · **A9** positioning_strategist

As skills abaixo dão ao A9 a **linguagem e os frameworks** para transformar dados em recomendação de negócio.

## Grupo 1 — Consultor de academias (domínio fitness)

| Skill | O que habilita | Insumo |
|---|---|---|
| `fitness-market-sizing` | Estimar demanda local (penetração de mercado, % população-alvo, sazonalidade) | A1, A2, A7 |
| `gym-business-models` | Reconhecer modelos (low-cost, premium, boutique, 24h, studio) e seus benchmarks operacionais | A3, A7 |
| `location-fit-scoring` | Pontuar adequação ponto×modelo (fluxo, vizinhança, estacionamento, visibilidade) | A1 |
| `competitor-positioning` | Mapear lacunas competitivas e espaço em branco de posicionamento | A3 |
| `membership-economics` | Entender métricas do setor (churn, LTV, ticket, ocupação por horário) | A4 |

## Grupo 2 — Marketing

| Skill | O que habilita | Insumo |
|---|---|---|
| `gtm-playbook` | Recomendar canais de aquisição por perfil de praça (digital, local, parcerias) | A7 |
| `brand-positioning` | Articular proposta de valor e mensagem central por segmento | A9 |
| `funnel-metrics` | Definir metas de CAC, conversão, custo por lead realistas | A4, A7 |
| `local-marketing` | Táticas de marketing geolocalizado e comunidade | A1, A7 |

## Grupo 3 — Financeiro

| Skill | O que habilita | Insumo |
|---|---|---|
| `financial-modeling-3scenarios` | Construir DRE e fluxo de caixa em conservador/base/otimista | A4 |
| `unit-economics` | Calcular payback, break-even, margem de contribuição | A4 |
| `investment-readiness` | Estruturar CAPEX/OPEX e necessidade de capital de giro | A4 |
| `sensitivity-analysis` | Avaliar variáveis críticas e margem de erro (tornado) | A4 |

## Grupo 4 — Transversais (saída/PDF)

| Skill | O que habilita |
|---|---|
| `report-structuring` | Organizar narrativa executiva → detalhe → recomendação |
| `data-confidence-tagging` | Aplicar selos de confiança e notas metodológicas (ver specs) |
| `pdf-chart-composition` | Selecionar e compor gráficos/tabelas conforme `A9_CHARTS_TABLES_SPEC.md` |
| `executive-summary-writing` | Sintetizar veredito em linguagem de decisão |

## Prioridade de implementação

1. **financial-modeling-3scenarios** + **unit-economics** (núcleo da decisão de investimento)
2. **competitor-positioning** + **location-fit-scoring** (núcleo do veredito de praça)
3. **report-structuring** + **data-confidence-tagging** (qualidade/credibilidade da saída)
4. **gtm-playbook** + **brand-positioning** (camada de marketing acionável)

## Observação sobre `.agents/skills`

Hoje a pasta só tem skills de Supabase/Postgres. As skills acima seriam **novas skills de domínio** a adicionar lá, cada uma como um documento de instrução/contexto que o A9 carrega ao gerar o relatório. Nada aqui altera código — é a especificação do conjunto de skills a criar.

---

*Documento de recomendação — consolida a discussão de skills do A9. Nenhuma fonte real é citada; todos os insumos vêm dos agentes internos A1–A9.*
