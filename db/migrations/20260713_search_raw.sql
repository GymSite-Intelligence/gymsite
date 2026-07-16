-- RAW cache SearchAPI (imutável + TTL). Ver docs/A9_SEARCHAPI_INGESTION.md
-- Prod: GYMSITE_SCHEMA_SEP=1 → tabela vive em gymsite.* (tools.db_schema.tbl).

create table if not exists gymsite.search_raw (
  id            uuid primary key default gen_random_uuid(),
  search_id     text not null,
  engine        text not null,
  params_hash   text not null,
  params        jsonb not null default '{}'::jsonb,
  payload       jsonb not null default '{}'::jsonb,
  relatorio_id  uuid references gymsite.relatorios(id) on delete set null,
  fetched_at    timestamptz not null default now(),
  expires_at    timestamptz not null,
  created_at    timestamptz not null default now()
);

create unique index if not exists ux_search_raw_engine_params
  on gymsite.search_raw (engine, params_hash);

create unique index if not exists ux_search_raw_search_id
  on gymsite.search_raw (search_id);

create index if not exists ix_search_raw_relatorio
  on gymsite.search_raw (relatorio_id);

create index if not exists ix_search_raw_expires
  on gymsite.search_raw (expires_at);

comment on table gymsite.search_raw is
  'Payloads crus SearchAPI — cache/auditoria; pipeline lê daqui antes de re-chamar API.';
