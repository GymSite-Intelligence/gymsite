# Schema GymSite Intelligence — Fase 2

Banco Postgres no Supabase para o CRUD UI baseado no JSON canônico v1.1 do pipeline ADK.

## Arquivos

| arquivo | propósito |
|---|---|
| `schema.sql` | DDL completo: 9 tabelas + 2 views + RLS + helpers |
| `seed.sql` | Org Vectra inicial (rodar após schema) |

## Como aplicar

### Opção A — via MCP Supabase (recomendado pra você)

No Claude Code com MCP Supabase ativo:

```
Use o tool mcp__plugin_supabase_supabase__apply_migration com:
- name: "gymsite_schema_v1"
- query: <conteúdo de schema.sql>
```

Depois aplique o seed:
```
apply_migration name="gymsite_seed_v1" query=<conteúdo de seed.sql>
```

### Opção B — via Supabase CLI local

```bash
cd C:\Users\marce\gymsite_intelligence\db
supabase db push --db-url $env:SUPABASE_DB_URL --file schema.sql
supabase db push --db-url $env:SUPABASE_DB_URL --file seed.sql
```

### Opção C — via SQL Editor do dashboard

1. Abra https://supabase.com/dashboard/project/<seu-projeto>/sql/new
2. Cole conteúdo de `schema.sql` → Run
3. Cole `seed.sql` → Run

## Após aplicar

1. **Crie seu user** via Supabase Auth (signup com email/senha ou Magic Link)
2. **Linke ao Vectra org** rodando:
   ```sql
   insert into organization_members (org_id, user_id, role)
   values (
     '00000000-0000-0000-0000-000000000001',
     '<seu user_id da tabela auth.users>',
     'owner'
   );
   ```

## Estrutura

```
organizations (1) ──N── organization_members ──N── auth.users
       │
       │ 1:N
       ▼
   relatorios ─── 1:1 ── relatorio_inputs      (formulário CRUD)
       │       └── 1:1 ── relatorio_outputs    (scores + veredito + textos)
       │       └── 1:N ── candidatos           (Top 3 imóveis)
       │       └── 1:N ── competidores         (concorrentes + reviews)
       │       └── 3:1 ── cenarios_financeiros (low/mid/premium)
       │       └── N:1 ── bairros_alternativos
```

## RLS (Multi-tenant)

- Todas as tabelas têm RLS habilitado.
- Usuário só vê dados das organizações em que é membro.
- Service role (pipeline ADK) bypassa RLS para gravar resultados.

## Views

- `v_relatorios_resumo` — header + dados-chave pra listagem.
- `v_bairros_aggregate` — agregado por bairro pra dashboards futuros.

## pgvector

Coluna `relatorio_outputs.embedding` (vector 1536) preparada para busca semântica
("encontre relatórios similares a este") usando OpenAI text-embedding-3-small
ou Gemini embeddings.

## Próximos passos (Fase 2)

1. ✅ Schema aplicado
2. 🔲 Endpoint Edge Function que recebe input do form e dispara pipeline ADK
3. 🔲 Frontend React/Vite (form + listagem + viewer do relatório)
4. 🔲 Worker/queue pra rodar pipeline em background (BullMQ ou Supabase Edge)
5. 🔲 Adapter Python no pipeline pra gravar JSON v1.1 direto no Postgres
