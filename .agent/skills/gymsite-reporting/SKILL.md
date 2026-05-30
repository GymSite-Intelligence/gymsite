---
name: gymsite-reporting
description: Geração de relatórios PDF e visualizações para GymSite Intelligence. Use ao criar, modificar ou depurar relatórios PDF, gráficos, ou layouts de saída. NÃO use para backend REST, pipelines de agente, ou componentes React de UI.
---

# GymSite Intelligence — Relatórios e PDF

## Contexto da Stack

- **PDF Engine:** ReportLab (layout programático)
- **Gráficos:** matplotlib (charts financeiros, demográficos)
- **Temas:** Classic | Executive | Data Room
- **Formato:** PDF estruturado com capa, sumário, seções e anexos

## Estrutura de um Relatório

```
1. Capa
   - Título, cidade, data, logotipo
2. Sumário Executivo
   - Veredito (VIÁVEL / VIÁVEL COM RESSALVAS / INVIÁVEL)
   - Score de confiança
3. Contexto de Mercado (A0)
   - CNPJ do parque, entrantes, tendências
4. Análise Geográfica (A1)
   - Mapa de zonas, listings comerciais
5. Demografia e Renda (A2)
   - Pirâmide etária, renda per capita
6. Concorrência (A3)
   - Tabela de concorrentes, oferta, diferenciais
7. Viabilidade Financeira (A4)
   - 3 cenários (low/mid/premium), payback, VPL
8. Contatos Qualificados (A5)
   - Decision makers, telefones, emails
9. Anexos
   - Gráficos, tabelas brutas, fontes
```

## Padrão de Código

### Gerar PDF

```python
from pdf.builder import RelatorioPDFBuilder
from pdf.theme import TemaClassic

builder = RelatorioPDFBuilder(
    tema=TemaClassic(),
    cidade="Fortaleza",
    bairro="Aldeota",
)
builder.adicionar_capa()
builder.adicionar_sumario_executivo(veredito="VIÁVEL", score=0.87)
builder.adicionar_contexto_mercado(dados_a0)
builder.adicionar_viabilidade_financeira(dados_a4)

pdf_bytes = builder.render()
```

### Gráfico Financeiro

```python
from pdf.charts import grafico_payback_cenarios

grafico_payback_cenarios(
    cenarios={
        "low": {"payback": 28, "cor": "#4CAF50"},
        "mid": {"payback": 22, "cor": "#2196F3"},
        "premium": {"payback": 18, "cor": "#9C27B0"},
    },
    output_path="artifacts/payback_chart.png",
)
```

## Temas Disponíveis

| Tema | Uso | Características |
|---|---|---|
| `Classic` | Cliente padrão | Cores sóbrias, layout tradicional |
| `Executive` | Investidor | Foco em números, gráficos grandes |
| `Data Room` | Due diligence | Tabelas densas, fonte pequena |

## Anti-padrões

- ❌ Não gere PDFs em requisições HTTP síncronas — use `BackgroundTasks`
- ❌ Não use fontes sem licença comercial — use Helvetica/Helvetica-Bold (padrão ReportLab)
- ❌ Não ignore quebras de página — use `builder.nova_pagina()` explicitamente
- ❌ Não renderize matplotlib em thread principal do ADK — use `asyncio.to_thread`

## Cache de Relatórios

```python
# Relatórios são cacheados por 24h
from tools.cache_store import get_cached, set_cached

key = f"pdf_{relatorio_id}"
pdf = get_cached(key)
if not pdf:
    pdf = gerar_pdf(relatorio_id)
    set_cached(key, pdf, ttl_days=1)
```
