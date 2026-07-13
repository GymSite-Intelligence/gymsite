# Data Lineage — GymSite Intelligence

> Mapa fonte → tabela/loader → agente consumidor. Cobre 70% do valor de um catálogo (Dataplex é luxo pra 1 dev — ver `roadmap_dados_bq_sinergia.md` Apontamento 3). Atualizar quando entrar fonte/tabela nova.

## Princípio (regra de ouro)
Toda métrica de cálculo vem de **dado com fonte** (tabela sourced) ou **benchmark rotulado** (`parametros_metodologia`). Nada hardcoded inline. Veredito/score = **determinístico** (param table + tools), nunca LLM gerando número.

## Dados externos → onde vivem → quem consome

| Fonte (origem) | Onde mora | Atualização | Consumidor (agente/tool) |
|---|---|---|---|
| **IBGE Censo 2022 — renda do responsável por bairro** (FTP Agregados_..._Rendimento_do_Responsavel) | tabela `renda_bairro` (nacional, 17.367 bairros, 895 cidades) · loader `tools/renda_bairro_loader.py` · JSON `tools/data/ibge_renda_bairro_BR_2022.json` | one-time (re-FTP anual) | `tools/posicionamento_renda.py` (headroom/percentil) → A9; `bairro_renda_loader` → A2 (FEITO, commit 93bdd60) |
| IPECE Informe 272 (Fortaleza, Censo 2022) | tabela `ipece_renda_bairro` (121, Fortaleza) | one-time | LEGADA — carga histórica; reconciliação ativa NÃO implementada (`posicionamento_renda` lê `renda_bairro`, não esta) |
| Data.Rio / IPP (RJ, Censo 2022) | JSON `tools/data/datario_renda_bairros_rj_2022.json` (não tabelado) | one-time | cross-check (RJ) — superseded pelo `renda_bairro` nacional |
| **IBGE Censo 2022 — pop/ocupação por setor** (basedosdados BQ) | tabela `censo_setor` (espelho nacional ~456k setores) · `tools/censo_setor_loader.py` | one-time | `tools/demanda_futura_tools.py` (ocupação), `tools/demografia_bairro_tools.py` |
| CKAN Fortaleza — IDH-Renda por bairro (base **Censo 2010**) | in-code `tools/bairro_renda_loader.py` | — | A2 demografia (fallback **tier 2**; SUPERSEDED — `renda_bairro` IBGE 2022 é primário desde commit 93bdd60) |
| IBGE renda per capita municipal (Censo 2022) | dict em `tools/ibge_tools.py` | — | A2 `analise_demografica_completa` (renda municipal, fallback do bairro) |
| **Benchmarks setoriais** | tabela `parametros_metodologia` · `tools/parametros_metodologia.py` · seed `tools/parametros_seed.py` | recalibrável (Supabase, sem deploy) | **TODOS** via `param()` (score demográfico/viabilidade/saturação/headroom/veredito) |
| └ hierarquia calibração | (1) **CVM / IR redes capital aberto** — Smart Fit (SMFT3), Bluefit e pares com DFs/releases públicos; (2) ACAD/Sebrae/Panorama; (3) calibração GymSite rotulada. Panorama sem % fechado → **não inventar**; manter ACAD ou puxar CVM. Proxy low-cost ≠ mid/premium. | ver P-000 §3 | A4 / `DEFAULTS_FALLBACK` / seeds |
| **CNO obras (RFB)** | tabelas `cno_obras_grande_porte` + `cno_obras_fitness` (Supabase) · loader VIVO `tools/rfb_cno_loader.py` (RFB bulk **mensal**); `tools/cno_bigquery_loader.py` = backfill histórico ≤2021 **dormente** (insert-only) | mensal (RFB) | `demanda_futura_tools` (obras futuras), `leads_condominial_tools` — leem do **Supabase**, não BQ em runtime |
| **CNPJ RFB fitness** (CNAE 9313-1/00, snapshot mensal) | tabela `cnpj_fitness_estabelecimentos` (Supabase) · loader `tools/rfb_cnpj_fitness_loader.py` · tool `tools/cnpj_fitness_tools.py` | mensal | A0 (`dados_parque_cnpj_para_a0` — parque ativo + entrantes), A6 (`fatos_parque_cnpj`) |
| **MRLR aluguel comercial** (IBAPE-GO, determinístico) | coeficientes `catalogos_metodologia` (`mrlr_coef`, `mrlr_escala`) · `tools/mrlr_modelo.py` · `tools/aluguel_mrlr.py` · espelhos `municipio_pib` + `renda_bairro` | recalibrável (catálogo) | A4 Tier 0 (`analise_financeira_a4_completo`), A1 (`anchoring_tools._anexar_aluguel_mrlr`) — **única fonte de aluguel de viabilidade** |
| **FipeZap** (séries de aluguel/m², mensal) | tabela `fipezap_indices` (Supabase) · loader `tools/fipezap_loader.py` · tool `tools/fipezap_tools.py` | mensal | A4 fallback pós-MRLR via `analise_financeira_completa` (benchmark rotulado, `aluguel_deterministico=false`) |
| **Portais imobiliários** (ZAP/Viva/OLX) | `tools/9_obsolete/aluguel_municipio_portais.py` (shim em `tools/aluguel_municipio_portais.py`) | legado | A4 Tier 1 **só** se `ALUGUEL_PORTAIS_TIER1=1` e MRLR falhou — **não** alimenta bundle batch |
| **OpenStreetMap** (malha viária + POIs Overpass) | runtime (OSMnx/Overpass) · cache `spatial_flow_cache` (Supabase, TTL 90d) | malha lenta | `tools/space_syntax.py` → fluxo pedestre (Choice angular + Integration) · A1 `fluxo_score` · A6 `fluxo_pedestre` · `GET /api/relatorios/{id}/fluxo-pedestre` |
| Google Places (New) | runtime (API) | — | `competitor_tools` (A3, âncora-bairro), `anchoring_tools` (A1) |
| Google Maps geocode/Distance | runtime (API) | — | A1, `demanda_futura`, `posicionamento_renda` |
| Google Maps Popular Times (lotação) | scraping runtime (Playwright + SearchAPI) · cache disco TTL 7d · `tools/popular_times_tool.py` | runtime (cache 7d) | `competitor_tools` → A3 (horários de pico) |
| **Gemini Search Grounding** (`GEMINI_API_KEY`) | runtime (API) | — | A7 qualitativo, A3 horários — **proibido** para aluguel OPEX / número de viabilidade (P-000 §3) |
| **SearchAPI.io** (`SEARCHAPI_KEY`) | runtime (API) | — | A3 concorrentes/reviews (`engine=google_maps`), listings candidatos (`listing_cascata`), Popular Times, Instagram — **não** aluguel viabilidade |
| **Agregadores** (Wellhub · Gurupass · TotalPass) | runtime httpx · `tools/agregadores_fetcher.py` · camada 3 `competitor_offer_mapper` | runtime | A3 oferta/ticket (tier corporativo rotulado) — ver `agents/specs/SPEC_OFERTA_AGREGADORES.md` |
| **Pré-lançamentos CNO** (janela T+24) | `tools/lancamento_fetcher.py` | runtime | `demanda_futura_tools` — refino determinístico; ver `SPEC_REFINO_LANCAMENTO_DETERMINISTICO.md` |
| **Catálogos metodologia** (dores, MRLR, faixas…) | tabela `catalogos_metodologia` · `tools/catalogos.py` | recalibrável | taxonomias e coeficientes sourced — nunca enum hardcoded em insight |

## Tabelas de saída (pipeline → Supabase)
`relatorio_inputs` (params do request) · `relatorios` (status/header) · `relatorio_outputs` (veredito, scores, posicionamento_estrategico+headroom, demanda_futura, demografia_bairro) · `competidores` · `candidatos` · `bairros_alternativos` · `validacoes` (saída do A8) · `relatorio_custos_agentes` (telemetria custo).

> BQ `gymsite_analytics.relatorios_mercado` foi **REMOVIDA** (2026-06-16) — era dead table com 3 rows dummy de cargo/logística, zero refs no código. Pipeline grava no Supabase `relatorio_outputs`, nunca no BQ. Dataset `gymsite_analytics` ficou vazio.

## Árvore determinística do veredito (folhas sourced)
```
veredito (cutoffs param 8/6/4)
└ score_bairro = média(
    demografico  ← ibge_tools (faixa% + renda BAIRRO renda_bairro/CKAN, cutoffs param)
    concorrencia ← competitor_tools (densidade/score, cutoffs param) + Places âncora-bairro
    viabilidade  ← financial_tools.calcular_score_viabilidade (param)
  ) + geoscout (anchoring_tools, param)
posicionamento (A9) → headroom_renda (posicionamento_renda + renda_bairro, determinístico)
```
Cada folha rastreável via `tools/metodologia_explain.py` (param_meta {categoria, fonte}).

## Calibração α/β/γ (2026-07-12)

Coeficientes iniciais iguais (0.33 / 0.33 / 0.34). Benchmark OndeAbrir Cocó: Fluxo **80/100**.
Meta GymSite: artérias estruturais ≥ 70; ruas locais < 40 no mesmo raio 2 km.
Ajuste futuro via `AnalysisConfig.alpha_pop`, `beta_emp`, `gamma_transp` em `tools/space_syntax.py`.

## Pendências de lineage
- ✅ FEITO: `bairro_renda_loader` (A2) usa `renda_bairro` IBGE 2022 > CKAN 2010 (commit 93bdd60).
- ✅ FEITO (2026-06-16): lineage reconciliado com a auditoria — +FipeZap, +CNPJ RFB, +Popular Times; CNO "onde mora" corrigido (Supabase, não BQ); SearchAPI×Gemini Grounding separados; `validacoes` (era `validacao_a8`).
- Data.Rio JSON não tabelado (redundante com `renda_bairro`; manter só como cross-check ou descartar).
- SP capital usa **distrito** (não bairro) no IBGE → `renda_bairro` não cobre; carregar `Agregados_por_Distrito` quando for prospectar SP.
- `ipece_renda_bairro`: tabela legada sem reconciliação ativa — decidir entre implementar cross-check ou marcar deprecada (docstring de `posicionamento_renda.py` ainda a cita).
- CNO: dois loaders (BQ histórico + RFB mensal) na mesma tabela; precedência resolvida via `ignore_duplicates` no loader BQ (commit 6eb692e). Considerar coluna `data_carga` se precisar rastrear origem por linha.
