# A9 — Especificação de Gráficos e Tabelas (PDF)

> Catálogo dos gráficos e tabelas do relatório PDF do A9, por seção. Para cada visual: propósito, tipo, dados de entrada, agente de origem e cores. Implementável em `pdf/charts.py`. Complementa `docs/A9_REPORT_DESIGN.md`, `docs/A9_DATA_CONFIDENCE.md` e `docs/A9_CONFIDENCE_BADGES_SPEC.md`.

## Convenções transversais

- **Paleta de séries:** TEAL `#0D9488` (primária), ORANGE `#E8751A` (destaque/alerta), SLATE `#64748B` (baixa confiança), LIME `#A3E635` (somente o ponto-foco da praça), NAVY `#1B2A4A` (eixos/títulos).
- **Veredito:** APROVADO `#16A34A`, RESSALVAS `#CA8A04`, INVESTIGAR `#EA580C`, REPROVADO `#DC2626`.
- **Estilo:** flat (sem 3D/sombra/gradiente), grid leve em BORDER `#E2E8F0`, fundo de card CARD_BG `#F1F5F9`.
- **Tipografia:** Helvetica nos rótulos (8 pt), Helvetica-Bold em títulos (10 pt).
- Todo gráfico carrega **selo de confiança** (ver spec dos badges) e uma **nota metodológica** curta no rodapé.

## 1. Resumo executivo

| Visual | Tipo | Dados de entrada | Origem | Cores |
|---|---|---|---|---|
| Score geral da praça | Medidor radial (gauge) 0–100 | score consolidado | A8/A9 | faixa em VEREDITO_COLORS |
| KPIs-chave | Tabela compacta (4–6 linhas) | população raio, nº concorrentes, ticket médio, payback | A1/A3/A4 | TEAL + selos |

## 2. Mercado e localização

| Visual | Tipo | Dados de entrada | Origem | Cores |
|---|---|---|---|---|
| Mapa de calor regional | Heatmap + pin | densidade pop. + ponto da praça | A1/A7 | base heatmap, pin LIME |
| População por raio | Barras horizontais (1/3/5 km) | população por faixa de raio | A1 | TEAL |
| Composição demográfica | Rosca (donut) | faixas etárias/renda do entorno | A1/A7 | TEAL → SLATE (degradê discreto) |
| Tabela raio × pop × domicílios × renda | Tabela | métricas por raio | A1 | linhas alternadas ROW_ALT `#F8FAFC` |

## 3. Concorrência

| Visual | Tipo | Dados de entrada | Origem | Cores |
|---|---|---|---|---|
| Mapa de posicionamento | Dispersão (scatter) preço × distância | concorrentes mapeados | A3 | pontos SLATE, praça LIME, tamanho = porte |
| Comparativo de concorrentes | Tabela (tipo, distância, faixa de preço, diferenciais) | concorrentes | A3 | cabeçalho NAVY, selos de triangulação |

## 4. Financeiro (3 cenários)

| Visual | Tipo | Dados de entrada | Origem | Cores |
|---|---|---|---|---|
| Receita e resultado por cenário | Colunas agrupadas (conservador/base/otimista) | projeções A4 | A4 | conservador SLATE, base TEAL, otimista TEAL_DARK `#115E59` |
| Fluxo de caixa acumulado | Linha + marcador de break-even | fluxo mensal | A4 | linha TEAL, payback ORANGE (linha vertical) |
| Sensibilidade | Barras tornado | impacto de variáveis-chave | A4 | barras TEAL/ORANGE por direção |
| DRE comparativa | Tabela 3 cenários lado a lado | DRE simplificada | A4 | faixa mín–máx destacada, selos |

## 5. Posicionamento

| Visual | Tipo | Dados de entrada | Origem | Cores |
|---|---|---|---|---|
| Perfil da praça | Radar (5–6 eixos: demanda, concorrência, custo ocupação, renda, acessibilidade, potencial digital) | scores normalizados | A9 | área TEAL translúcida, borda TEAL_DARK |
| Atratividade × esforço | Matriz 2×2 | classificação da praça | A9 | quadrantes em tons SLATE, praça LIME |

## 6. Recomendações

| Visual | Tipo | Dados de entrada | Origem | Cores |
|---|---|---|---|---|
| Ações priorizadas | Tabela (ação, impacto, esforço, prazo) | recomendações | A9 | selos de veredito por linha |
| Roadmap de fases | Timeline horizontal | fases sugeridas | A9 | barras TEAL, marcos ORANGE |

## Prioridade de implementação (MVP enxuto)

1. **Gauge de veredito** (resumo executivo)
2. **Scatter de concorrência** (seção 3)
3. **Colunas dos 3 cenários + linha de payback** (seção 4)
4. **Tabela DRE comparativa** (seção 4)

Esses quatro concentram quase toda a decisão. Os demais entram em iterações seguintes.

---

*Especificação de design — implementável em `pdf/charts.py` (gráficos) e `pdf/builder.py` (tabelas/layout). Nenhuma fonte real é citada; todos os dados vêm dos agentes internos A1–A9.*
