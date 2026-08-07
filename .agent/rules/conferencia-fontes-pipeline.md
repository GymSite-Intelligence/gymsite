# Conferência de Fontes — Documento Canônico (alwaysApply)

> **Ler ANTES de qualquer mudança** em `agents/*.py`, `tools/*_tools.py`, `agents_site/tools.py`, `backend/routers/site_agent.py`, contratos de relatório ou specs A0–A9.
> Adotado jul/2026. Complementa (não substitui) [`pipeline-fontes-deterministicas.md`](pipeline-fontes-deterministicas.md) e [`docs/arquitetura/PIPELINE_AGENTES.md`](../../docs/arquitetura/PIPELINE_AGENTES.md).

---

## 1. Regra de ouro

| Tipo de dado | Fonte canônica | Proibido no caminho crítico |
|---|---|---|
| Concorrência Maps | SearchAPI `google_maps` · **R=1000 m do centróide** + gate tipo/status (jul/2026) | Scraping Maps; LLM inventando N; **gate string de bairro** no caminho crítico |
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
| `tools/a1_listing_pipeline.py` | listing filtrado + `aluguel_deterministico` por área real do candidato A1 |

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

## 9. Contagem de concorrentes — gate espacial (nacional)

**Adotado jul/2026** (R=1000 m); **Spec C ago/2026** (polígono IBGE quando resolvido).

| Camada | Papel | Canônico |
|---|---|---|
| Query Formato 1 (`academia no bairro X, cidade - UF`) | Recall SearchAPI | Hint |
| Centróide (geocode do ponto do relatório) | Âncora | Sim |
| **Polígono IBGE do bairro** (Censo 2022) — se `resolver_bairro_poligono` hit | Gate de inclusão | **Preferido** (Spec C) |
| `dist(centroid, place) ≤ R` com **R = 1000 m** | Gate de inclusão | **Fallback** sem polígono |
| Gate **tipo** (`_tipo_relevante` / exclude pilates·studio·luta·crossfit p/ `academia`) | Escopo do negócio | Sim |
| Status operacional (descarta `CLOSED`) | Limpeza | Sim |
| String “bairro no nome/endereço” | — | **Proibido** no caminho crítico |

**Demografia (A2):** com polígono — setores com centróide **dentro** do polígono (pop + idade×sexo = mesma lista). Sem polígono — raio **1500 m** + fill `pop_alvo` (legado).

**Número exibido** = `|places|` após gate espacial + tipo + status.  
**Carimbo:** `N · polígono IBGE bairro · SearchAPI…` **ou** `N · raio 1000 m do centróide · SearchAPI…`.  
**Smoke URL:** lista Maps **bruta** ≠ N; carimbar aviso ou listar só `place_id`s filtrados — nunca apresentar o link como prova do total.

Constante código: `RAIO_CONCORRENCIA_CANONICO_M = 1000` em `tools/competitor_tools.py` (fallback). Resolver: `tools/bairro_poligono.py`. Spec: `docs/superpowers/specs/2026-08-06-spec-c-bairro-poligono-ibge-design.md`.

---

## 9.1 Matriz demografia × saturação → modelo

| Peça | Fonte |
|---|---|
| Compute | `tools/matriz_demo_saturacao.py` — **não** A0/A2 |
| Limiares | `param()` (`matriz_n_per_10k_*`, `matriz_premium_min_armadilha`, …) |
| Quem anexa W1 | A9 `attach_matriz_demo_saturacao` → `relatorio_posicionamento.matriz_demo_saturacao` |
| PDF | Seção **Modelo de Negócio Adequado** (`pdf/html_builder.py`) |
| Veto A4 | `quadrante == Armadilha de Renda` → `modelo_recomendado` ≠ premium genérico |
| Espacial | Preferir `gate_espacial=poligono_ibge_bairro` (Spec C); senão `raio_fallback` |
| Aluguel | **Não muda** — continua MRLR Tier 0 |

Precedência: **Armadilha vence** headroom `OCEANO_AZUL` se `mix.premium ≥ matriz_premium_min_armadilha` (`matriz_override=true`). W3: `baixas_24m` / `rede_ancora` = modifiers CNPJ (não substituem N/10k). Spec: `docs/superpowers/specs/2026-08-07-matriz-demo-saturacao-modelo-design.md`.

---

## 9.2 Absorção / margem fresca (W2a)

| Peça | Regra |
|---|---|
| Compute | `tools/absorcao_margem_fresca.py` — **não** A0/A2; Matriz **não** embute a fórmula |
| Área proxy | `area_proxy_low_m2=1000`, mid=1500, premium=2000, nicho/desc=1250 (`param()`) |
| Capacidade parque | N×tier × área_proxy × `matr_m2_*_realista` |
| Pool | estoque etário × `penetracao_potencial_fitness` × pen academia (`geral`\|`bairro_ab`) — **não** pop total crua; **não** 100% da faixa Core |
| Três pools | primário (form) · secundário (resto 15+) · total; rótulo fresco/misto/roubo só no **primário** |
| PDF | Seção **Absorção e margem de alunos** (`pdf/html_builder.py`) · preview = `gerar_html` |
| Quem anexa | A9 `attach_absorcao_margem_fresca` → `relatorio_posicionamento.absorcao_margem_fresca` |
| Spatial W2a | Spec C PIP / raio — **sem Voronoi** |
| Spec | `docs/superpowers/specs/2026-08-07-absorcao-margem-fresca-design.md` |

---

## 10. Testes de regressão MRLR

| Teste | O que valida |
|---|---|
| `tools/test_aluguel_mrlr.py` | `aluguel_deterministico` espelhos |
| `tools/test_mrlr_reproducao.py` | Mesma praça = mesmo valor |
| `tools/test_anexar_aluguel_mrlr.py` | Paridade A1 candidato × A4 |
| `tools/test_a0_override.py` | A0 não inventa CNPJ |

Rodar: `.venv/Scripts/python.exe -m pytest tools/test_aluguel_mrlr.py tools/test_mrlr_reproducao.py tools/test_anexar_aluguel_mrlr.py`
