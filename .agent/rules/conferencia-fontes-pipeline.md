# Conferência de Fontes — Documento Canônico (alwaysApply)

> **Ler ANTES de qualquer mudança** em `agents/*.py`, `tools/*_tools.py`, `agents_site/tools.py`, `backend/routers/site_agent.py`, contratos de relatório ou specs A0–A9.
> Adotado jul/2026. Complementa (não substitui) [`pipeline-fontes-deterministicas.md`](pipeline-fontes-deterministicas.md) e [`docs/arquitetura/PIPELINE_AGENTES.md`](../../docs/arquitetura/PIPELINE_AGENTES.md).

---

## 1. Regra de ouro

| Tipo de dado | Fonte canônica | Proibido no caminho crítico |
|---|---|---|
| Concorrência Maps | SearchAPI `google_maps` | Scraping Maps; LLM inventando N |
| Reviews | SearchAPI `google_maps_place.review_results` (1 call c/ pico); fallback `google_maps_reviews` | LLM como única classificação |
| Imóveis candidato | `listing_cascata` (SearchAPI) | Listing como **fonte de aluguel** |
| **Aluguel viabilidade (OPEX)** | **`aluguel_deterministico` → `mrlr_modelo`** (A4 Tier 0) | Preço de anúncio; SearchAPI `rent_sqm`; A7 grounding |
| Aluguel referência batch | ~~`bundle.aluguel_portais`~~ | **removido** — `tools/9_obsolete/` |
| Demografia | IBGE Censo 2022 / espelhos BQ | LLM inventando número |
| CNPJ/CNO | RFB/Supabase determinístico | LLM (A0 override fecha CNPJ) |
| Pico / popular times | SearchAPI `google_maps_place` + `cache_places_details` / `cache_popular_times` | A7 como fonte primária no pipeline |
| Crowdsource §14 | Input usuário + validação | SearchAPI inventando demanda |
| A7 gaps qualitativos | Google Search Grounding (chat on-demand) | Aluguel, concorrência, demografia |

**Número no relatório = tool ou banco.** LLM narra (A6/A9) ou refina texto já coletado.

---

## 2. MRLR — aluguel determinístico

### 2.1 Código canônico

| Arquivo | Papel |
|---|---|
| `tools/mrlr_modelo.py` | Equação IBAPE-GO (coeficientes em `catalogos_metodologia`) |
| `tools/aluguel_mrlr.py` | `aluguel_deterministico()` — lê espelhos Supabase |
| `tools/financial_tools.py` | A4 macro — **Tier 0 MRLR** sobrescreve tiers portal/grounding |
| `tools/anchoring_tools.py` | `_anexar_aluguel_mrlr` — mesmo número no candidato A1 |

### 2.2 Inputs obrigatórios para `status=ok`

| Input | Origem | Obrigatório |
|---|---|---|
| `area_m2` | Form / `input_params` / candidato | ✅ > 0 |
| `cidade` | Usuário / stub relatório | ✅ lookup `renda_bairro` |
| `bairro` | Usuário / stub relatório | ✅ lookup `bairro_norm` |
| `id_municipio` | Derivado de `renda_bairro.municipio_cod` | ✅ (ou passado) |
| `populacao`, `pib_reais` | `municipio_pib` | ✅ |
| `percentil_municipio` | `renda_bairro` | opcional → padrão 2 |
| `zona_sigla` | Zoneamento A1 | opcional → local=2 (ZEDUS/ZOC) |

**Espelhos Supabase:** `renda_bairro` (cidade + `bairro_norm`) + `municipio_pib` (`id_municipio`).

**Normalização bairro:** `bairro_norm` sem acento — "Coco" deve casar "Cocó" (`aluguel_mrlr._norm_busca`).

### 2.3 Outputs (carimbo P-010)

```text
valor_unitario_m2 · área informada · MRLR IBAPE-GO · espelhos municipio_pib + renda_bairro
```

Campos: `valor_unitario_m2`, `aluguel_total`, `fonte`, `inputs` (padrao, local, porte, pib, fator_economico, renda_percentil).

### 2.4 O que NÃO alimenta MRLR

- `price_raw` de listing SearchAPI/OLX — só display no candidato
- `bundle.aluguel_portais` — contexto A0 batch, selo ORANGE
- SearchAPI `google_light` `rent_sqm` — estimativa snippet, nunca Tier 0
- A7 Google Search Grounding — chat qualitativo apenas

---

## 3. `backend/routers/site_agent.py` × MRLR

### 3.1 Fluxo

`POST /api/site-agent/analise` → `NovoRelatorioInput` → **mesmo pipeline ADK** → A4 `analise_financeira_a4_completo` → Tier 0 MRLR.

Site agent **não chama** `aluguel_mrlr` diretamente — pipeline A4 resolve.

### 3.2 Campos que o stub fornece hoje

| Campo `AnaliseInput` | Vai para pipeline | MRLR usa? |
|---|---|---|
| `cidade` | ✅ | ✅ lookup renda |
| `bairro` | ✅ | ✅ lookup renda |
| `uf` | opcional | indireto (disambiguar cidade) |
| `tipo_negocio` | ✅ | A4 CAPEX, não MRLR |
| `area_m2` | ❌ **ausente** | usa default stub `300–1500`, preset `m` |

**Gap:** visitante não informa área na landing — MRLR roda com área inferida do preset (`area_m2_min/max` hardcoded 300–1500). Mesma praça + preset = mesmo R$/m²; total mensal varia com área efetiva que A4 escolhe.

### 3.3 Mini-relatório free (`GET /analise/{id}`)

`_extras_teaser` expõe `aluguel_m2` de `relatorio_outputs` (`aluguel_mediana_m2`, `aluguel_min_m2`, `aluguel_max_m2`) — **produto do A4 MRLR**, não SearchAPI.

### 3.4 Chat degustação (`POST /conversar`)

`localizacao` (cidade/bairro) preenche form Tier 2. Para MRLR no relatório completo: cidade + bairro resolvíveis em `renda_bairro` são **mínimo**. Área explícita melhora total mensal, não R$/m² (equação é por m²).

### 3.5 Checklist site_agent

- [ ] `cidade` + `bairro` presentes no stub antes de enfileirar pipeline
- [ ] Não documentar/implicar aluguel via SearchAPI na landing
- [ ] `aluguel_m2` no teaser = saída A4, carimbar fonte MRLR no relatório completo
- [ ] Futuro: `area_m2` opcional em `AnaliseInput` melhora payback no teaser

---

## 4. `agents_site/tools.py` × MRLR

| Tool | MRLR? | Notas |
|---|---|---|
| `estimar_investimento` | ✅ via A4 | Única tool site para **aluguel viabilidade** |
| `buscar_pontos_comerciais` | ✅ via A1 | `aluguel_estimado` = MRLR; `price_raw` = anúncio |
| `pesquisar_contexto_mercado` | ❌ | Bundle pode ter `aluguel_portais` — **não decisão** |
| `buscar_concorrentes` | — | Sem aluguel |
| `analisar_demografia` | — | Sem aluguel |

**Regra para agentes site:** pergunta de aluguel/viabilidade → `estimar_investimento`, nunca citar `bundle.aluguel_portais` como OPEX.

---

## 5. Slot A7 — o que entra e o que não entra

A7 = agente **lateral** (chat/grounding), **fora** do pipeline A0→A9.

| Gap | Responsável | A7? |
|---|---|---|
| Aluguel viabilidade | **A4 MRLR** | ❌ |
| Concorrência | **A3a** SearchAPI | ❌ |
| Pico residual | **A3a** (+ A7 só chat fallback narrativo) | ⚠️ chat only |
| Crowdsource §14 | slot novo / input usuário | ⚠️ qualitativo |
| Regulatório municipal pontual | A7 grounding | ✅ com carimbo |

**Proibido:** reintroduzir "aluguel portal SearchAPI" no slot A7 do pipeline.

---

## 6. `market_bundle` — aluguel fora do batch

- **`aluguel_portais` removido do bundle batch** (jul/2026) — código em `tools/9_obsolete/`.
- Aluguel viabilidade = **A4 MRLR** apenas.
- `LIVE_TRAIL_FIELDS` = só `competicao_osm` (trilha viva batch).

---

## 7. Checklist pré-merge (obrigatório)

1. Fonte primária = SearchAPI ou determinístico (esta tabela)?
2. Aluguel tocado? → só `aluguel_mrlr` / A4 Tier 0?
3. Passo novo bloqueia A1 ou ParallelAnalysis?
4. Duplica fetch de agente posterior?
5. LLM introduz número? Justificado e listado em PIPELINE_AGENTES §6?
6. Número exibido tem carimbo P-010?
7. Specs/docs desta seção §8 atualizados?

---

## 8. Índice de documentos — manter sincronizados

| Mudança | Atualizar |
|---|---|
| Qualquer fonte pipeline | Este arquivo + `pipeline-fontes-deterministicas.md` + `PIPELINE_AGENTES.md` §7–§9 |
| Aluguel / MRLR | `SPEC_A4_FinancialEstimator.md` + `tools/aluguel_mrlr.py` docstring |
| A7 escopo | `SPEC_A7_MarketResearch.md` |
| A0 bundle | `SPEC_A0_ContextBuilder.md` + `market_bundle.py` comentários |
| Site / landing | `agents_site/tools.py` docstrings + `site_agent.py` header |
| SearchAPI ingestão | `A9_SEARCHAPI_INGESTION.md` (rent_sqm = ORANGE, não A4 Tier 0) |
| Agente novo | `.agent/AGENTS.md` + `processo-mudanca.md` § Pipeline |

---

## 9. Testes de regressão MRLR

| Teste | O que valida |
|---|---|
| `tools/test_aluguel_mrlr.py` | `aluguel_deterministico` espelhos |
| `tools/test_mrlr_reproducao.py` | Mesma praça = mesmo valor |
| `tools/test_anexar_aluguel_mrlr.py` | Paridade A1 candidato × A4 |
| `tools/test_a0_override.py` | A0 não inventa CNPJ |

Rodar: `.venv/Scripts/python.exe -m pytest tools/test_aluguel_mrlr.py tools/test_mrlr_reproducao.py tools/test_anexar_aluguel_mrlr.py`
