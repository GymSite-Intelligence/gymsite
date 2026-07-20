# Plano de ação — Custo granular por chamada × Score × Localidade

**Data:** 2026-07-15 · **Branch:** `cursor/custo-granular-plano-acao-73fa`

---

## 0. Arquivos analisados

| Arquivo | O que é | Uso nesta análise |
|---------|---------|-------------------|
| `custos_tudo_2026-07-15_e909.csv` | **Export real** da tela `/custos` (1 linha = 1 relatório) | **Fonte principal** — ver [`ANALISE_CUSTOS_TUDO_2026-07-15.md`](./ANALISE_CUSTOS_TUDO_2026-07-15.md) |
| `campanha-flow_33fe.csv` | Lista de **leads** (não é custo) | Só orçamento projetado SearchAPI se gerar relatórios em lote |

**Achado-chave (Cocó, n=36):** custo **R$ 1,60–17,49 (×10,9)**; junho mediana R$ 5,90 / 1,0M tokens → julho **R$ 2,71 / 73k tokens (−54% custo)**. Correlação tokens×custo **0,82**. Score **não vem** neste export.

Arquivos gerados:
- `docs/produto/assets/custo-granular/custos_tudo_2026-07-15_enriquecido.csv` (responsável + tools esperadas + outliers)
- `docs/produto/assets/custo-granular/divergencia_mesma_localidade.csv`
- `docs/produto/assets/custo-granular/catalogo_chamadas_agente_tool.csv`
- `docs/produto/ANALISE_CUSTOS_TUDO_2026-07-15.md`

---

## 1. Decisão em 30 segundos

| Tema | Veredito |
|------|----------|
| Export `/custos` atual | Agregado por relatório — **sem** score e **sem** linhas por tool |
| Divergência **mesmo bairro** (Cocó) | **Provada:** R$ 1,60–17,49; julho −54% vs junho porque tokens −93% |
| Vilão do custo alto | **LLM tokens** (r=0,82 com custo), não SearchAPI N× |
| N× calls reviews/pico/IG | By design (`MAX_ENRIQUECIMENTO=6`) — ruído pequeno vs R$ 17 |
| Score × custo | **Ainda cego** neste CSV — incluir score no export |
| Outlier a investigar | 2026-07-15 Cocó R$ 6,17 / 53k tok / **3427 s** |

---

## 2. Catálogo granular (responsável × tool × SKU)

Preço SearchAPI canônico no código: `SEARCHAPI_USD_PER_SEARCH` default **US$ 0.004** (`tools/pricing.py`).  
Taxa USD→BRL default **5,40** → ~**R$ 0,0216 / crédito**.

### 2.1 Pacote “1 relatório A3 enriquecido default” (SearchAPI)

Fonte: diagrama interno + `MAX_ENRIQUECIMENTO` (default 6) em `competitor_tools.py`.

| # | Responsável (agente) | Tool / função | SKU / engine | Calls típicas | Custo USD (granular) | Custo BRL (~) |
|---|----------------------|---------------|--------------|---------------|----------------------|---------------|
| 1 | **A3a** Competitor Intel | `descobrir_concorrentes_bairro` | `searchapi_google_maps` | 1× | 0,004 | 0,022 |
| 2 | **A3a** | `reviews_concorrente` / `buscar_reviews_academia` | `searchapi_google_maps_reviews` | até **6×** | 0,004 × N | 0,022 × N |
| 3 | **A3a** | `pesquisar_horarios_pico` | `searchapi_popular_times` | até **6×** | 0,004 × N | 0,022 × N |
| 4 | **A3a** | `competidor_ig` / Instagram profile | `searchapi_instagram_profile` | até **6×** | 0,004 × N | 0,022 × N |
| 5 | **A1 / A4 / listings** | `listing_cascata` / planos / light | `searchapi_google_light` | **N×** (variável) | 0,004 × N | 0,022 × N |

**Faixa agregada SearchAPI (diagrama):** 15–25 créditos → **US$ 0,06–0,10** (~R$ 0,32–0,54) **só SearchAPI**, por 1 relatório.  
Isso **não** inclui Gemini (LLM) nem Places fallback.

### 2.2 Outras calls trackeadas no código (`track_api_call`)

| Responsável | Tool name (tracker) | SKU | Onde |
|-------------|---------------------|-----|------|
| A3a | `descobrir_concorrentes_bairro` | `places_search_new` (fallback) | `competitor_tools.py` |
| A3a | `buscar_academias_nearby` | `places_search_new` | idem |
| A3a | `buscar_rede_geofenced` | `places_search_new` | idem |
| A3a | `planos_precos` | `searchapi_google_light` | idem |
| A1 / maps | `geocode_google` | `geocoding` | `maps_tools.py` |
| A1 | `buscar_pontos_comerciais` | `places_search_new` | idem |
| A1 | `buscar_imoveis_texto` | `places_search_new` | idem |
| A3/maps | `obter_detalhes_contato` | `places_details_new` | idem |
| A3/maps | `obter_atributos_place` | `places_details_new` | idem |
| A2? | `places_aggregate` | `places_aggregate` | `places_aggregate_tools.py` |
| A3a | `searchapi_popular_times` | `searchapi_popular_times` | `popular_times_tool.py` |
| A3a | `competidor_ig` | `searchapi_instagram_profile` | `competidor_intel_cache.py` |
| A1 | `listing_cascata` | `searchapi_google_light` | `listing_cascata.py` |

**Colunas pedidas →** ver CSV `catalogo_chamadas_agente_tool.csv` (`responsavel_agente`, `tool_name`, `api_sku`, `custo_usd_por_call`, `custo_brl_por_call`, `multiplicidade`).

---

## 3. Por que há “muitas chamadas” da mesma tool

### Causa raiz (não é bug — é loop de enriquecimento)

```
1× Maps descobrir → lista de academias
        ↓
top-N = min(encontrados, MAX_ENRIQUECIMENTO=6)
        ↓
para cada um dos N:
   1× reviews
   1× popular_times (pico)
   1× Instagram (se houver handle)
   (+ Places details atributos, opcional)
        ↓
+ N× google_light (planos / listings) conforme cascata
```

| Sintoma na fatura | Motivo técnico | Onde |
|-------------------|----------------|------|
| Reviews 4–6× | 1 call **por** concorrente enriquecido | `buscar_reviews_academia` no loop `_processar_um` |
| Pico 4–6× | 1 call **por** place_id | `pesquisar_horarios_pico` |
| IG 0–6× | 1 call se username resolvido | `competidor_ig` |
| Listings “Nx” | cascata de queries bairro-scoped | `listing_cascata.py` |
| Mesma tool “de novo” em re-run | cache miss / TTL / `relatorio_id` novo | caches locais + SearchAPI |

### Plano de solução (reduzir N× sem matar qualidade)

| Prio | Ação | Efeito | Risco |
|------|------|--------|-------|
| P0 | Expor `MAX_ENRIQUECIMENTO` no admin + default **4** em degustação / **6** em relatório pago | −33% reviews/pico/IG no caminho barato | Menos quotes no PDF |
| P0 | Cache cross-relatório por `place_id` (reviews + pico + IG) com TTL 7–30d já parcial — **auditar hit-rate** e logar `cache_hit` no `relatorio_api_calls` | Zera call em re-análise do mesmo bairro | Dado “velho” |
| P1 | Enriquecer IG/pico **só top-3 por avaliações**; reviews nos 6 | Corta SKUs caras em engajamento | Pico/IG incompletos |
| P1 | Deduplicar `planos_precos` / `google_light` quando o mesmo query já rodou no run | Corta Nx listings | Baixo |
| P2 | UI Custos: drill-down por `tool_name` + `num_calls` (hoje o export CSV da página **não tem** granularidade) | Transparência | Só front |
| P2 | Relatório “mesmo bairro, 2 runs”: comparar `num_calls` vs `custo_brl` vs cache | Prova o modelo | Operacional |

---

## 4. Mesma localidade: por que score e custo divergem

**São métricas de naturezas diferentes.** Correlacionar sem normalizar é erro.

| Dimensão | Score (`score_bairro` / `score_top1_candidato`) | Custo (`custo_brl`) |
|----------|-----------------------------------------------|---------------------|
| O que mede | Atratividade / viabilidade / competitividade do lugar | Quanto **pagamos** de API+LLM para montar o relatório |
| Sobe quando | Renda ok, saturação gerenciável, candidato forte | Muitos concorrentes no top-N, cache miss, Pro tokens, retries |
| Cai quando | Parque saturado, demografia fraca | Cache hit, poucos places, Flash, enrich N baixo |

### Cenários típicos (mesmo bairro)

| Cenário | Score | Custo | Por quê |
|---------|-------|-------|---------|
| A — 1º run frio, 20 concorrentes, enrich 6 | Médio/alto | **Alto** | 1+6+6+6 SearchAPI + LLM cheio |
| B — 2º run quente (cache place_id) | ≈ igual | **Baixo** | Calls de reviews/pico/IG puladas |
| C — Parque pequeno (3 academias) | Pode ser **alto** (oceano) | **Baixo** | Nenrich=3 ≪ 6 |
| D — Parque denso + LLM Pro A6/A9 | Médio | **Muito alto** | SearchAPI + Vertex dominam |
| E — Score “ruim” mas enrich completo | **Baixo** | **Alto** | Mercado fraco ≠ barato de analisar |

**Conclusão:** divergência score×custo **no mesmo bairro** em runs diferentes quase sempre = **cache / N enrich / tokens LLM / depth listings**, não “bug de score”.  
Divergência **entre** dois bairros na mesma cidade = misturar qualidade de mercado com carga de descoberta.

### Como medir de verdade (bloqueado até ter o CSV certo)

Export necessário (1 linha por relatório + child rows por call):

```
relatorio_id, cidade, bairro, score_bairro, score_top1_candidato, custo_brl_total
relatorio_id, tool_name, api_sku, num_calls, custo_brl, cache_hit?
```

A tela `/custos` hoje exporta só: Data, Cidade, Bairro, Status, Tempo, Tokens, Custo — **sem score e sem linhas por tool**.

---

## 5. Plano de ação (checklist)

### Fase A — Dados (esta semana)

- [ ] Exportar de produção `relatorio_api_calls` ⋂ `relatorios` (ou estender `exportarCSV` em `CustosPage.tsx`)
- [ ] Incluir colunas: `responsavel_agente`, `tool_name`, `api_sku`, `num_calls`, `custo_brl`, `score_bairro`, `score_top1`
- [ ] Rodar pareamento “mesmo `cidade+bairro`”: desvio-padrão de `custo_brl` e de scores

### Fase B — Custo SearchAPI (próximo sprint)

- [ ] Baixar `MAX_ENRIQUECIMENTO` default em modo degustação / landing
- [ ] Logar `cache_hit` no tracker
- [ ] Capar IG+pico a top-3; reviews até 6 (ou env separado `MAX_REVIEWS_ENRIQ`)

### Fase C — Score × custo (produto)

- [ ] Dashboard: scatter plot score vs custo_brl (colorir por cidade)
- [ ] Alerta: mesmo bairro com custo >2× mediana → flag “cache miss / enrich cheio”
- [ ] Não usar custo como proxy de qualidade do bairro na UI

### Fase D — Campanha Flow (arquivo enviado)

- [ ] Tratar CSV só como lead-gen (DDD/cidade)
- [ ] Se a campanha disparar relatórios em lote, usar `campanha-flow_33fe_custos_projetados.csv` como **teto orçamentário SearchAPI** (~US$ 0,06–0,10 × nº de cidades únicas), não como fatura

---

## 6. Impacto estimado (só SearchAPI A3 enrich)

| Mudança | Calls por relatório | Economia vs default 6 |
|---------|---------------------|------------------------|
| Default hoje (1+6+6+6) | ~19 + Nx light | baseline |
| MAX=4 | ~13 + Nx | ~−30% SearchAPI A3 |
| MAX=4 + pico/IG só top-3 | ~1+4+3+3 = 11 + Nx | ~−40% |
| Cache hit 100% no re-run | ~1 (só descobrir) | ~−90% no 2º run |

LLM (Gemini) continua o maior bolso em muitos runs — ver `AUDITORIA_CUSTO_LLM_PIPELINE.md`.

---

## 7. Aceite

- [ ] Catálogo granular versionado no repo  
- [ ] Plano de solução N× tools documentado com owner técnico (A3a / `competitor_tools`)  
- [ ] Divergência score×custo explicada sem misturar métricas  
- [ ] Export de custos reais (com score + por chamada) solicitado / especificado  
- [ ] CSV campanha enriquecido só como **projeção**, rotulado  

---

## 8. Referências de código

- `tools/pricing.py` — `SEARCHAPI_USD_PER_SEARCH`, `PLACES_API_USD_PER_CALL`  
- `tools/api_cost_tracker.py` — grava `tool_name`, `api_sku`, `num_calls`, `custo_brl`  
- `tools/competitor_tools.py` — `MAX_ENRIQUECIMENTO` (default 6), loop `_processar_um`  
- `frontend/src/routes/CustosPage.tsx` — export CSV agregado (lacuna granular + score)  
- `docs/arquitetura/AUDITORIA_CUSTO_LLM_PIPELINE.md` — Vertex/Gemini  
