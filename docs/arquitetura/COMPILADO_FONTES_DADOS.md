# Compilado — Para Onde a Plataforma de Dados Está Indo (CKAN + CNPJ + CNO)

> Compilado de 2026-06-11 a partir de 19 arquivos com menções a CKAN, do log de carga
> RFB e da integração CNO. Doc-mestre de referência: `ARQUITETURA_DADOS_MERCADO_E_LATENCIA.md`.

---

## 1. A visão em uma frase

Transformar o GymSite de **"agente que pesquisa a web a cada clique"** (Deep Research:
5–20 min, caro, não auditável) em **plataforma com data warehouse próprio de mercado
fitness**, atualizado em batch de fontes OFICIAIS, onde o A0 vira um *loader* de
bundle pré-computado e o relatório sai em **3–8 min com 40k–120k tokens**.

```
        DESCOBERTA              FETCH OFICIAL                ESTOQUE                CONSUMO
┌──────────────────────┐  ┌─────────────────────────┐  ┌──────────────────┐  ┌───────────────────┐
│ CKAN (dados.gov.br + │  │ IBGE/SIDRA  · IPECE     │  │ market_bundle    │  │ A0 = loader (<1s) │
│ portais municipais)  │─▶│ BCB Olinda  · DataStore │─▶│ .json por        │─▶│ A2/A4/A6 reforço  │
│ = catálogo/licença/  │  │ CVM/RI (Smart Fit etc.) │  │ cidade/bairro    │  │ DR só fallback    │
│   link, NÃO o dado   │  └─────────────────────────┘  │ (batch semanal)  │  └───────────────────┘
└──────────────────────┘                               └──────────────────┘
        +  TRILHAS PRÓPRIAS (já carregadas localmente, independentes do CKAN):
┌──────────────────────────────┐   ┌──────────────────────────────────────────┐
│ CNPJ/RFB — parque fitness    │   │ CNO — obras (academias em construção)    │
│ 132.961 estabelecimentos     │   │ radar de FUTUROS concorrentes/leads      │
└──────────────────────────────┘   └──────────────────────────────────────────┘
```

---

## 2. As cinco trilhas de dados

### Trilha 1 — Territorial (CKAN → IBGE/municipal)
- **Papel do CKAN:** catálogo (package_search/package_show) — diz ONDE está o dataset,
  com licença e link. O fetch é sempre na API oficial. "CKAN não substitui IBGE nem
  CVM — organiza o acesso."
- **Lacuna que fecha:** `renda_media_bairro` — Deep Research não entrega (caso
  Parangaba documentado). Portais CKAN municipais (IPECE, SIMDA, secretarias) têm.
- **Estado (atualizado 2026-06-15):** `renda_media_bairro` agora é puxado do **CKAN
  municipal OFICIAL como fonte primária**, não mais lacuna aberta. `bairro_renda_loader.
  _carregar_ckan_bairros` baixa o dataset "Desenvolvimento Humano por Bairro" de Fortaleza
  (dados.fortaleza.ce.gov.br), lê a coluna IDH-Renda e converte para renda per capita pela
  fórmula Atlas Brasil/PNUD (Rmin 8,59 / Rmax 4033,99) — cobre os 124 bairros de Fortaleza.
  Wire completo (bundle build + `financial_tools`). O **piloto curado**
  (`data/bairro_renda_pilot/`) virou FALLBACK rotulado. `tools/ckan_client.py` +
  `bairro_renda_loader` prontos e testados.

### Trilha 2 — Setor listado (CVM/RI)
- Smart Fit (SMFT3), Bluefit: ITR/DRE/KPIs → `sector_benchmarks` (ARPU, churn,
  EBITDA, CAPEX/unidade) para calibrar o A4 ("payback vs rede listada").
- **Estado:** `cvm_fetch` + `cvm_listed_metrics` prontos com fixtures; não agendados.

### Trilha 3 — CNPJ/RFB (parque fitness nacional) — JÁ CARREGADA
- **O que é:** dump mensal da Receita (Estabelecimentos1..9.zip, ~3GB), filtrado por
  CNAE fitness → upsert no Supabase.
- **Estado real (log `metrics/rfb_cnpj_load.log`):** carga 2026-05 COMPLETA —
  **132.961 estabelecimentos fitness** no parque (`done: 132961`).
- **Usos vivos no pipeline:** entrantes 90 dias no A0 (`market_context.entrantes_recentes`),
  tabela de novos entrantes no relatório (A6), envio para prospecção
  (`oportunidades_prospeccao` → sync Apollo), enriquecimento Razão Social/QSA.
- **É a resposta para "41 mil vs 56.833 academias"** dos docs de metodologia: o parque
  CNPJ próprio é a fonte canônica auditável — os outros números viram referência
  externa com ano/fonte.

### Trilha 4 — CNO (Cadastro Nacional de Obras) — radar do futuro
- **O que traz:** obras registradas na Receita → **academias em CONSTRUÇÃO** =
  concorrentes futuros (defesa) e leads de pré-abertura (ataque/prospecção).
- **Regra anti-falso-positivo (CNO_INTEGRACAO.md):** nunca filtrar por CNAE da obra
  (4120400 é construção genérica; 9313100 não aparece em `cno_cnaes.csv`).
  Classificação por `_eh_obra_fitness()`: keyword OU CNPJ responsável com CNAE
  9313100 no parque da Trilha 3. Fluxo obrigatório: município inteiro primeiro,
  recorte de bairro depois.
- **Bônus:** `calcular_benchmark_tempo_obra_cno()` — mediana/P25/P75 de tempo de
  obra por porte → alimenta prazos do PLAYBOOK de execução (tarefas de OBRAS com
  benchmark real, não chute).
- **Estado (atualizado 2026-06-15):** CNO **carregado no Supabase** — flag
  `CNO_SOURCE=supabase` roteia a leitura para `public.cno_obras_fitness`; loader
  `rfb_cno_loader` faz carga fresca via RFB bulk (dadosabertos.rfb.gov.br/CNO) → Supabase
  (`extract` local CSV permanece como fallback/teste). Tools prontas (`cno_fitness_tools`,
  `consultar_municipio_cnpj_cno`). Próximo: rota BQ basedosdados nacional (seção 7) +
  batch (cron) — ainda não agendados.

### Trilha 5 — Local viva (Places/OSM/portais de aluguel)
- Concorrência atual (A3), listings OLX/ImovelWeb (A1), popular times — já em
  produção com caches próprios.

---

## 3. O que cada trilha alimenta

| Consumidor | Trilhas | Resultado |
|---|---|---|
| A0 market_context | 1+2+3+4 via bundle | contexto em <1s, com fonte/licença |
| A2 demografia | 1 (bairro!) | renda/pop de BAIRRO — diferencial vs geomarketing caro |
| A4 financeiro | 2 (CVM) + 1 (BCB) | benchmarks reais de rede listada |
| A6/A8 relatório | 3 (entrantes) + 4 (obras) | "4 academias abriram em 90d + 2 em obra" auditável |
| Prospecção/Apollo | 3 + 4 | leads de entrantes E de pré-abertura |
| Playbook (execução) | 4 (benchmark tempo de obra) | prazos de OBRAS com mediana real |

---

## 4. Estado consolidado: motor pronto, chave desligada (atualizado 2026-06-15)

| Peça | Estado |
|---|---|
| Código das 5 trilhas (clients, loaders, bundle, gates de teste) | ✅ commitado |
| Modos `A0_CONTEXT_SOURCE` (`auto`/`ckan_bundle` estrito/`deep_research_fallback`) | ✅ implementados |
| Carga CNPJ 2026-05 | ✅ completa (132.961) |
| `renda_media_bairro` (Trilha 1) via CKAN municipal oficial | ✅ primário — `bairro_renda_loader._carregar_ckan_bairros` (Fortaleza, 124 bairros, IDH-Renda→renda pc); piloto curado = fallback; wire em bundle + `financial_tools` |
| CNO carregado no Supabase (Trilha 4) | ✅ carga fresca RFB bulk → `public.cno_obras_fitness` sob `CNO_SOURCE=supabase` (extract CSV = fallback) |
| Batch semanal | 🟢 AGENDADO (2026-06-15): `.github/workflows/weekly-market-batch.yml` cron domingo 6h + workflow_dispatch, secrets configurados (GCP_SA_KEY/SUPABASE/MAPS/SEARCHAPI). Roda `run_weekly_market_batch.py` (CVM + bundles das ondas + golden gate). Depende dos secrets estarem setados no repo GitHub |
| Censo 2022 setor no Supabase | 🟢 CARREGADO (2026-06-15): `censo_setor` com **456.008 setores** nacionais (`censo_setor_loader --nacional`). Censo é estático → load 1x, não é passo semanal |
| Bundles gerados | 🟢 EM GERAÇÃO (2026-06-15): `run_weekly_market_batch --skip-cvm` gera os bundles das 10 ondas (market_waves.csv) já com demografia (renda CKAN + pop/ocupação Censo). Antes: nenhum |
| CNO via BQ basedosdados nacional (Trilha 4 → seção 7) | ⏳ rota decidida 2026-06-14; loader+tabela+cron por construir. `bigquery.jobUser` CONFIRMADO presente na SA (2026-06-15) — não falta mais |
| CVM/RI (Trilha 2) | 🟡 PARCIAL (2026-06-15): `atualizar_sector_listed_via_cvm` rodado → CVM ITR real persistido (SMFT3 margem EBITDA 47,8%, dívida/EBITDA 1,48) + ARPU proxy derivado (receita÷alunos). Cobertura KPI op. 25%→50%. Falta: churn (só RI), capex/unidade (extrair DFC), agendar batch |
| Censo 2022 setor censitário / BQ basedosdados (Trilha 6) | 🟡 PARCIAL (2026-06-15): população/domicílios/**média moradores** por setor LIVE via `censo_setor_tools` (BQ, ST_DWITHIN no centróide). Cocó: 127 setores, pop 72.453, média 2,67. Já é FONTE da ocupação na demanda futura (param=fallback). **Renda por setor 2022 NÃO existe** (IBGE não liberou) → renda segue do CKAN Trilha 1. Falta: wire pop no A2/bundle + polígono real do bairro |
| Recarga mensal CNPJ automatizada | ❌ manual |

## 5. Os 4 passos para ligar o motor

1. `discover_ckan_catalog` para as cidades-alvo reais (Fortaleza, Eusébio, Caucaia,
   João Pessoa...) — popular `data/ckan_catalog/` para o bundle. (Nota 2026-06-15:
   o caso `renda_media_bairro` de Fortaleza já está LIVE via rota dedicada do
   `bairro_renda_loader`, primária sobre o piloto — independente desse catálogo.)
2. Agendar `run_weekly_market_batch` (GitHub Actions ou cron na VM) — inclui recarga
   CNPJ mensal e refresh CVM.
3. **CNO via BigQuery basedosdados** (não download de zip) → filtra fitness NACIONAL →
   indexa em `cno_obras_fitness` (Supabase). Sem lista de município; consulta por
   município no read. Detalhe: seção 7.2. (Antes: "indexar só Fortaleza 1389" —
   superado pela rota BQ nacional.)
4. `A0_CONTEXT_SOURCE=auto` em produção + medir antes/depois em 1 relatório
   (gates de `MARKET_DATA_TEST_GATES.md` validam).

---

## 6. Trilha 6 — Base dos Dados (BigQuery) — curadoria 12/06/2026

Catálogo basedosdados.org: 1.164 conjuntos varridos por tema (12 buscas
dirigidas). Diferencial: tabelas TRATADAS e padronizadas direto no BigQuery
(`basedosdados.<dataset>.<tabela>`) — já temos projeto GCP e BigQuery client,
custo de integração baixo. Curadoria pelo critério: alimenta agente/score do
nosso processo ou morre.

### Tier A — entra no bundle (alto valor, granularidade certa)

| Dataset BD | Granularidade | Alimenta | Por quê |
|---|---|---|---|
| Censo 2022 / Censo Demográfico | **setor censitário** | A2 score demanda, anel NO_BAIRRO, TAM bairro | população/renda/domicílios DENTRO do polígono do bairro — reforça `renda_media_bairro` (hoje já coberto via CKAN municipal da Trilha 1, que viraria fallback) com granularidade de setor sem depender de portal municipal. **Ainda não construído** |
| Atlas do Desenvolvimento Humano (ADH) | UDH (sub-municipal) | A2 score socioeconômico | IDHM-renda por região intraurbana; única fonte nacional padronizada nesse grão |
| RAIS | município × CNAE | A0 contexto, benchmark setor | vínculos formais CNAE 9313-1 = tamanho do mercado empregador fitness; massa salarial = demanda diurna (quem TRABALHA perto da academia) |
| CAGED | município × CNAE, mensal | A0 "setor cresce/encolhe" | saldo de empregos fitness 12m = dinâmica do mercado local com fonte oficial e data |
| Quadros Societários CNPJ | nacional | valida Trilha 3 | NÃO substitui nosso parquet local (custo zero); usar como verificação/atualização entre dumps mensais e pra QSA além do nosso filtro fitness |

### Tier B — enriquecimento (entra depois do Tier A rodar)

| Dataset BD | Uso | Nota |
|---|---|---|
| Eleições Brasileiras (perfil eleitorado) | distribuição ADULTA por zona/seção | Censo conta criança; eleitorado é 16+ = público pagante por região — original e ninguém do mercado usa |
| PIB Municipal | A0 macro | uma linha de contexto, custo zero |
| Estatísticas de Frota de Veículos | proxy renda + pressão por estacionamento | dor "estacionamento" já aparece nos reviews; frota/hab contextualiza |
| Pesquisa Nacional de Saúde (PNS) | A9 narrativa | % sedentarismo por capital = argumento de venda do relatório |
| Censo Escolar | polos geradores | baixa prioridade — Places já cobre |

### Tier C — fora (avaliados e descartados)

Esporte competitivo (Olimpíadas/futebol), BNDES, INMET, ESTBAN, Big Mac
Index, INSE-SP (só SP): sem ligação com decisão de ponto fitness.

### Integração

1. IDs exatos das tabelas: confirmar no BQ explorer (`SELECT * FROM
   basedosdados.INFORMATION_SCHEMA` ou UI) antes de codar o loader.
2. Loader novo `tools/basedosdados_loader.py` no padrão dos existentes
   (cache + gate de teste), saída no `market_bundle` — mesma esteira da
   Trilha 1, A0 continua loader de bundle.
3. Censo setor censitário × polígono do bairro = mesmo recorte geométrico
   dos anéis competitivos (Motor v2 Apêndice D) — UMA implementação de
   geometria serve aos dois.
4. Custo BQ: tabelas BD são públicas (billing no nosso projeto, ~centavos
   por query com partição/cluster) — sempre filtrar por sigla_uf/id_municipio.

---

## 7. Decisão (2026-06-14): BQ-basedosdados como ROTA CANÔNICA das fontes nacionais

Volume em GB é razão **PRÓ** BigQuery, não contra: o basedosdados é particionado/
clusterizado, então a query **escaneia só a fatia** (UF/município) — nunca baixa os
GB. Quanto maior o dataset nacional, mais o BQ ganha (download+parse de GB no CI vs
query de MB). Free tier **1 TiB/mês** + filtro = **~US$0**.

### 7.1 Discriminador — quando BQ, quando não

| Fonte é… | Rota | Por quê |
|---|---|---|
| Nacional + padronizada + no basedosdados (CNO, Censo, RAIS, CAGED, PIB, frota) | ✅ **BQ** | tratado, escaneia fatia, grátis, sem baixar GB |
| Municipal / portal-específico (IPTU, zoneamento, áreas edificadas — base do Motor v2) | ❌ CKAN/prefeitura | cada cidade publica o seu; **não existe** no basedosdados |
| REST API pequena point-query (IBGE/SIDRA município, BCB Olinda) | ❌ API nativa | já barato/grátis; BQ só adiciona dependência |
| Já temos path local grátis (CNPJ parque webdav, CVM parser) | ⚠️ BQ = só **verificação** | BQ não substitui o parquet local |

**Ressalva (Motor v2):** BQ cobre contexto demográfico/econômico (Censo/RAIS mata
`renda_media_bairro`), mas **NÃO** a base territorial (IPTU/zoneamento) do registro-
primeiro — essa fica em CKAN/portal municipal. BQ é peça grande, não a história toda.

### 7.2 CNO — 1º caso concreto (resolve o bloqueador de download)

CNO **não** precisa de download de zip da Receita (sem URL estável, manual). Já está
tratado no basedosdados, verificado via `bq`:

| Item | Valor |
|---|---|
| Dataset | `basedosdados.br_me_cno` |
| Tabelas | `microdados` (obras), `microdados_vinculo` (CNPJ responsável), `microdados_cnae`, `dicionario` |
| Volume | **848.256 obras** nacionais; **345** com keyword fitness; 534k na faixa de área |
| Custo | query escaneou **~0 bytes** (5s) — anos dentro do free tier 1 TiB/mês |

**Schema (contrato CNO coberto):** `id_cno`, `area` (FLOAT m²), `cep`/`tipo_logradouro`/
`logradouro`/`numero_logradouro`/`bairro`, `sigla_uf`/`id_municipio`/`id_municipio_rf`,
`situacao`, `data_inicio`/`data_situacao` (tempo de obra), `ni_responsavel`/
`nome_empresarial`/`nome_responsavel` (filtro fitness + cruzamento CNAE 9313100).

**Carga NACIONAL, sem lista de município** (lista = perda de capacidade): filtra fitness
no Brasil inteiro (`_eh_obra_fitness`: keyword + área [80,8000] + cruzamento CNPJ CNAE
9313100 do parque) → upsert no Supabase → pipeline consulta por município no read
(espelha a Trilha 3 CNPJ). De-hardcodar `1389` em `cno_fitness_tools.py`/`ibge_tools.py`.

### 7.3 Componentes a construir

```
tools/basedosdados_loader.py   # client BQ genérico (query + guarda de custo)
tools/cno_bigquery_loader.py   # CNO: microdados+vinculo → _eh_obra_fitness → upsert
db/migrations/*_cno_obras_fitness.sql   # tabela destino (id_cno PK, área, endereço,
                                        # município, situacao, datas, ni_responsavel,
                                        # metodo_classificacao, JSONB cruzamento)
.github/workflows/monthly-receita-batch.yml  # cron MENSAL (1º domingo): CNO (BQ) +
                                              # recarga CNPJ (webdav). Ritmo ≠ semanal.
```

`consultar_municipio_cnpj_cno()` passa a ler de `public.cno_obras_fitness` (Supabase),
não do extract local.

### 7.4 Pré-requisitos e guardas de custo

- **IAM:** service account `gymsite-pipeline@gen-lang-client-0106729343` hoje só tem
  `roles/aiplatform.user`. Precisa de `roles/bigquery.jobUser` (rodar query; grátis,
  reversível) — datasets públicos do basedosdados são lidos por qualquer projeto que
  rode job.
- **Guarda de custo (obrigatória):** toda query com `WHERE sigla_uf=`/`id_municipio=`
  quando aplicável + flag `--maximum_bytes_billed` (cap contra scan acidental >1 TiB).
- **Cadência:** mensal (basedosdados re-ingere dumps da Receita periodicamente).

### 7.5 Esteira de expansão (depois do CNO)

`basedosdados_loader.py` vira template. Próximos pela mesma rota (Tier A da seção 6):
Censo 2022 setor censitário (renda-bairro forte), RAIS/CAGED (mercado empregador
fitness), PIB municipal. Todos: query fatia → bundle/tabela → pipeline lê do banco.
