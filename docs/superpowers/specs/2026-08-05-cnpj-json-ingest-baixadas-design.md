# Design — Ingest JSON CNPJ fitness (ativos + baixadas) + métricas mun/bairro

**Data:** 2026-08-05  
**Âmbito:** Espelho RFB → `cnpj_fitness_estabelecimentos` + tools A0 (`dados_parque_cnpj` / árvore oferta)  
**Humano:** Marcelo  
**Depende de:** `docs/metodologia/ipm_mortalidade_migracao.md` (eixos abertura × mortalidade); loader `tools/rfb_cnpj_fitness_loader.py`; tools `tools/cnpj_fitness_tools.py`

---

## Problema

1. Loader ZIP RFB hoje **só upserta situação ativa** (`SITUACAO_ATIVA`) — baixas (`08`) ficam de fora.
2. Tools A0 só expõem **entrantes 90d** — sem baixas, churn, saldo oferta, nem cluster rede.
3. Já existe JSON pré-processado (`ativo+baixada`, ~57k) fora do repo; falta caminho canônico `--from-json`.
4. Produto precisa perguntas tipo Perdizes/SP: abriu N · baixou X (90d e trimestre) · mercado em retração? · academias solo vs multi-unidade (raiz CNPJ).

Baixadas **não são opcionais** — dado rico que complementa o parque ativo.

---

## Decisões (aprovadas)

| # | Escolha |
|---|---------|
| Arquitetura | **Estender espelho atual** — uma tabela `cnpj_fitness_estabelecimentos` |
| Situações no load | **`02` + `08` obrigatórios** — file sem rows `08` → rejeitar |
| Fonte v1 | JSON `receita-cnae-9313100-principal-ativo-baixada.json` (CNAE principal 9313100) |
| Janelas métricas | **90d rolling** + **trimestre calendário** (ex. 2026-Q1 = 01-01…03-31) |
| Qual Q no relatório | **Último Q civil fechado** — Q em andamento fora do v1 |
| Redes | **Hybrid:** cluster agora por `cnpj_basico`; `razao_social` async (enrich / Empresas) |
| Escopo multiunidade | Contar filiais da raiz **no Brasil** (estável); reportar quantas no recorte mun/bairro |
| Números | Só tool/banco — A0/A6 narram; carimbo valor · base · fonte · janela |
| IPM completo | **Fora do v1** — só eixos abertura × mortalidade (+ saldo oferta); migração/MCMV depois |

---

## Fonte JSON

Path típico (fora do monorepo):

`assistent-control/data/processed/receita-cnae-9313100-principal-ativo-baixada.json`

| Campo JSON | Uso |
|---|---|
| `cnpj` | PK lógica (14 dígitos) |
| `cnpj_basico` | `grupo_id` / rede |
| `situacao_cadastral` | `02` ativo · `08` baixada (string ou int) |
| `data_inicio_atividade` | entrantes (`YYYYMMDD` int → date) |
| `data_situacao_cadastral` | baixas na janela |
| `municipio` | código RFB 4 dígitos → `municipio_codigo` + resolve `cidade` |
| `uf`, `bairro`, endereço, CNAEs, `nome_fantasia` | espelho |
| *(ausente)* `razao_social` | enrich async |

Arquivo só-ativos (`…-ativos.json`) = subset — **não** é fonte canônica do load v1.

---

## Schema / migração

Já existem: `situacao_cadastral`, `data_situacao_cadastral`, `bairro`, `razao_social`, unique `(ref_month, cnpj)`.

**Novo (migração):**

```sql
alter table cnpj_fitness_estabelecimentos
  add column if not exists cnpj_basico text;

create index if not exists idx_cnpj_fitness_basico
  on cnpj_fitness_estabelecimentos (cnpj_basico);

create index if not exists idx_cnpj_fitness_situacao_data
  on cnpj_fitness_estabelecimentos (situacao_cadastral, data_situacao_cadastral);
```

Backfill: `cnpj_basico = left(cnpj, 8)` onde null.

---

## Loader

Estender `tools/rfb_cnpj_fitness_loader.py`:

```text
--from-json PATH [--ref YYYY-MM] [--dry-run]
```

### Regras

1. Parse array JSON; exigir ≥1 row com situacao `08` (senão exit ≠0).
2. Aceitar `02` e `08` apenas (outros: log + skip ou contar em `skipped_situacao`).
3. Mapear datas int/`YYYYMMDD` → `date`; situacao → `integer`.
4. `ref_month` = CLI ou inferido (mtime / metadado); persistir `YYYY-MM-01`.
5. Resolver `cidade` via mapa Municípios RFB (mesmo path do ZIP loader) quando possível.
6. Upsert `on_conflict=ref_month,cnpj` incluindo `cnpj_basico`, `bairro`, `nome_fantasia`.
7. `razao_social`: se Empresas map disponível no mesmo `--ref`, preencher; senão null (enrich depois).
8. Idempotente; stdout: counts `upserted_02`, `upserted_08`, `ref_month`.

### Compat ZIP

Path ZIP: flag `--include-baixadas` (**default on**). Queries de parque ativo **sempre** filtram `situacao=02` — sem regressão de contagem.

### CNPJ que some do JSON

Não apagar rows de `ref_month` anteriores. Snapshot novo = só rows presentes no file. Parque ativo = query no `ref_month` mais recente com `situacao=02`. Documentar: “fantasma” = esteve em ref antigo e não no atual.

---

## Métricas (tool determinística)

Estender `dados_parque_cnpj_para_a0` / helpers em `cnpj_fitness_tools.py`.

### Recorte

- Município (`cidade` + `uf`) obrigatório.
- Bairro: match **normalizado** (upper, sem acento, trim); miss → métricas bairro `null` + só município (honesto).

### Parque

- `parque_ativo_*` = count `situacao_cadastral = 02` no `ref_month` vigente (após gate CNAE/nome já existente).

### Entrantes

- `data_inicio_atividade` em janela; situacao atual pode ser 02 ou 08 (abriu e já baixou conta como entrante na janela de abertura).

### Baixas

- `situacao_cadastral = 08` **e** `data_situacao_cadastral` em janela.
- Mesmo **gate parque limpo** (CNAE 931 + nome→tipo) — clínica/saúde não infla mortalidade.

### Âncora temporal (`as_of`)

RFB espelhado atrasa o calendário wall-clock. Janelas usam:

`as_of = min(hoje_utc, último_dia_de_ref_month)`

Ex.: `ref_month=2026-05-01` e hoje=2026-08-05 → `as_of=2026-05-31`. Carimbo inclui `as_of` + `ref_month`.

### Janelas

| Key suffix | Definição |
|---|---|
| `_90d` | `[as_of−90d, as_of]` |
| `_q` | último trimestre civil **fechado** relativo a `as_of` (ex. as_of=2026-05-31 → 2026-Q1 = 2026-01-01…2026-03-31) |

Carimbo: `janela=90d` ou `janela=2026-Q1` · `as_of=…` · `ref_month=…`.

### Árvore oferta (v1)

Expandir além do 2×2 atual:

```text
(estoque_ativo, entrantes, baixas)
  × (municipio, bairro)
  × (90d, Q)
```

Campos mínimos (nomes canônicos — implementação pode aninhar):

| Campo | Significado |
|---|---|
| `baixas_municipio_90d` / `_q` | baixas no mun |
| `baixas_bairro_90d` / `_q` | baixas no bairro (ou null) |
| `entrantes_municipio_q` / `entrantes_bairro_q` | simétrico aos 90d já existentes |
| `saldo_oferta_municipio_q` | entrantes_q − baixas_q |
| `churn_municipio_q_pct` | 100 × baixas_q / parque_ativo_mun (null se parque 0) |
| idem bairro | quando bairro resolvido |

### Redes (hybrid)

1. `grupo_id = cnpj_basico` (8 dígitos).
2. Raiz é **multiunidade BR** se count de estab. fitness `situacao=02` com mesmo `cnpj_basico` no Brasil ≥ 2 (qualquer `ref_month` vigente).
3. No recorte mun/bairro: contar unidades ativas cuja raiz é multiunidade vs solo.
4. Bloco `redes` no payload A0:

```json
{
  "ativos_multiunidade_municipio": 12,
  "ativos_solo_municipio": 40,
  "ativos_multiunidade_bairro": 2,
  "ativos_solo_bairro": 5,
  "baixas_multiunidade_q": 1,
  "baixas_solo_q": 3,
  "criterio": "cnpj_basico com >=2 estab. ativos fitness no BR",
  "razao_social_cobertura_pct": 0
}
```

5. Enrich async: job/reuse `cnpj_enrichment` / `cnpj_contato_cache` → preencher `razao_social`; não bloqueia load nem métricas de contagem.

---

## Contrato A0

- Copiar escalares de `metricas_objetivas` / árvore (override numérico existente).
- Sinal tool `pressao_oferta_q`: `retracao` se `saldo_oferta_*_q < 0`; `expansao` se `> 0`; `neutro` se `= 0`. Churn % só informativo no v1 (limiar IPM 2,5% trim. fica pra fase narrativa/IPM — não gate automático sem calibração).
- LLM narra a partir do sinal + números; **não** inventa N/X.
- Atualizar `agents/specs/SPEC_A0_ContextBuilder.md` + `docs/arquitetura/PIPELINE_AGENTES.md` § fontes quando implementar.

---

## Architecture

```text
JSON ativo+baixada
    → rfb_cnpj_fitness_loader --from-json
    → cnpj_fitness_estabelecimentos (02+08, cnpj_basico)
         ├─ (async) enrich razao_social
         └─ cnpj_fitness_tools
              → arvore oferta + redes
              → A0 override / A6 narração
              → (futuro) IPM numerador migração
```

---

## Fora de escopo (v1)

- IPM com saldo migratório / MCMV  
- Ledger `cnpj_fitness_eventos` separado  
- Lista hardcoded de marcas (Smart Fit…)  
- Q calendário **em andamento** no relatório  
- Crawl nacional diário / sector_intel / CKAN batch  
- Trocar fonte aluguel (MRLR) ou SearchAPI listing  

---

## Error / edge

| Caso | Comportamento |
|---|---|
| JSON sem `08` | Fail load |
| Bairro RFB ≠ produto | Normalize; miss → null bairro |
| `cnpj_basico` ausente | Derivar `left(cnpj,8)` |
| Parque 0 | churn null; não dividir |
| Datas inválidas | skip row + contador |

---

## Sucesso verificável

1. Load dry-run + upsert: `upserted_08 > 0` no mesmo `ref_month`.
2. Query Perdizes/SP (ou fixture): `entrantes_*_90d`, `baixas_*_90d`, `*_q` numéricos com carimbo.
3. Teste unitário: `as_of` + Q fechado corretos com `hoje`/`ref_month` fixos; ativo não conta como baixa; baixa fora da janela ignorada.
4. Teste: raiz com 2+ ativos BR → flag multiunidade; solo = 1.
5. Parque ativo reportado **igual** filtro `situacao=02` (regressão vs só-ativos).

---

## Autorrevisão (pré-user review)

| Lacuna | Fix |
|---|---|
| ZIP default ambíguo | `--include-baixadas` default on |
| `hoje` vs atraso RFB | `as_of = min(hoje, fim ref_month)` |
| Limiar “retração” solto | v1 = sinal por `saldo_q` apenas |
| Gate CNAE em baixas | Mesmo gate do parque limpo (família 931 + nome→tipo); baixas também passam pelo filtro — senão clínica/saúde infla mortalidade |

---

## Changelog

- 2026-08-05 — Spec inicial aprovada (brainstorm: espelho único, baixas obrigatórias, 90d+Q calendário, redes hybrid).
- 2026-08-05 — Autorrevisão: as_of, ZIP default, sinal retracao, gate baixas.
