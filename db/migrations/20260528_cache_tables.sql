-- ============================================================================
-- GymSite Intelligence — Cache tables (v1)
--
-- Objetivo:
-- - Persistir caches que hoje vivem no filesystem do container, para reuso
--   cross-deploy e redução de custo/latência (Gemini Deep Research, Places, etc.)
-- - Acesso recomendado: SOMENTE backend com service_role (sem RLS por padrão)
--
-- Tabelas:
-- - cache_market_context  (cidade/uf/bairro → markdown do Deep Research)
-- - cache_places_details  (place_id → JSON normalizado de details)
-- - cache_popular_times   (place_id → JSON de popular times)
-- ============================================================================

-- 1) cache_market_context -----------------------------------------------------
create table if not exists cache_market_context (
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
  on cache_market_context (cidade_slug, uf, bairro_slug);

create index if not exists cache_market_context_expires_idx
  on cache_market_context (expires_at);

create index if not exists cache_market_context_last_hit_idx
  on cache_market_context (last_hit_at);

comment on table cache_market_context is
  'Cache de Deep Research (Gemini Interactions/grounded) por cidade/UF/bairro. Recomenda-se acesso apenas via backend (service_role).';


-- 2) cache_places_details -----------------------------------------------------
create table if not exists cache_places_details (
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
  on cache_places_details (expires_at);

comment on table cache_places_details is
  'Cache de Google Places Details (New) por place_id. payload = JSON normalizado (nome/endereço/latlng/rating/telefone/website/etc).';


-- 3) cache_popular_times ------------------------------------------------------
create table if not exists cache_popular_times (
  place_id text primary key,
  payload jsonb,
  status text not null default 'ok',
  cached_at timestamptz not null default now(),
  expires_at timestamptz not null,
  last_hit_at timestamptz,
  hit_count integer not null default 0
);

create index if not exists cache_popular_times_expires_idx
  on cache_popular_times (expires_at);

comment on table cache_popular_times is
  'Cache de popular times por place_id. TTL recomendado: ok=7d, sem_popular_times=1d.';

