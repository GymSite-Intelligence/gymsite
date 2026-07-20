---
description: Aplicar UMA migration SQL pendente no Supabase (schema-aware gymsite/public). Proíbe reaplicar todas.
---

# Workflow: /migrate

> **Canônico:** [P-000 §7 gotcha schema](../rules/P-000_REGRA_MESTRA_MUDANCA.md) · [REGRAS_USO_GLOBAL §3.4](../rules/REGRAS_USO_GLOBAL.md) · skill Supabase.
> **Proibido:** `for f in db/migrations/*.sql` · `psql -f db/migrations/*.sql` · tratar `public.*` como tabela quando SEP ON.

Prod Supabase: `epgedaiukjippepujuzc`. Com `GYMSITE_SCHEMA_SEP=1`: tabelas reais em **`gymsite.*`** (e `shared.*`); `public.*` costuma ser **view**.

## Onde vive o SQL (dual-path)

| Pasta | Papel | Quando usar |
|---|---|---|
| **`db/migrations/`** | **Canônico** — histórico completo do monorepo | Sempre criar migration nova aqui; `/migrate` aplica **desta** pasta |
| **`supabase/migrations/`** | Espelho parcial / legado CLI Supabase | Não reaplicar em loop; só se fluxo explícito Supabase CLI pedir — preferir copiar/sincronizar para `db/migrations/` e aplicar uma vez |

**Regra:** um DDL = um arquivo em `db/migrations/` nomeado (`YYYYMMDD_descricao.sql`). Nunca “sincronizar” as duas pastas com `*.sql` em lote.

## Prerequisites

- Arquivo SQL **novo** nomeado (ex. `db/migrations/20260719_foo.sql`) — já revisado
- Acesso service role / MCP Supabase / `psql` com URL de prod (cuidado)
- Saber se DDL mexe em tabela real ou view

## Steps

1. **Identificar a migration** (nunca “todas”)
   ```powershell
   Get-ChildItem db\migrations\*.sql | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name
   ```
   Escolher **um** arquivo. Confirmar que ainda **não** foi aplicado (histórico / advisors / tentativa idempotente).

2. **Pré-check `relkind`** (se ALTER/ADD COLUMN)
   ```sql
   SELECT n.nspname, c.relname, c.relkind
   FROM pg_class c
   JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE c.relname = 'NOME_TABELA'
     AND n.nspname IN ('gymsite', 'public', 'shared');
   ```
   - `r` = tabela → `ALTER TABLE gymsite.…`
   - `v` = view → **não** ALTER; recrear `CREATE OR REPLACE VIEW public…` se precisar compat PostgREST

3. **Backup lógico (antes de DDL destrutivo)**
   - Preferência: dump schema/tabela via Supabase dashboard ou `pg_dump --schema=gymsite …`
   - Ver também `/backup` para dump amplo
   - Schema-only **não** é rollback completo de dados

4. **Aplicar só o arquivo**
   - MCP: `apply_migration` / `execute_sql` no projeto certo, **ou**
   ```powershell
   # Exemplo — UM arquivo. Substituir path.
   psql $env:DATABASE_URL -f db/migrations/20260719_foo.sql
   ```
   Idempotente quando possível (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`).

5. **Verificar**
   - Coluna/tabela existe em `gymsite.*`
   - Se view `public`: `CREATE OR REPLACE VIEW` alinhada (padrão `db/migrations/20260713_user_projects_consultor_v2_columns.sql`)
   - Advisors Supabase se RLS/policy tocados
   - App writers: `tbl(sb, "…")` — não hardcode `public`

6. **Smoke**
   - Query Supabase na tabela/view, **ou** endpoint que lê o dado
   - Não assumir Docker local / `localhost:5432`

## Rollback (honesto)

| Situação | Ação |
|---|---|
| Migration com down SQL | Aplicar down **nomeado** |
| Sem down | Restore dump / point-in-time Supabase — **não** “reaplicar schema-only = undo” |
| View errada | `CREATE OR REPLACE VIEW` corrigida |

## Anti-padrões

- ❌ Loop em `db/migrations/*.sql` (reaplica histórico → erro / drift)
- ❌ `ALTER TABLE public.parametros_metodologia` em prod SEP (view)
- ❌ Misturar seed de params com “deploy feito” sem Cloud Run quando Python mudou
