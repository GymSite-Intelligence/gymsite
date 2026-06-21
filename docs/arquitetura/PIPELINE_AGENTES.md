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
├─ A1  GeoScout                det.     →candidatos_geoscout(_pronto)
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
- **Classe / model:** `Agent` (LLM) · gemini-2.5-flash
- **Tools:** `carregar_market_bundle`, `rodar_deep_research`, `rodar_kimi_research`, `dados_parque_cnpj_para_a0`, `fatos_competicao_local`
- **Lê:** `input_params` (cidade/bairro/uf) · **Escreve:** `market_context`
- **Fonte:** Deep Research + Kimi (qualitativo) · CNPJ RFB/Supabase + CNO (quantitativo) · market_bundle (cache) · OSM
- **Faz:** consolida contexto de mercado (ticket, aluguel, tendência, redes, parque CNPJ/CNO). **Aqui mora a árvore 2×2 do parque** (`dados_parque_cnpj_para_a0` → `arvore_2x2_parque`).
- **Callback (jun/2026):** `after_agent_callback` `_a0_override_cnpj_numeros` — re-roda a tool determinística e **sobrescreve todo número CNPJ** no `market_context` + pluga `arvore_2x2_parque`. O LLM produz a prosa qualitativa; **número = sempre da tool (banco)**, nunca da boca do LLM. Fecha o último "LLM produz dado" do pipeline.
- **Relatório:** §5 (Cobertura Deep Research), §8 (Novos Entrantes CNPJ).

### A1 — GeoScout · [`a1_geoscout.py`](../../agents/a1_geoscout.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analisar_pontos_comerciais_completo` (em thread)
- **Lê:** `input_params`, `market_context` · **Escreve:** `candidatos_geoscout_pronto`, `candidatos_geoscout`
- **Fonte:** Google Maps/Geocoding + SearchAPI imóveis + zoneamento
- **Faz:** zonas comerciais-âncora + top candidatos com score de localização.
- **Relatório:** §2 (Scores), §3 (Top 3 Candidatos), §12 (Bairros Alternativos).

### A2 — DemoAnalyst · [`a2_demo_analyst.py`](../../agents/a2_demo_analyst.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analise_demografica_completa` + perfil sexo/idade + densidade setor
- **Lê:** `input_params`, `market_context` · **Escreve:** `analise_demografica` (+ insights)
- **Fonte:** IBGE Censo 2022 · BigQuery (perfil sexo×idade) · CKAN 2010 (renda legada) · nominatim (fallback)
- **Faz:** renda, público 18-45, score demográfico, perfil sexo, densidade.
- **Relatório:** §2 (Scores), §13 (Demanda Futura T+24).

### A3a — CompetitorSearch · [`a3a_competitor_search.py`](../../agents/a3a_competitor_search.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analisar_concorrentes_a3a_completo`
- **Lê:** `input_params`, `market_context` · **Escreve:** `concorrentes_brutos`
- **Fonte:** **SearchAPI `engine=google_maps`** (primário, 4× barato; Places API fallback) + reviews + Gemini Flash batch (classificação de dores)
- **Faz:** busca + gate `_eh_academia_tradicional` + enriquecimento dos concorrentes.
- **⚠️ Nosso fix:** o gate agora entende types PT do SearchAPI (era só EN → cortava academia real). Ver [`tools/competitor_tools.py`](../../tools/competitor_tools.py).
- **Relatório:** §6.1 (por bairro), §11 (Distribuição Geográfica).

### A3b — CompetitorAnalysis · [`a3b_competitor_analysis.py`](../../agents/a3b_competitor_analysis.py) — **determinizado + FUNDIDO com A3c (jun/2026)**
- **Classe / model:** `BaseAgent` (determinístico) · — *(era `Agent` gemini-2.5-flash-lite)*
- **Macros:** `analisar_concorrentes_completo` (agrega) + `mapear_oferta_competidores_completo` (oferta site+IG via SearchAPI)
- **Lê:** `concorrentes_brutos`, `market_context`, `input_params` · **Escreve:** `inteligencia_competitiva` **+ `oferta_concorrentes`**
- **Faz:** (1) macro calcula gaps/dores/saturação/`score_concorrencia`; (2) grava envelope verbatim + filtra bairro/tipo/CLOSED (`_filtrar_envelope`); (3) sintetiza `posicionamento_recomendado`/`resumo_executivo` por template; (4) **FUSÃO A3c:** roda a oferta e **mescla as modalidades em `servicos_oferecidos` de cada concorrente** (`_mesclar_servicos_na_oferta`).
- **Por que fundiu A3c:** A9 `_gaps_reais` lê `servicos_oferecidos`/`servicos_ig`/`planos_precos` POR concorrente. Sem o site-scrape mesclado, serviço que só aparece no site (não no IG/search) virava **gap falso** → ERRC mandava CRIAR algo que o concorrente já tem → relatório furado (bug Tio Sam). Validado Cocó: merge fechou 6 gaps falsos (spinning/yoga/recovery/funcional/dança/estética que o Parque Esportes já oferece).
- **Por que determinizou:** o LlmAgent só re-emitia o output da macro, dropava campos e crashava (`MALFORMED_FUNCTION_CALL`/OUT=0). **Tradeoff:** tradução de reviews EN→PT saiu.
- **Relatório:** §6 (Inteligência Competitiva), §9 (Counter-Programming), §10/oferta (mensalidades/serviços), e corrige o GAP da ERRC do A9 (§7).

### A3c — CompetitorMapper · [`a3c_competitor_mapper.py`](../../agents/a3c_competitor_mapper.py) — **FUNDIDO NO A3b (morto)**
> A função do A3c (mapear oferta) virou um passo do A3b determinizado. A macro `mapear_oferta_competidores_completo` já normaliza+persiste `oferta_concorrentes` sozinha (sem LLM), e o A3b a chama + mescla os serviços. O arquivo segue no repo mas **não está no pipeline** e o LlmAgent é dead code — remover numa limpeza (cuidar do import em [agent.py](../../gymsite_intelligence/agent.py)).

- **Classe / model:** `Agent` (LLM) · gemini-2.5-flash
- **Tool:** `mapear_oferta_competidores_completo`
- **Lê:** `inteligencia_competitiva.concorrentes_detalhados` · **Escreve:** `oferta_concorrentes`
- **Callback:** `after_agent` fallback determinístico se output vazio
- **Fonte:** site oficial (httpx + BeautifulSoup) + **Instagram via SearchAPI `engine=instagram_profile`** (`get_instagram_profile`) — **sem Playwright, sem Outscraper** (jun/2026). Escopo: só os `concorrentes_detalhados` dados, sem expandir.
- **Status:** modo shadow (A6 não consome). O offer mapper NÃO tem Playwright (é httpx) — o crash citado era do enrichment do A3a. Pendente: determinizar p/ `BaseAgent` (o normalizador `_normalizar_oferta_basica` já existe) + religar no pipeline.
- **Relatório:** seção de ofertas/mensalidades (quando ligado).

### A4 — FinancialEstimator · [`a4_financial_estimator.py`](../../agents/a4_financial_estimator.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `analise_financeira_a4_completo` (async)
- **Lê:** `input_params` (area/tipo/tamanho/gênero), `market_context`, `candidatos_geoscout_pronto` (lat/lng top 1) · **Escreve:** `analise_financeira_pronto`, `analise_financeira`
- **Fonte:** MRLR (aluguel Tier 0) — viabilidade determinística
- **Faz:** 3 cenários (low/mid/premium): CAPEX, OPEX, payback, margem, modelo recomendado, score.
- **Relatório:** §10 (Viabilidade Financeira a/b/c/d).

### A5 — ContactHunter · [`a5_contact_hunter.py`](../../agents/a5_contact_hunter.py) — *fora do pipeline*
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `gerar_contato_decisor_completo` (via `_StateShim`)
- **Lê:** session.state inteiro · **Escreve:** `contato_decisor`
- **Fonte:** Google Maps (proprietário/gerente) + parsing de site + CNPJ (administrador) + Apollo (prospecção)
- **Faz:** decisor #1 + canal + script de abordagem.

### A6 — ReportConsolidator · [`a6_report_consolidator.py`](../../agents/a6_report_consolidator.py)
- **Classe / model:** `Agent` (LLM) · gemini-2.5-flash · **tools=[]** (só narra)
- **Lê:** `market_context`, `analise_demografica`, `inteligencia_competitiva`, `oferta_concorrentes`, `analise_financeira_pronto`, `candidatos_geoscout_pronto`, `contato_decisor` · **Escreve:** `relatorio_md`
- **Callbacks:**
  - `before_agent` `_a6_precompute_callback` → pré-computa `bairros_alternativos_pronto`, `entrantes_cnpj_pronto`, `obras_cno_pronto` (seções **PRÉ-COMPUTADAS** = determinísticas, LLM usa literal)
  - `after_agent` `_a6_after_agent_callback` → parseia markdown, persiste JSON local + Supabase, telemetria
- **Fonte:** CNO (obras) + CNPJ entrantes 90d (precompute) + mapas hardcoded `BAIRROS_ALTERNATIVOS`/`REGIAO_METROPOLITANA`
- **Faz:** monta o relatório executivo de 5 agentes + narração (Claude headless + guardrail).
- **Relatório:** §1 (Resumo Executivo), §16 (Decisão), + injeta as seções pré-computadas.

### A7 — MarketResearch · [`a7_market_research.py`](../../agents/a7_market_research.py) — *auxiliar (chat), NÃO pipeline*
- **Classe / model:** `Agent` (LLM) · gemini-2.5-flash
- **Tool:** `google_search` (Grounding oficial)
- **Lê:** — · **Escreve:** `market_research_result`
- **Fonte:** Google Search Grounding (URLs reais, tempo real)
- **Consumidor (VIVO):** o **chat da landing** ([backend/routers/chat.py:127](../../backend/routers/chat.py#L127), intenção `pesquisa_mercado`). A **função** de grounding também é reusada dentro de A3a/A4. NÃO roda no pipeline de relatório — é tool on-demand.
- **Faz:** pesquisa pontual (horário pico, aluguel, custos, reclamações) sob demanda.

### A8 — Validador Cruzado · [`a8_validator.py`](../../agents/a8_validator.py) — *pós-A6, não-ADK*
- **Classe:** `A8ValidadorCruzado` (classe Python standalone, `async def validar()`)
- **Lê:** `relatorio_markdown` + `state_json` + `relatorio` (dict) · **Retorna:** `alertas`, `score_validacao`, `status_validacao`, `claims_verificadas`
- **Fonte:** Kimi Search (corroboração opcional)
- **Faz:** coerência financeira/demográfica/competitiva; alertas globais.
- **Relatório:** §15 (Alertas Globais).

### A9 — PositioningStrategist · [`a9_positioning_strategist.py`](../../agents/a9_positioning_strategist.py)
- **Classe / model:** `BaseAgent` (determinístico) · —
- **Macro:** `_errc_deterministica(state)`
- **Lê:** `market_context`, `candidatos_geoscout`, `analise_demografica`, `inteligencia_competitiva`, `oferta_concorrentes`, `analise_financeira`, `contato_decisor`, `relatorio_md` · **Escreve:** `relatorio_posicionamento_md`, `relatorio_posicionamento`
- **Callback:** `after_agent` `_a9_after_agent_callback` → override de veredito (headroom renda IBGE 2022) + síntese narrada opcional (Claude headless) + persiste Supabase
- **Fonte:** IBGE Censo 2022 (headroom renda × ticket) — determinístico
- **Faz:** framework ERRC + GAPs + ticket recomendado + veredito (OCEANO_AZUL/TRANSICAO/VERMELHO).
- **Relatório:** §7 (Posicionamento Recomendado).

### A3 — CompetitorIntel · [`a3_competitor_intel.py`](../../agents/a3_competitor_intel.py) — **LEGADO**
- `Agent` (LLM) gemini-2.5-flash, 8 tools soltas. Monólito que estourava AFC=10 (`MALFORMED_FUNCTION_CALL`). **Substituído** por A3a/A3b/A3c. Mantido só p/ referência.

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

---

## 4. Fluxo de dados (state — quem escreve / quem lê)

| Chave de state | Escrito por | Lido por |
|---|---|---|
| `input_params` | entrypoint | A0, A1, A2, A4 |
| `market_context` | A0 | A1, A2, A3a, A4, A6, A9 |
| `candidatos_geoscout(_pronto)` | A1 | A4, A6, A9 |
| `analise_demografica` | A2 | A6, A9 |
| `concorrentes_brutos` | A3a | A3b |
| `inteligencia_competitiva` | A3b | A3c, A6, A9 |
| `oferta_concorrentes` | A3c [off] | A6, A9 |
| `analise_financeira(_pronto)` | A4 | A6, A9 |
| `contato_decisor` | A5 [fora] | A6, A9 (tratam ausência) |
| `relatorio_md` | A6 | A9, A8 |
| `relatorio_posicionamento` | A9 | persistência |

**Padrão:** cada A_n lê o output do A_(n-1); A0 (`market_context`) e `input_params` são lidos por quase todos. A6 e A9 são os **agregadores** (leem 6-8 chaves).

---

## 5. Acoplamento ao trabalho recente (jun/2026)

- **Gate A3a (types PT SearchAPI):** consertado em `tools/competitor_tools.py` — alimenta §6/§11. Antes sub-contava concorrente.
- **Árvore 2×2 CNPJ (joio/trigo, portão CNAE 931 + nome→tipo):** em `tools/cnpj_fitness_tools.py` / `tools/cnpj_segment_classifier.py` — alimenta A0 e §8 do relatório. Parque limpo gated.
- **Narrador Claude headless + guardrail decimal:** `tools/narrador_claude.py` — usado por A6 (§1/§16) e A9 (§7). LLM só veste o dado determinístico.
- **A6 vs A9 = UM PDF, não dois.** `gerar_pdf_weasy(model)` ([api.py](../../api.py)) monta um único PDF de um `model` ESTRUTURADO (saíram do markdown-do-LLM de propósito). A6 fornece as seções de viabilidade; A9 fornece a seção ERRC/posicionamento (`model.posicionamento_estrategico`) + veredito. Complementares, providers de seções diferentes. Os `*_md` (relatorio_md, relatorio_posicionamento_md) são secundários (preview/UI), NÃO a fonte do PDF.
- **Fusão A3b+A3c (jun/2026):** A3b agora emite `oferta_concorrentes` + mescla serviços por concorrente → corrige gap falso da ERRC (A9). A3c morto.
- **Determinização A4/A9/A3a/A3b:** `BaseAgent` sem LLM — números reproduzíveis run-a-run. **A3b** (jun/2026): era LlmAgent-eco que crashava (`MALFORMED_FUNCTION_CALL`); agora roda a macro + grava verbatim + filtro inline + textos por template.

## 6. Auditoria — agentes que AINDA usam LLM (jun/2026)

| Agente | LLM justificado? | Risco | Ação |
|---|---|---|---|
| **A7** MarketResearch | ✅ sim (Google Search Grounding = web em tempo real) | baixo | manter |
| **A6** ReportConsolidator | parcial (é redator) | 🟡 médio | guardrail cobre só o resumo executivo; estender p/ todo número da saída ∈ state |
| **A0** ContextBuilder | só o lado Deep Research/qualitativo | ✅ fechado | LLM mantém a prosa (ticket/aluguel/tendência/insights); `after_agent_callback` `_a0_override_cnpj_numeros` **re-roda a tool e sobrescreve TODO número CNPJ** + pluga `arvore_2x2_parque`. Número = sempre da tool (banco). Travado em `tools/test_a0_override.py`. |
| **A6** ReportConsolidator | parcial (é redator) | 🟡 médio | guardrail cobre só o resumo executivo; estender p/ todo número da saída ∈ state |
| **A7** MarketResearch | ✅ sim (Google Search Grounding) | baixo | manter |
| ~~A3b~~ | — | — | ✅ determinizado + fundiu A3c |
| ~~A3c~~ | — | — | ✅ morto (lógica no A3b) |

**Pendência da determinização:** só **A6** (estender o guardrail além do resumo executivo). A0 fechado via override determinístico (jun/2026); A7 fica LLM por desenho.
