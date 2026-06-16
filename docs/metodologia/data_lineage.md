# Data Lineage — GymSite Intelligence

> Mapa fonte → tabela/loader → agente consumidor. Cobre 70% do valor de um catálogo (Dataplex é luxo pra 1 dev — ver `roadmap_dados_bq_sinergia.md` Apontamento 3). Atualizar quando entrar fonte/tabela nova.

## Princípio (regra de ouro)
Toda métrica de cálculo vem de **dado com fonte** (tabela sourced) ou **benchmark rotulado** (`parametros_metodologia`). Nada hardcoded inline. Veredito/score = **determinístico** (param table + tools), nunca LLM gerando número.

## Dados externos → onde vivem → quem consome

| Fonte (origem) | Onde mora | Atualização | Consumidor (agente/tool) |
|---|---|---|---|
| **IBGE Censo 2022 — renda do responsável por bairro** (FTP Agregados_..._Rendimento_do_Responsavel) | tabela `renda_bairro` (nacional, 17.367 bairros, 895 cidades) · loader `tools/renda_bairro_loader.py` · JSON `tools/data/ibge_renda_bairro_BR_2022.json` | one-time (re-FTP anual) | `tools/posicionamento_renda.py` (headroom/percentil) → A9; **(planejado)** `bairro_renda_loader` p/ A2 |
| IPECE Informe 272 (Fortaleza, Censo 2022) | tabela `ipece_renda_bairro` (121, Fortaleza) | one-time | cross-check do `renda_bairro` (validação) |
| Data.Rio / IPP (RJ, Censo 2022) | JSON `tools/data/datario_renda_bairros_rj_2022.json` (não tabelado) | one-time | cross-check (RJ) — superseded pelo `renda_bairro` nacional |
| **IBGE Censo 2022 — pop/ocupação por setor** (basedosdados BQ) | tabela `censo_setor` (espelho nacional ~456k setores) · `tools/censo_setor_loader.py` | one-time | `tools/demanda_futura_tools.py` (ocupação), `tools/demografia_bairro_tools.py` |
| CKAN Fortaleza — IDH-Renda por bairro (base **Censo 2010**) | in-code `tools/bairro_renda_loader.py` | — | A2 demografia (fallback **a ser superseded** por `renda_bairro` 2022) |
| IBGE renda per capita municipal (Censo 2022) | dict em `tools/ibge_tools.py` | — | A2 `analise_demografica_completa` (renda municipal, fallback do bairro) |
| **Benchmarks setoriais** (ACAD/Sebrae/Smart Fit + calibração GymSite) | tabela `parametros_metodologia` (165 métricas sourced) · `tools/parametros_metodologia.py` · seed `tools/parametros_seed.py` | recalibrável (Supabase, sem deploy) | **TODOS** via `param()` (score demográfico/viabilidade/saturação/headroom/veredito) |
| CNO obras (RFB) | basedosdados BQ (leitura) + `tools/cno_*` | leitura | `demanda_futura_tools` (obras futuras), `leads_condominial_tools` |
| Google Places (New) | runtime (API) | — | `competitor_tools` (A3, âncora-bairro), `anchoring_tools` (A1) |
| Google Maps geocode/Distance | runtime (API) | — | A1, `demanda_futura`, `posicionamento_renda` |
| SearchAPI / Search Grounding | runtime | — | A3a (horários), A4 (aluguel mediana) |

## Tabelas de saída (pipeline → Supabase)
`relatorio_inputs` (params do request) · `relatorios` (status/header) · `relatorio_outputs` (veredito, scores, posicionamento_estrategico+headroom, demanda_futura, demografia_bairro) · `competidores` · `candidatos` · `bairros_alternativos` · `validacao_a8` · `relatorio_custos_agentes` (telemetria custo).

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

## Pendências de lineage
- `bairro_renda_loader` (A2) ainda lê CKAN 2010 → migrar p/ `renda_bairro` 2022 (nacional).
- Data.Rio JSON não tabelado (redundante com `renda_bairro`; manter só como cross-check ou descartar).
- SP capital usa **distrito** (não bairro) no IBGE → `renda_bairro` não cobre; carregar `Agregados_por_Distrito` quando for prospectar SP.
