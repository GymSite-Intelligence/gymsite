# Roadmap de Dados — 3 apontamentos-sinergia (BigQuery / App-Centric)

> Origem: análise multi-agente do **documento-fonte** abaixo. Veredito: doc 80% certo, mas propõe TUDO de uma vez = over-engineering pra early-stage (1 dev). Aqui ficam só os **3 ADOTAR** com sinergia ao que já estamos fazendo.

## 📎 Documento-fonte (criado pelo dono do produto)
Pasta [`analise_melhorias_bq/`](./analise_melhorias_bq/) (extraída de `Analise de melhorias BQ.zip`):
- **Tese** — [`diferencas_disciplinas_dados.md`](./analise_melhorias_bq/diferencas_disciplinas_dados.md) (92KB): as 4 disciplinas de dados (análise/ciência/engenharia/administração) convergindo no BigQuery; aplicação ao GymSite (§12).
- **Arquitetura** — [atual](./analise_melhorias_bq/gymsite_arquitetura_atual.png) · [futura](./analise_melhorias_bq/gymsite_arquitetura_futura.png) (Supabase-cêntrico → App-centric com BQ DW + Analytics Hub + Dataplex).
- **BQ sharing** — [Analytics Hub](./analise_melhorias_bq/bq_analytics_hub_architecture.png) · [modelos de sharing](./analise_melhorias_bq/bq_sharing_models_comparison.png) · [catálogos granulares](./analise_melhorias_bq/bq_granular_catalogs_curation.png).
- **App-centric / skills** — [golden paths](./analise_melhorias_bq/adc_golden_paths_data.png) · [convergência](./analise_melhorias_bq/convergencia_app_centric.png) · [pipeline](./analise_melhorias_bq/pipeline_dados_fluxo.png) · [skills radar](./analise_melhorias_bq/skills_radar_chart.png) · [Venn disciplinas](./analise_melhorias_bq/venn_disciplinas_dados.png) · [salários](./analise_melhorias_bq/salarios_comparacao_brasil.png).

Este roadmap é a **leitura crítica + plano de execução faseado** do que esse documento propõe.

## Veredito da análise (resumo)
| proposta | veredito | gatilho de reconsideração |
|---|---|---|
| A2 REST→BigQuery SQL | ✅ **ADOTAR** | — (já) |
| App Hub registration (light) | ✅ **ADOTAR-PARCIAL** | — (só registration, sem blueprints) |
| Schema/lineage docs | ✅ **ADOTAR** | — (já) |
| Data Warehouse central (ETL) | 🟢 **JÁ EM CURSO** | = nacionalização IBGE (renda_bairro) |
| Analytics Hub multi-tenant | ⏸️ ADIAR | ≥2 clientes pagando por dados |
| Dataplex catalog full | ⏸️ ADIAR | ≥3 devs OU ≥20 tabelas |
| BQML A7 preditor | ❌ DESCARTAR agora | ≥100 relatórios históricos |

**Sinergia central:** o "Data Warehouse Central / Fase 2" do doc (camada de produto na [arquitetura futura](./analise_melhorias_bq/gymsite_arquitetura_futura.png)) = a **nacionalização da renda IBGE** que já executamos (`renda_bairro`, 17k bairros, Censo 2022). A fundação do doc já está de pé — sem o overhead de Analytics Hub/Dataplex/App Hub do topo do diagrama.

---

## Apontamento 1 — A2 DemoAnalyst: cross-query via BigQuery (granularidade setor)
**O que:** o A2 pode, além da renda (que já vem nacional do `renda_bairro` Supabase), cruzar setor censitário × PIB municipal × densidade numa query SQL ao `basedosdados.br_ibge_censo_2022`. Hoje A2 faz REST municipal.

**Sinergia:** já temos (a) `censo_setor` (pop/ocupação por setor, espelhado) e (b) `renda_bairro` (renda Censo 2022). O BQ SQL agrega o que falta: **cross-query** (faixa etária no setor + densidade no raio + crescimento 2010–2022) numa chamada.

**Plano (faseado, baixo risco):**
1. Tool `analise_setor_bq(lat, lng, id_municipio)` → 1 query parametrizada ao basedosdados (pop por faixa, densidade, crescimento). **Feature-flag** `A2_FONTE=bq`; fallback REST/`analise_demografica_completa` se BQ falhar ou setor não publicado.
2. A2 consome o cross-query SÓ pra enriquecer (faixa etária granular); a renda continua do `renda_bairro` (mais simples que BQ pra esse campo).
3. Telemetria de custo BQ (< R$0,10/query esperado) + de tokens economizados.

**Esforço:** médio (~2-3 dias). **Payoff:** granularidade setor + −tokens (Search Grounding pra dado estruturado). **Risco:** lock-in GCP (mitigado por flag+fallback); setor não 100% publicado (fallback municipal).

---

## Apontamento 2 — App Hub registration (visibilidade, sem blueprints)
**O que:** registrar o GymSite como UMA aplicação no Google Cloud App Hub → Cloud Hub mostra custo/health/dependências num painel só (hoje: Cloud Run + Supabase + Maps + BQ espalhados).

**Sinergia:** acabamos de adicionar fontes (renda_bairro, censo_setor, CNO, IPECE/DataRio) — App Hub agrupa esses workloads logicamente. Casa com o `/api/version` (já temos) pra rastrear o que está deployado.

**Plano:** registrar backend FastAPI (Cloud Run) como service + os loaders/ETL como workloads. **NÃO** fazer Application Design Center blueprints (prematuro — arquitetura ainda evoluindo). Usar Gemini Cloud Assist só pontual.

**Esforço:** baixo (~20h, IaC). **Payoff:** MTTR (saber qual agente/fonte falhou) + custo por aplicação. **Risco:** baixo (Supabase é externo ao GCP — registrar como workload genérico).

---

## Apontamento 3 — Schema + lineage docs (data lineage)
**O que:** documentar o LINEAGE dos dados: fonte → tabela → agente que consome. Hoje está só no código.

**Sinergia:** com `renda_bairro` + `ipece_renda_bairro` + `datario` + `parametros_metodologia` + `censo_setor` + `cno`, o mapa de dados cresceu — precisa de um README de lineage antes de virar caos.

**Plano:** `docs/metodologia/data_lineage.md` — tabela por fonte:
| fonte | tabela Supabase | atualização | agente consumidor |
|---|---|---|---|
| IBGE Censo 2022 renda | `renda_bairro` | one-time (re-FTP anual) | A2, posicionamento_renda, bairro_renda |
| IBGE Censo 2022 setor | `censo_setor` | one-time | demanda_futura, demografia_bairro |
| benchmarks setoriais | `parametros_metodologia` | recalibrável | todos (param) |
| CNO obras | (BQ basedosdados) | leitura | demanda_futura |
| Google Places | runtime | — | A3 |
Sem Dataplex (luxo pra 1 dev) — README cobre 70% do valor.

**Esforço:** baixo (~10h). **Payoff:** onboarding + "o que é essa coluna". **Risco:** zero.

---

## Sequenciamento (1 dev, early-stage)
```
JÁ FEITO   ── Fundação Fase 2: renda nacional (renda_bairro) + 165 params sourced
FASE 1 ─── Apontamento 3 (lineage docs, 10h)  ── baixo risco, destrava entendimento
       └── Apontamento 1 (A2 cross-query BQ, flag+fallback)  ── payoff tokens/granularidade
FASE 2 ─── Apontamento 2 (App Hub registration, 20h)  ── quando ≥3 fontes/serviços (já)
ADIADO ─── Analytics Hub / Dataplex / BQML  ── só nos gatilhos (cliente pagando / 3 devs / 100 relatórios)
```

## Princípio (do veredito dos agentes)
> O risco não é escolher BigQuery (aposta certa) — é escolher TUDO ao mesmo tempo (over-engineering early-stage). Faseado, medir antes de escalar. MoSCoW: must=A2 BQ + lineage; should=App Hub; could=Dataplex; won't(agora)=Analytics Hub + BQML.
