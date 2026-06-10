# QA pós-pipeline — auditoria do JSON Supabase

## Regra de ouro (fase de testes)

Após cada relatório com `status = 'done'`, executar o join em [`QA_POS_PIPELINE_JOIN.sql`](./QA_POS_PIPELINE_JOIN.sql) e validar o checklist no rodapé do arquivo.

Salvar o JSON exportado em `eval/runs/<relatorio_id>.json` se for baseline de regressão.

---

## O que NÃO é o pipeline de produção

O trecho com `fetch_market_context` retornando `densidade_populacional_hab_km2: 4820.5` e `renda_media_domiciliar_brl: 3150` é **exemplo/TODO** (protótipo de cache local). O runtime usa:

| Camada | Módulo | Dados reais? |
|--------|--------|----------------|
| Enrichment disco | `scripts/enrichment/cache_enrichment.py` + `tools/local_market_facts.py` | Sim (OSM, portais, BCB) |
| Compressão prompt | `scripts/enrichment/prompt_compressor.py` | Resume o JSON acima — **sem** 3150 fixo |
| A0 qualitativo | `tools/deep_research_tool.py` / Kimi | LLM + **cache arquivo** `market_context/{cidade}_{bairro}.md` + LangCache |
| A2 renda (score) | `tools/ibge_tools.py` | Censo IBGE por município/bairro quando mapeado |
| A4 financeiro | `tools/financial_tools.py` | Determinístico; gravado em `cenarios_financeiros` |
| CNPJ parque | `tools/cnpj_fitness_tools.py` | Supabase `cnpj_fitness_estabelecimentos` |

---

## Diagnóstico — `828df620-c299-433d-b568-9b9fe724d7f3` (Parangaba)

### 1. Split brain: `markdown_completo` vs `relatorio_outputs`

| Campo | Valor no join | Markdown no mesmo relatório |
|-------|----------------|------------------------------|
| `veredito` | **INVESTIGAR MAIS** | **APROVADO COM RESSALVAS** |
| `score_bairro` | **8.75** | **6.5** |
| `score_top1_candidato` | **8.75** | **6.9** (Top 1 Pinheiro) |
| Competição | `score_concorrencia` **null**, `total_concorrentes` **0** | 10 academias detalhadas, score comp. **1.9** |

**Causa:** o markdown é texto do A6 (LLM); scores/veredito em `relatorio_outputs` vêm de `_extrair_relatorio_estruturado` com regras determinísticas. Com `concorrentes_detalhados` vazio no state no momento do extract, o guard P1 força `INVESTIGAR MAIS` e média demográfica+viabilidade **sem** score competitivo → 8.75. O markdown foi redigido com narrativa completa (incl. A3 no texto), mas **não foi re-sincronizado** com o JSON normalizado.

### 2. `candidatos` e `competidores` vazios `[]`

O `db/supabase_writer.py` só insere linhas se `output_consolidado.top_3_candidatos` e `competitors_set` existirem no momento do `write_relatorio_failsafe`. Neste run, o extract estruturado não levou esses arrays → UI/join vazios, enquanto o markdown ainda descreve supermercados âncora e academias.

**Ação:** corrigir propagação `inteligencia_competitiva.concorrentes_detalhados` + `candidatos_geoscout` até o A6 extract; ou derivar persistência a partir do markdown parseado (fallback).

### 3. Market context cacheado e datado

```json
"cached": true,
"data_coleta": "2024-05-18"
```

Vem do **briefing Deep Research em disco** (`tools/deep_research_tool.py`, TTL ~7 dias) e/ou LangCache semântico `deep_research_a0:fortaleza:parangaba`. O A0 copia `data_coleta` do cabeçalho do cache — **não** é data do run (`2026-06-03`).

**Efeito:** insights de 2024/2025 (ex.: Top Up nov/2024) reaparecem em runs de 2026.

**Mitigação teste:** apagar `market_context/fortaleza_parangaba.md` (e hit LangCache) antes de rerun; ou `A0_RESEARCH_PROVIDER=kimi` com briefing fresco.

### 4. Renda `R$ 787,91` e “Uma fonte indica”

- **Não** vem do stub `fetch_market_context` (3150).
- **Não** é o Censo municipal usado no A2 para score (Fortaleza municipal ~**1572** — citado no próprio markdown).
- É string **`renda_media_bairro`** produzida pelo **A0 (LLM)** a partir do Deep Research, com redação vaga (“Uma fonte indica”) em vez do formato exigido no prompt: `R$ X (Deep Research)`.

O insight de “contraste com Censo” é **inferência do A0**, não um campo IBGE automático no `market_context`.

### 5. O que está correto / determinístico

- `cenarios_financeiros` + `sensibilidade_cenarios`: coerentes com A4 (Low Cost viável, Premium inviável).
- `aluguel_mensal` 30670.50, `fonte_aluguel` portais N=21.
- `fatos_parque_cnpj` / CNPJ: 1828 parque, 47 aberturas 90d — Supabase RFB real.
- `bairros_alternativos`: 4 linhas com busca Places real.
- `custos_agentes` / `api_calls`: rastreio de custo OK.
- `validacao` **null**: A8 não persistiu (ver `A8_VALIDATOR_ENABLED`, logs `persist_validacao`).

### 6. Hardcoded / fallback explícitos

| Item | Onde |
|------|------|
| Briefing DR em cache antigo | `market_context/*.md`, LangCache |
| `data_coleta` do cache | A0 não sobrescreve com `date.today()` em hit |
| Veredito `INVESTIGAR MAIS` com 0 concorrentes | `a6_report_consolidator.py` guard P1 |
| `nivel_saturacao` “indeterminado (0 concorrentes)” | mesmo guard |
| Premium payback `999` | convenção financeira “inviável” |
| LangCache A9 (outros relatórios) | desligado em dev: `LANGCACHE_A9_ENABLED=0` |

---

## Fix aplicado (2026-06-03) — extract A6

- `_resolver_competitividade_extracao`: se `inteligencia_competitiva` vazio, usa `concorrentes_brutos` (A3a) e recalcula `score_concorrencia`.
- Guard P1 (0 concorrentes) **não** dispara quando o fallback A3a tem lista.
- `_alinhar_markdown_ao_estruturado`: antes do `write_relatorio_failsafe`, alinha veredito/scores no markdown ao JSON.
- Testes: `tools/test_a6_competitividade_extracao.py`

Relatórios antigos no Supabase precisam **reprocessar** ou regravar via novo run.

## Próximos fixes recomendados (prioridade)

1. **A0:** em cache hit, setar `data_coleta` = hoje + invalidar DR > 90 dias.
2. **Renda:** preencher `renda_media_bairro` com `ibge_tools` quando bairro mapeado; DR só como nota.
3. **Insights:** proibir “Uma fonte”; exigir `(Deep Research)` ou `(CNPJ)` por bullet.
4. **A8:** investigar por que `validacoes` não persiste em alguns runs.
