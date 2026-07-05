# GymSite — Schema Supabase (no projeto compartilhado `cargo-flow-navigator`)

> O GymSite Intelligence **não tem Supabase próprio**: vive no projeto `epgedaiukjippepujuzc`
> (nome no dashboard: *cargo-flow-navigator*), compartilhado com Vectra Cargo / MiroFish /
> Scout / SIPOC (~150 tabelas no total). Este doc isola e descreve **apenas o schema GymSite**.
> RLS verificada via `pg_policies` em 2026-06-16 (não presumida).
>
> ⚠️ **DEFASADO PARCIALMENTE (nota 2026-07-03):** escrito quando tudo vivia em `public`.
> Desde jun/2026 as tabelas GymSite moram nos schemas **`gymsite`** (negócio) e **`shared`**
> (tenancy + dado aberto), com views de compat em `public`. Roteamento: `tools/db_schema.py`.
> A modelagem/colunas descritas abaixo seguem válidas; o schema-pai mudou.

## 1. Pipeline de relatório — star schema

`relatorios` é o hub; toda tabela filha referencia `relatorio_id` (FK). `org_id` → `organizations`.

```
relatorios ──org_id──> organizations
  ├─ relatorio_inputs          (params do request)
  ├─ relatorio_outputs         (veredito, scores, posicionamento, demanda, demografia — JSON pesado)
  ├─ relatorio_custos_agentes  (telemetria custo por agente)
  ├─ relatorio_api_calls       (telemetria de chamadas externas)
  ├─ candidatos                (imóveis top — A1 GeoScout)
  ├─ competidores              (concorrentes — A3)
  ├─ bairros_alternativos      (A6)
  ├─ cenarios_financeiros      (3 cenários — A4)
  │    └─ sensibilidade_cenarios  (FK cenario_id + relatorio_id — stress tests)
  └─ validacoes                (saída do A8 validator; FK org_id + relatorio_id)
```

Standalone (sem FK pro hub):
- `leads` — captura da landing (`/api/leads` + sync Apollo). org-scoped.
- `chat_interacoes` — histórico do `/api/chat`. RLS sem policy (só service-role).
- ~~`chat_sessions_deprecated_20260610`~~ — **REMOVIDA** (era dead table).

## 2. Dados determinísticos (reference data, sem FK)

Carregados por ETL/loaders, lidos pelo pipeline via service-role. **RLS on + 0 policy** (deny-all a anon/authenticated; service-role bypassa).

| Tabela | Linhas | Tamanho | Loader / fonte |
|--------|--------|---------|----------------|
| `censo_setor` | ~459k | 84 MB | `censo_setor_loader` (IBGE Censo 2022 setor) |
| `cnpj_fitness_estabelecimentos` | ~133k | 72 MB | `rfb_cnpj_fitness_loader` (CNAE 9313-1/00) |
| `cno_obras_grande_porte` | ~118k | 54 MB | `rfb_cno_loader` (RFB mensal) + `cno_bigquery_loader` (backfill ≤2021, insert-only) |
| `renda_bairro` | ~17k | 11 MB | `renda_bairro_loader` (IBGE Censo 2022 nacional) |
| `municipio_rf_ibge` | ~5.5k | 968 kB | mapa código RF↔IBGE |
| `cno_obras_fitness` | 751 | 664 kB | derivado CNO (classificação fitness) |
| `cnpj_contato_cache` | 456 | 504 kB | cache de contato CNPJ |
| `parametros_metodologia` | 161 | 104 kB | tabela de calibração (`param()`) — source of truth recalibrável |
| `ipece_renda_bairro` | 121 | 88 kB | **LEGADA** (só Fortaleza; sem reconciliação ativa) |
| `market_bundles` / `market_snapshots` | — | — | bundles de contexto de mercado (A0) |

Footprint: ~221 MB de ref data fitness colocada na Supabase do cargo (nota arquitetural).

## 3. Segurança / RLS

✅ **Multi-tenant CORRETO** — as tabelas do relatório usam `org_id IN (SELECT user_org_ids())`
no `USING` **e** `WITH CHECK`. UPDATE de `relatorios` tem ambos (não permite reassinar `org_id`).
Filhas escopam via parent (`relatorio_id IN (SELECT id FROM relatorios WHERE org_id IN user_org_ids())`).
**Sem BOLA/IDOR, sem `TO authenticated` cru.**

⚠️ **Posture (não-vulnerabilidade):**
- 13 tabelas com **RLS on + 0 policy** (ref data + `chat_interacoes`): seguras (deny-all), mas
  o frontend **não lê direto** via anon (ex.: UI de recalibração de `parametros_metodologia`
  precisaria ir via API ou ganhar uma policy de leitura pública).
- **Data API (pg_graphql)** expõe todas as tabelas GymSite a `anon`+`authenticated`. As com
  policy filtram linha; as 0-policy negam tudo. Pra reduzir surface, mover ref data pra schema
  não-exposto é opção.
- `leads`/`validacoes` usam `roles={public}` (inclui anon) — o predicado org-scoped torna
  seguro (anon → `user_org_ids()` vazio → 0 linhas), mas `{authenticated}` seria mais apertado.

## 4. Notas

- O ID do projeto Supabase do GymSite é `epgedaiukjippepujuzc` (= cargo-flow-navigator).
- Ver também `docs/metodologia/data_lineage.md` (fonte → tabela → agente).
