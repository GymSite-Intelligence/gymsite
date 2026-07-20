-- ============================================================================
-- GymSite — cache tables no schema `gymsite` (2026-07-17)
--
-- Contexto: `GYMSITE_SCHEMA_SEP=1` faz `tools/db_schema.tbl()` rotear
-- `cache_popular_times` / `cache_places_details` / `cache_market_context` /
-- `cache_reviews` para `gymsite.*`. A migration `20260528_cache_tables.sql`
-- criava só em `public` → writes silenciosas falhavam (PGRST205) e o Act-on
-- pico→Supabase não aquecia.
--
-- Segurança: RLS on, sem policies pra anon/authenticated; service_role ALL.
-- Datas: timestamptz UTC. Sem org_id (cache técnico backend-only, não multi-tenant row).
-- ============================================================================

create table if not exists gymsite.cache_market_context (
  id uuid primary key default gen_random_uuid(),
  cidade text not null,
  uf text,
  bairro text not null,
  cidade_slug text not null,
  bairro_slug text not null,
  conteudo_md text not null,
  tier text not null default 'cache',
  fontes jsonb not null default '[]'::jsonb,
  cached_at timestamptz not null default now(),
  expires_at timestamptz not null,
  last_hit_at timestamptz,
  hit_count integer not null default 0,
  created_by_relatorio_id uuid
);

create unique index if not exists cache_market_context_key_uq
  on gymsite.cache_market_context (cidade_slug, uf, bairro_slug);

create index if not exists cache_market_context_expires_idx
  on gymsite.cache_market_context (expires_at);

create index if not exists cache_market_context_last_hit_idx
  on gymsite.cache_market_context (last_hit_at);

create table if not exists gymsite.cache_places_details (
  place_id text primary key,
  payload jsonb not null,
  status text not null default 'ok',
  source text,
  cached_at timestamptz not null default now(),
  expires_at timestamptz not null,
  last_hit_at timestamptz,
  hit_count integer not null default 0
);

create index if not exists cache_places_details_expires_idx
  on gymsite.cache_places_details (expires_at);

create table if not exists gymsite.cache_popular_times (
  place_id text primary key,
  payload jsonb,
  status text not null default 'ok',
  cached_at timestamptz not null default now(),
  expires_at timestamptz not null,
  last_hit_at timestamptz,
  hit_count integer not null default 0
);

create index if not exists cache_popular_times_expires_idx
  on gymsite.cache_popular_times (expires_at);

create table if not exists gymsite.cache_reviews (
  place_id text primary key,
  reviews jsonb not null default '[]'::jsonb,
  source text,
  cached_at timestamptz not null default now(),
  expires_at timestamptz not null,
  hit_count integer not null default 0
);

create index if not exists cache_reviews_expires_idx
  on gymsite.cache_reviews (expires_at);

alter table gymsite.cache_market_context enable row level security;
alter table gymsite.cache_places_details enable row level security;
alter table gymsite.cache_popular_times enable row level security;
alter table gymsite.cache_reviews enable row level security;

grant usage on schema gymsite to service_role;
grant all on table gymsite.cache_market_context to service_role;
grant all on table gymsite.cache_places_details to service_role;
grant all on table gymsite.cache_popular_times to service_role;
grant all on table gymsite.cache_reviews to service_role;

revoke all on table gymsite.cache_market_context from anon, authenticated;
revoke all on table gymsite.cache_places_details from anon, authenticated;
revoke all on table gymsite.cache_popular_times from anon, authenticated;
revoke all on table gymsite.cache_reviews from anon, authenticated;

comment on table gymsite.cache_popular_times is
  'Cache popular times por place_id (schema gymsite; GYMSITE_SCHEMA_SEP=1). TTL ok=7d, sem=1d.';
