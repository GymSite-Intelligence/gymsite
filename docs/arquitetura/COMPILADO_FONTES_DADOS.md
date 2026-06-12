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
- **Estado:** `tools/ckan_client.py` + `bairro_renda_loader` prontos e testados;
  `data/ckan_catalog/` praticamente vazio (1 arquivo de teste com bug São Paulo/CE).

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
- **Estado:** tools prontas (`cno_fitness_tools`, `consultar_municipio_cnpj_cno`),
  dados via extract local (`CNO_DATA_DIR`); pendência: indexar em tabela Supabase.

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

## 4. Estado consolidado: motor pronto, chave desligada

| Peça | Estado |
|---|---|
| Código das 5 trilhas (clients, loaders, bundle, gates de teste) | ✅ commitado |
| Modos `A0_CONTEXT_SOURCE` (`auto`/`ckan_bundle` estrito/`deep_research_fallback`) | ✅ implementados |
| Carga CNPJ 2026-05 | ✅ completa (132.961) |
| Batch semanal (cron/DAG escritos) | ❌ nunca agendado |
| Catálogo CKAN das cidades-alvo | ❌ vazio |
| Bundles gerados | ❌ nenhum |
| CNO indexado no Supabase | ❌ extract local apenas |
| Recarga mensal CNPJ automatizada | ❌ manual |

## 5. Os 4 passos para ligar o motor

1. `discover_ckan_catalog` para as cidades-alvo reais (Fortaleza, Eusébio, Caucaia,
   João Pessoa...) — popular `data/ckan_catalog/`.
2. Agendar `run_weekly_market_batch` (GitHub Actions ou cron na VM) — inclui recarga
   CNPJ mensal e refresh CVM.
3. Indexar CNO de Fortaleza (município 1389) em tabela Supabase `cno_obras_fitness`.
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
| Censo 2022 / Censo Demográfico | **setor censitário** | A2 score demanda, anel NO_BAIRRO, TAM bairro | população/renda/domicílios DENTRO do polígono do bairro — mata o gap renda_media_bairro sem depender de portal municipal (Trilha 1 vira fallback) |
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
