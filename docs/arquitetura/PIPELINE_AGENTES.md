# Pipeline GymSite Intelligence — Agentes, Scripts e Relatório

> Mapa de referência do pipeline de viabilidade A0→A9: árvore de execução, script
> interno de cada agente, e como cada um alimenta as seções do relatório.
> Orquestrador: [`gymsite_intelligence/agent.py`](../../gymsite_intelligence/agent.py).
> Gerado a partir de leitura direta dos `agents/*.py` (jun/2026).

---

## 1. Árvore de execução (pipeline)

`SequentialAgent` **GymSitePipeline**:

```
GymSitePipeline (Sequential)
│
├─ A0  ContextBuilder          LLM      →market_context
├─ A1  GeoScout                det.     →candidatos_geoscout(_pronto) listing+MRLR
│
├─ ParallelAnalysis (Parallel — rodam JUNTOS)
│   ├─ A2  DemoAnalyst         det.     →analise_demografica
│   ├─ CompetitorPipeline (Sequential)
│   │    ├─ A3a CompetitorSearch    det.   →concorrentes_brutos
│   │    └─ A3b CompetitorAnalysis  det.   →inteligencia_competitiva + oferta_concorrentes  ← funde A3c (jun/2026)
│   │       (A3c CompetitorMapper — FUNDIDO no A3b, morto)
│   └─ A4  FinancialEstimator  det.     →analise_financeira(_pronto)
│
├─ A6  ReportConsolidator      LLM      →relatorio_md
└─ A9  PositioningStrategist   det.     →relatorio_posicionamento(_md)
```

**Fora do pipeline de viabilidade** (definidos, não wired no fluxo principal):

| Agente | Arquivo | Papel | Por que fora |
|---|---|---|---|
| A5 ContactHunter | `agents/a5_contact_hunter.py` | decisor + canal + script | contato = prospecção, não viabilidade |
| A7 MarketResearch | `agents/a7_market_research.py` | Google Search Grounding on-demand | chamado sob demanda, não no fluxo fixo |
| A8 Validador | `agents/a8_validator.py` | validação cruzada pós-A6 | classe standalone, não é agente ADK |
| A3 CompetitorIntel | `agents/a3_competitor_intel.py` | monólito antigo | **substituído** por A3a/A3b/A3c |

**Determinismo (regra VEC — LLM veste, não produz dado):** A1, A2, A3a, A3b, A4, A5, A9 = `BaseAgent` sem LLM. **LLM restante:** A0 (com override determinístico dos números — ver §6), A6 (narrador guardrail parcial), A7 (web grounding, justificado). A6/A9 narram via `narrador_claude` (Claude headless + guardrail). A3b determinizado + A0 com override de número CNPJ (jun/2026) — **nenhum agente produz número sem guardrail**, exceto a cobertura parcial do A6.

---

## 2. Script interno por agente

### A0 — ContextBuilder · [`a0_context_builder.py`](../../agents/a0_context_builder.py)
- **Classe / model:** `Agent` (LLM) · gemini-3.6-flash (NVIDIA via `PIPELINE_LLM_PROVIDER`)
- **Tools:** `carregar_market_bundle`, `dados_parque_cnpj_para_a0`, `fatos_competicao_local` (Deep Research/Kimi removidos — Act-on bundle-only)
- **Lê:** `input_params` (cidade/bairro/uf) · **Escreve:** `market_context`, `a0_tool_snapshots` (payloads completos das tools)
- **Fonte:** market_bundle (qualitativo) · CNPJ RFB/Supabase + CNO (quantitativo) · OSM (`fatos_competicao_local`)
- **Faz:** consolida contexto de mercado (ticket, tendência, redes, parque CNPJ/CNO). **Aqui mora a árvore 2×2 do parque** (`dados_parque_cnpj_para_a0` → `arvore_2x2_parque`).
- **Slim prompt (ago/2026):** `after_tool_callback` `_a0_after_tool_slim` — grava tool response **completa** em `a0_tool_snapshots` e devolve versão slim (`tools/context_slimmer.py`) ao LLM. State/`market_context` final permanece completo (A4/A6 leem daqui). Loop/cap: `before_model_callback` (máx. 12 turns / tool repetida 3×) + `on_model_error_callback` fail-soft em estouro de contexto (NVIDIA 131k).
- **Callback:** `after_agent_callback` `_a0_override_cnpj_numeros` — preferência por snapshot completo; fallback re-roda a tool e **sobrescreve todo número CNPJ** no `market_context` + pluga `arvore_2x2_parque`. Número = tool/banco, nunca LLM.
- **Relatório:** §5 (contexto mercado), §8 (Novos Entrantes CNPJ).

### A1 — GeoScout · [`a1_geoscout.py`](../../agents/a1_geoscout.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Pipeline:** `buscar_candidatos_listing_mrlr` → `listing_cascata` SearchAPI → gate bairro/cidade/UF + área do anúncio → score por distância → aluguel MRLR
- **Macro POI morta:** `analisar_pontos_comerciais_completo` não roda no caminho A1 (evidência Pirapora: sinal indireto, área 600 por tipo, contaminação Diadema)
- **Lê:** `input_params`, `market_context` · **Escreve:** `candidatos_geoscout_pronto`, `candidatos_geoscout` (`status=ok|ok_vazio`)
- **Aluguel:** `price_raw` é display; decisão = MRLR por área real do listing, com carimbo
- **Relatório:** Top3 no A6 usa 35% geo + 65% payback estimado; lista vazia permanece honesta

### A2 — DemoAnalyst · [`a2_demo_analyst.py`](../../agents/a2_demo_analyst.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analise_demografica_completa` + perfil sexo/idade + densidade setor
- **Lê:** `input_params`, `market_context` · **Escreve:** `analise_demografica` (+ insights)
- **Fonte:** IBGE Censo 2022 por setor · **polígono IBGE bairro** quando `resolver_bairro_poligono` hit (`demografia_setor_poligono` + `perfil_sexo_idade_poligono`); senão raio 1,5 km + fill `pop_alvo` · CKAN/renda · nominatim (fallback)
- **Faz:** renda, público 18-45, score demográfico, perfil sexo, densidade.
- **Relatório:** §2 (Scores), §13 (Demanda Futura T+24).

### A3a — CompetitorSearch · [`a3a_competitor_search.py`](../../agents/a3a_competitor_search.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analisar_concorrentes_a3a_completo`
- **Lê:** `input_params`, `market_context` · **Escreve:** `concorrentes_brutos`
- **Fonte:** **SearchAPI `engine=google_maps`** (primário, 4× barato; Places fallback) + **SearchAPI `engine=google_maps_reviews`** (`sort_by=lowest_rating`, cache 7d) → card determinístico `_processar_review_card` (`dores_detectadas`, `sentimento`, `servicos_mencionados`) + **refino opcional** Gemini Flash batch (`categoria_dor` taxonomia fechada; fallback substring se falha)
- **Gate espacial (Spec C):** inclusão = **point-in-polygon** no polígono IBGE do bairro se resolvido; senão **R=1000 m** do centróide (`RAIO_CONCORRENCIA_CANONICO_M`). Bairro na query = só recall.
- **Faz:** busca + gate `_eh_academia_tradicional` + reviews SearchAPI + enriquecimento.
- **⚠️ Nosso fix:** o gate agora entende types PT do SearchAPI (era só EN → cortava academia real). Ver [`tools/competitor_tools.py`](../../tools/competitor_tools.py).
- **Relatório:** §6.1 (por bairro), §11 (Distribuição Geográfica).

### A3b — CompetitorAnalysis · [`a3b_competitor_analysis.py`](../../agents/a3b_competitor_analysis.py) — **determinizado + FUNDIDO com A3c (jun/2026)**
- **Classe / model:** `BaseAgent` (determinístico) · — *(era `Agent` gemini-3.6-flash)*
- **Macros:** `analisar_concorrentes_completo` (agrega) + `mapear_oferta_competidores_completo` (oferta site+IG via SearchAPI)
- **Lê:** `concorrentes_brutos`, `market_context`, `input_params` · **Escreve:** `inteligencia_competitiva` **+ `oferta_concorrentes`**
- **Faz:** (1) macro calcula gaps/dores/saturação/`score_concorrencia`; (2) grava envelope verbatim + filtra bairro/tipo/CLOSED (`_filtrar_envelope`); (3) sintetiza `posicionamento_recomendado`/`resumo_executivo` por template; (4) **FUSÃO A3c:** roda a oferta e **mescla as modalidades em `servicos_oferecidos` de cada concorrente** (`_mesclar_servicos_na_oferta`).
- **Por que fundiu A3c:** A9 `_gaps_reais` lê `servicos_oferecidos`/`servicos_ig`/`planos_precos` POR concorrente. Sem o site-scrape mesclado, serviço que só aparece no site (não no IG/search) virava **gap falso** → ERRC mandava CRIAR algo que o concorrente já tem → relatório furado (bug Tio Sam). Validado Cocó: merge fechou 6 gaps falsos (spinning/yoga/recovery/funcional/dança/estética que o Parque Esportes já oferece).
- **Por que determinizou:** o LlmAgent só re-emitia o output da macro, dropava campos e crashava (`MALFORMED_FUNCTION_CALL`/OUT=0). **Tradeoff:** tradução de reviews EN→PT saiu.
- **Relatório:** §6 (Inteligência Competitiva), §9 (Counter-Programming), §10/oferta (mensalidades/serviços), e corrige o GAP da ERRC do A9 (§7).

### A3c — CompetitorMapper · [`a3c_competitor_mapper.py`](../../agents/a3c_competitor_mapper.py) — **FUNDIDO NO A3b (morto)**
> A função do A3c (mapear oferta) virou passo do A3b determinizado. Macro `mapear_oferta_competidores_completo` roda dentro do A3b; `oferta_concorrentes` é escrito pelo **A3b**, não pelo A3c. Arquivo legado no repo — **não wired** em [`agent.py`](../../gymsite_intelligence/agent.py). Remover numa limpeza.

### A4 — FinancialEstimator · [`a4_financial_estimator.py`](../../agents/a4_financial_estimator.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analise_financeira_a4_completo` (async)
- **Lê:** `input_params` (area/tipo/tamanho/gênero), `market_context`, `candidatos_geoscout_pronto` (lat/lng top 1), `concorrentes_brutos` / inteligência (matriz veto) · **Escreve:** `analise_financeira_pronto`, `analise_financeira`
- **Fonte:** MRLR (aluguel Tier 0) — viabilidade determinística; modelo recomendado pode ser **vetado** pela matriz (Armadilha → ≠ Premium genérico)
- **Faz:** 3 cenários (low/mid/premium): CAPEX, OPEX, payback, margem, modelo recomendado, score.
- **Relatório:** §10 (Viabilidade Financeira a/b/c/d).
- **Aluguel:** continua **só MRLR** — matriz não troca fonte de aluguel.

### A5 — ContactHunter · [`a5_contact_hunter.py`](../../agents/a5_contact_hunter.py) — *fora do pipeline*
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `gerar_contato_decisor_completo` (via `_StateShim`)
- **Lê:** session.state inteiro · **Escreve:** `contato_decisor`
- **Fonte:** Google Maps (proprietário/gerente) + parsing de site + CNPJ (administrador) + Apollo (prospecção)
- **Faz:** decisor #1 + canal + script de abordagem.

### A6 — ReportConsolidator · [`a6_report_consolidator.py`](../../agents/a6_report_consolidator.py)
- **Classe / model:** `Agent` (LLM) · gemini-3.6-flash · **tools=[]** (só narra)
- **Lê:** `market_context`, `analise_demografica`, `inteligencia_competitiva`, `oferta_concorrentes`, `analise_financeira_pronto`, `candidatos_geoscout_pronto`, `contato_decisor` · **Escreve:** `relatorio_md`
- **Callbacks:**
  - `before_agent` `_a6_precompute_callback` → pré-computa `bairros_alternativos_pronto`, `entrantes_cnpj_pronto`, `obras_cno_pronto`, **`fluxo_pedestre`** (jul/2026 — ver §8) (seções **PRÉ-COMPUTADAS** = determinísticas, LLM usa literal)
  - `before_model` injeta bairros alternativos, crowdsource estruturado (`input_params.bairros_indicados`), ofertas, entrantes e aluguel **MRLR**; não injeta preço de portal/Grounding
  - `after_agent` `_a6_after_agent_callback` → parseia markdown, persiste JSON local + Supabase, telemetria
- **Fonte:** CNO (obras) + CNPJ entrantes 90d (precompute) + mapas hardcoded `BAIRROS_ALTERNATIVOS`/`REGIAO_METROPOLITANA` + OSMnx/Overpass (fluxo pedestre)
- **Faz:** monta relatório + Top3 determinístico (`candidato_viabilidade_rank`: 35% geo + 65% payback A4 mid/MRLR). O LLM copia a ordem pronta e não aplica tie-breaker de POI.
- **Relatório:** §1, Top3 enriched (carimbo MRLR + payback estimado), §16, `fluxo_pedestre`.

### A7 — MarketResearch · [`a7_market_research.py`](../../agents/a7_market_research.py) — *auxiliar (chat), NÃO pipeline*
- **Classe / model:** `Agent` (LLM) · gemini-3.6-flash
- **Tool:** `google_search` (Grounding oficial)
- **Lê:** — · **Escreve:** `market_research_result`
- **Fonte:** Google Search Grounding (URLs reais, tempo real)
- **Consumidor (VIVO):** chat landing + consultor on-demand. **NÃO** roda no pipeline de relatório.
- **Faz (slot gaps):** crowdsource §14 qualitativo, pico narrativo residual, dado web pontual com carimbo.
- **NÃO faz:** aluguel viabilidade (→ **A4 MRLR**), concorrência (→ **A3a**), demografia (→ **A2/IBGE**).

### A8 — Validador Cruzado · [`a8_validator.py`](../../agents/a8_validator.py) — *pós-A6, não-ADK*
- **Classe:** `A8ValidadorCruzado` (classe Python standalone, `async def validar()`)
- **Lê:** `relatorio_markdown` + `state_json` + `relatorio` (dict) · **Retorna:** `alertas`, `score_validacao`, `status_validacao`, `claims_verificadas`
- **Fonte:** Kimi Search (corroboração opcional)
- **Faz:** coerência financeira/demográfica/competitiva; alertas globais.
- **Relatório:** §15 (Alertas Globais).

### A9 — PositioningStrategist · [`a9_positioning_strategist.py`](../../agents/a9_positioning_strategist.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `_errc_deterministica(state)` + `attach_matriz_demo_saturacao` (`tools/matriz_demo_saturacao.py`) + `attach_absorcao_margem_fresca` (`tools/absorcao_margem_fresca.py`)
- **Lê:** `market_context`, `candidatos_geoscout`, `analise_demografica`, `inteligencia_competitiva`, `oferta_concorrentes`, `analise_financeira`, `contato_decisor`, `relatorio_md`, `demografia_bairro`, `concorrentes_brutos` · **Escreve:** `relatorio_posicionamento_md`, `relatorio_posicionamento` (incl. `matriz_demo_saturacao`, `absorcao_margem_fresca`)
- **Absorção (W2a/W2a.1):** teto (`área×matr/m²`) × capacidade parque (N×tier×área_proxy) × **pool etário** (estoque form/resto × interesse × pen academia) → rótulo `fresco|misto|roubo` no pool **primário**. Números = tool. Spec: `docs/superpowers/specs/2026-08-07-absorcao-margem-fresca-design.md` + `2026-08-07-pool-etario-absorcao-design.md`.
- **Voronoi smoke (W2.1):** `voronoi_smoke` (clássico+ponderado) em paralelo; nota experimental no PDF/app; **não** muda rótulo/`base_espacial`. Spec: `2026-08-07-voronoi-smoke-design.md`.
- **Veto absorção:** `rotulo==roubo` derruba `OCEANO_AZUL` → `TRANSICAO` (`aplicar_veto_oceano_por_roubo`); não piora `VERMELHO`/`TRANSICAO`.
- **UI app:** `AbsorcaoMargemFrescaCard` no viewer (`posicionamento_estrategico.absorcao_margem_fresca`) — leitura executiva, espelho PDF.
- **Callback:** `after_agent` `_a9_after_agent_callback` → override de veredito (headroom renda IBGE 2022) + **matriz demografia×saturação** (quadrante → modelo) + absorção + veto roubo + síntese narrada opcional (Claude headless) + persiste Supabase

- **Fonte:** IBGE Censo 2022 (headroom renda × ticket) + N/mix no polígono Spec C — determinístico
- **Faz:** framework ERRC + GAPs + ticket recomendado + veredito (OCEANO_AZUL/TRANSICAO/VERMELHO) + quadrante (Oceano/Armadilha/Guerra/Deserto). **Armadilha vence** headroom Oceano se ≥2 Premium no polígono (`matriz_override`).
- **Relatório:** §7 (Posicionamento Recomendado) + seção PDF **Modelo de Negócio Adequado**.

### A3 — CompetitorIntel · [`a3_competitor_intel.py`](../../agents/a3_competitor_intel.py) — **LEGADO**
- `Agent` (LLM) gemini-3.6-flash, 8 tools soltas. Monólito que estourava AFC=10 (`MALFORMED_FUNCTION_CALL`). **Substituído** por A3a/A3b/A3c. Mantido só p/ referência.

---

## 3. Árvore do relatório acoplada aos agentes

Seções na ordem do doc final (montado pelo A6). `PRÉ` = pré-computada (determinística, injetada por código).

| # | Seção | Agente | Tipo |
|---|---|---|---|
| 1 | 🎯 Resumo Executivo | A6 | narrado (guardrail) |
| 2 | 📊 Scores Regionais | A1+A2 | dado |
| 3 | 🏆 Top 3 Candidatos | A1 | dado |
| 4 | 🏗️ Checklist Diligência Imóvel | A1/A6 | template |
| 5 | 🔍 Cobertura Deep Research (A0) | A0 | dado |
| 6 | 🥊 Inteligência Competitiva (concorrente×concorrente) | A3b (+A3a) | dado + texto template |
| 6.1 | 📍 \<Bairro\> (N academias) | A3a | PRÉ |
| 7 | 💡 Posicionamento Recomendado (ERRC) | A9 | det.+narrado |
| 8 | 🏢 Novos Entrantes de Mercado (CNPJ) | A0/CNPJ | **PRÉ** ← árvore 2×2 |
| 9 | 🕐 Counter-Programming (horário pico) | A3b | PRÉ |
| 10 | 💰 Viabilidade Financeira — 3 Cenários | A4 | det. |
| 10a | 📊 Demanda — Matrículas vs Capacidade | A4 | det. |
| 10b | 💵 Receita & Custos Mensais | A4 | det. |
| 10c | 🏗️ Investimento & Retorno | A4 | det. |
| 10d | ⚠️ Sensibilidade (3 stress tests) | A4 | det. |
| 11 | 📍 Distribuição Geográfica Concorrentes | A3a | PRÉ |
| 12 | 🗺️ Bairros Alternativos | A1/A6 | PRÉ |
| 13 | 🏗️ Demanda Futura — Novos Moradores (T+24) | A2 | dado |
| 14 | 📣 Demanda Social (Crowdsource) | A7 | dado |
| 15 | ⚠️ Alertas Globais | A8 | dado |
| 16 | 📌 Decisão Recomendada (veredito) | A6 | narrado (guardrail) |
| — | 🚶 Fluxo Pedestre (space syntax) | A1 (badge) + A6 (bloco) | det. OSM — ver §8 |

---

## 4. Fluxo de dados (state — quem escreve / quem lê)

> Fonte travada: [`tools/pipeline_deps.py`](../../tools/pipeline_deps.py) · gate `tests/test_pipeline_deps.py` · cartões reverso [`.superpowers/sdd/pipeline-deps-reverse.md`](../.superpowers/sdd/pipeline-deps-reverse.md)

| Chave de state | Escrito por | Lido por |
|---|---|---|
| `input_params` | entrypoint | A0, A1, A2, A3a, A3b, A4, A6, A9 |
| `demanda_futura` | entrypoint (`api.py` enrichment) | A6, A9 |
| `market_context` | A0 | A1, A2, A3a, A3b, A4, A6, A9 |
| `a0_tool_snapshots` | A0 (`after_tool`) | A0 after_agent (CNPJ/CNO completo) |
| `candidatos_geoscout(_pronto)` | A1 | A4, A6 (ambas as chaves; `_pronto` preferido) |
| `analise_demografica` | A2 | A6 |
| `concorrentes_brutos` | A3a | A3b, A6, A9 |
| `inteligencia_competitiva` | A3b | A6, A9 |
| `oferta_concorrentes` | **A3b** (fundiu A3c) | A6, A9 |
| `flujo_pedestre` | A6 precompute (+ `fluxo_*` nos candidatos via A1) | API `GET /flujo-pedestre`, front |
| `analise_financeira_pronto` | A4 | A6 (números) |
| `analise_financeira` | A4 | A9 (alertas fiscais / piso) |
| `demografia_bairro` | A6 (bridge after_agent) | A9 (Brilliant Basics público) |
| `cobertura_competitiva` | A6 (B1 pós–cross_check) | A9 (mapa_servicos + gaps_validados B2) |
| `zoneamento` | A6 (cascata ZEUS: CKAN → OSM proxy → indisponível) | PDF Weasy § zoneamento; resumo A6 |
| `contato_decisor` | A5 [fora] | A6, A9 (opcional — tratam ausência) |
| `relatorio_md` | A6 | A9, A8 |
| `relatorio_posicionamento(_md)` | A9 | persistência / PDF |

**Padrão:** cada A_n lê o output do A_(n-1); A0 (`market_context`) e `input_params` são lidos por quase todos. A6 e A9 são os **agregadores**. Loop reverso (contrato→consumidor→entradas): A9→A6→A4→A3b→A3a→A2→A1→A0.

---

## 5. Acoplamento ao trabalho recente (jun/2026)

- **Gate A3a (types PT SearchAPI):** consertado em `tools/competitor_tools.py` — alimenta §6/§11. Antes sub-contava concorrente.
- **Raio canônico concorrência (jul/2026):** `RAIO_CONCORRENCIA_CANONICO_M=1000` — inclusão por distância ao centróide + tipo/status; bairro só na query de recall. Ver `conferencia-fontes-pipeline.md` §9.
- **Árvore CNPJ oferta (joio/trigo + baixas):** `tools/cnpj_fitness_tools.py` + `tools/cnpj_oferta_janelas.py` / `cnpj_oferta_metricas.py` — parque limpo gated; **ativos + baixadas** (`situacao 02/08`); janelas 90d + Q civil fechado com `as_of`; redes por `cnpj_basico`. Ingest: `rfb_cnpj_fitness_loader.py --from-json` (JSON ativo+baixada) ou ZIP `--include-baixadas`. Spec: `docs/superpowers/specs/2026-08-05-cnpj-json-ingest-baixadas-design.md`. Aluguel viabilidade continua **só MRLR (A4)**.
- **Narrador Claude headless + guardrail decimal:** `tools/narrador_claude.py` — usado por A6 (§1/§16) e A9 (§7). LLM só veste o dado determinístico.
- **A6 vs A9 = UM PDF, não dois.** `gerar_pdf_weasy(model)` ([api.py](../../api.py)) monta um único PDF de um `model` ESTRUTURADO (saíram do markdown-do-LLM de propósito). A6 fornece as seções de viabilidade; A9 fornece a seção ERRC/posicionamento (`model.posicionamento_estrategico`) + veredito. Complementares, providers de seções diferentes. Os `*_md` (relatorio_md, relatorio_posicionamento_md) são secundários (preview/UI), NÃO a fonte do PDF.
- **Fusão A3b+A3c (jun/2026):** A3b agora emite `oferta_concorrentes` + mescla serviços por concorrente → corrige gap falso da ERRC (A9). A3c morto.
- **Determinização A4/A9/A3a/A3b:** `BaseAgent` sem LLM — números reproduzíveis run-a-run. **A3b** (jun/2026): era LlmAgent-eco que crashava (`MALFORMED_FUNCTION_CALL`); agora roda a macro + grava verbatim + filtro inline + textos por template.
- **Fluxo pedestre (jul/2026):** `tools/space_syntax.py` + hook A1 top-3 + bloco A6 — **determinístico**, mas **fora da hierarquia SearchAPI** e com risco de latência (§8). Spec: [`agents/specs/SPEC_FLUXO_PEDESTRE.md`](../../agents/specs/SPEC_FLUXO_PEDESTRE.md).

## 6. Auditoria — agentes que AINDA usam LLM (jun/2026)

| Agente / passo | LLM justificado? | Risco | Ação |
|---|---|---|---|
| **A7** MarketResearch | ✅ sim (Google Search Grounding = web em tempo real) | baixo | manter |
| **A6** ReportConsolidator | parcial (é redator) | 🟡 médio | guardrail cobre só o resumo executivo; estender p/ todo número da saída ∈ state |
| **A0** ContextBuilder | só o lado Deep Research/qualitativo | ✅ fechado | LLM mantém a prosa; `_a0_override_cnpj_numeros` sobrescreve todo número CNPJ com tool (banco). Travado em `tools/test_a0_override.py`. |
| **A3a** (sub-passo reviews) | ✅ fechado | baixo | SearchAPI `google_maps_reviews` + `topics[]` + card det. + `temas_insatisfacao`. Gemini **off** default (`CLASSIFICAR_DORES_GEMINI=1` opt-in). |
| **A3a** (sub-passo planos) | 🟡 parcial | médio | Tier0 **site HTML** (`planos_site_fetcher`, Smart Fit `plans[]`) → Tier1 SearchAPI `google_light`+Gemini extract → Tier2 grounding. Balcão ≠ Wellhub. |
| ~~A3b agent~~ | — | — | ✅ determinizado + fundiu A3c |
| ~~A3c~~ | — | — | ✅ morto (lógica no A3b) |

**Pendência da determinização:** **A6** (guardrail completo) + **sub-passo planos A3b** (Gemini extrai preço de snippet SearchAPI). Reviews A3a: fetch+card = SearchAPI determinístico; Gemini = refino opcional. A0 fechado via override (jun/2026); A7 fica LLM por desenho.

---

## 7. Hierarquia de fontes — SearchAPI primário (regra VEC)

> **Regra mestra:** ler junto com [`.agent/rules/pipeline-fontes-deterministicas.md`](../../.agent/rules/pipeline-fontes-deterministicas.md) antes de qualquer mudança no pipeline.

| Camada | Fonte primária | Fallback | Proibido no caminho crítico |
|---|---|---|---|
| Concorrentes Maps | SearchAPI `engine=google_maps` · **polígono IBGE bairro** (Spec C) ou **R=1000 m** fallback · gate tipo/status | Places API (`COMPETIDOR_MAPS_BACKEND=places`) | Scraping Maps; gate string bairro; LLM inventando N |
| Reviews concorrente | SearchAPI `engine=google_maps_reviews` (`sort_by=lowest_rating`) → card `_processar_review_card` | Places Details reviews | LLM como única classificação |
| Temas agregados reviews | SearchAPI `topics[]` → `temas_insatisfacao` + gap A3b | — | Gemini como classificação primária |
| Oferta site/IG | httpx + BS4 + SearchAPI `instagram_profile` | — | Playwright, Outscraper |
| Imóveis/listings | SearchAPI cascata bairro (`listing_cascata.py`) | Playwright OLX/ImovelWeb (`LISTINGS_PLAYWRIGHT`) | Listing como fonte de **aluguel** (aluguel = MRLR Tier 0) |
| Aluguel viabilidade | MRLR determinístico (`aluguel_mrlr.py`) | — | Preço de anúncio raspado |
| Demografia | IBGE Censo 2022 / BQ | CKAN 2010, nominatim | LLM inventando número |
| Parque CNPJ/CNO | RFB/Supabase determinístico | — | LLM (A0 override fecha) |
| Fluxo pedestre | OSMnx malha + Overpass POI | **nenhum grid sintético** | Score fake / fallback heurístico |
| Zoneamento (ZEUS) | CKAN municipal (`zoneamento_municipio`) | OSM `landuse` (proxy → `INDIVIDUALIZAR`) | Assumir `PERMISSIVO` sem malha; omitir bloco quando indisponível |

**Princípio:** dado numérico = **tool determinística** ou API paga estruturada (SearchAPI). LLM **narra** (A6/A9) ou **refina** texto já coletado (ex.: `categoria_dor` pós-SearchAPI; planos A3b). Fetch + card de review = SearchAPI + código, não LLM.

**ZEUS (ago/2026):** sem adapter CKAN → `proxy_osm` (rótulo `INDIVIDUALIZAR` + alerta prefeitura) ou `indisponivel` (`compatibilidade=None`). PERMISSIVO só com malha oficial (ex.: Fortaleza fora de zona especial = uso geral). Código: `tools/zoneamento_tools.py`.

---

## 8. Fluxo pedestre (jul/2026) — acoplamento e dívidas

**Spec:** [`agents/specs/SPEC_FLUXO_PEDESTRE.md`](../../agents/specs/SPEC_FLUXO_PEDESTRE.md) · **Código:** `tools/space_syntax.py`, `tools/fluxo_pedestre_tools.py`, `tools/vias_geometry_tools.py`, cache `spatial_flow_cache`.

| Onde roda | O quê | Input POI | Latência típica |
|---|---|---|---|
| **A1** `anchoring_tools.py` L421-429 | `enrich_candidato_fluxo` nos **top 3** | Overpass (não reusa concorrentes A3a ainda) | **9+ min** cold OSMnx × até 3 coords distintas |
| **A6** `_a6_precompute_callback` | `build_fluxo_pedestre_block` no candidato #1 ou centróide bairro | `competidores` do state A3b | cache hit se mesma coord; senão +1 cold |
| **A6** | `top_vias_por_fluxo` → `melhores_vias_prospeccao` (+ `mapa_svg` / `coords`) | mesmo GeoJSON do motor (sem 2ª osmnx) | ~ms após cache |
| **API** | `GET /api/relatorios/{id}/fluxo-pedestre` | lê persistido + cache | fora do pipeline |

**Conflitos com §7 (auditados jul/2026):**

1. **Bloqueia A1** — GeoScout é gate do `ParallelAnalysis`; osmnx cold segura o pipeline inteiro (ex.: relatório `9901df6e` ~11+ min preso em GeoScout).
2. **Duplicação A1 + A6** — mesma análise pode rodar 4× (3 candidatos + bloco relatório) se coords diferem e cache vazio.
3. **POI duplicado** — Overpass busca POIs que A3a já tem via SearchAPI Maps; deveria **reusar** `concorrentes_brutos` no A6 (já faz) e **tirar do A1** ou passar state.
4. **Não entra no veredito** — `fluxo_score` é badge/UI; score regional continua 4 dim (geoscout + 3 regionais).
5. **Calibragem pendente** — Cocó golden ≥70; smoke deu ~26.7 (α/β/γ).

**Direção correta (não implementada):**

- Fluxo **só no A6** (ou job async pós-pipeline), **1× por relatório** no centróide do bairro ou top-1.
- A1 grava só `fluxo_confianca: pendente` ou copia do bloco A6 após merge.
- POIs = concorrentes SearchAPI + âncoras A1, não Overpass genérico quando state disponível.
- Flag `FLUXO_PEDESTRE_IN_A1=false` em prod até latência < 60s (cache quente).

---

## 9. Auditoria MD vs código — gaps conhecidos (revisitar sempre)

| Tópico | Este MD (antes) | Código real (jul/2026) | Status |
|---|---|---|---|
| `oferta_concorrentes` writer | A3c [off] | **A3b** escreve + mescla | ✅ corrigido neste doc |
| A3c status | shadow / religar pipeline | **Morto**, fundido no A3b | ✅ corrigido neste doc |
| A1 fontes | só Maps + SearchAPI imóveis | + osmnx fluxo top-3 | ✅ §8 |
| A6 precompute | 3 blocos | + `fluxo_pedestre` | ✅ |
| A3a reviews | Gemini = classificação primária | **SearchAPI** fetch+card det.; Gemini = refino `categoria_dor` opcional | ✅ §6–§7 |
| SearchAPI `topics[]` | temas insatisfação | **wired** `_fetch_reviews_bundle` + cache | ✅ jul/2026 |
| Gemini reviews | classificação primária | **off** default; opt-in env | ✅ jul/2026 |
| Listings | SearchAPI cascata | cascata **+** Playwright se flag on | ⚠️ manter flag off prod |
| Fluxo no veredito | — | **não** entra fórmula | documentado §8 |
| `inteligencia_competitiva` leitor A3c | tabela §4 | só A6, A9 | ✅ corrigido |

**Checklist antes de merge no pipeline:** (1) novo passo usa SearchAPI ou banco determinístico? (2) bloqueia agente upstream? (3) duplica fetch já feito em agente posterior? (4) número tem carimbo P-010? (5) atualizar este MD + spec se mudar contrato.
