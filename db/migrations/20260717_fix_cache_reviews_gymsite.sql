-- Align gymsite.cache_reviews with public + set_reviews() (reviews/source).
-- 20260717_cache_tables_gymsite.sql wrongly copied places shape (payload/status).

drop table if exists gymsite.cache_reviews;

create table gymsite.cache_reviews (
  place_id text primary key,
  reviews jsonb not null default '[]'::jsonb,
  source text,
  cached_at timestamptz not null default now(),
  expires_at timestamptz not null,
  hit_count integer not null default 0
);

create index if not exists cache_reviews_expires_idx
  on gymsite.cache_reviews (expires_at);

alter table gymsite.cache_reviews enable row level security;

grant all on table gymsite.cache_reviews to service_role;
revoke all on table gymsite.cache_reviews from anon, authenticated;

insert into gymsite.cache_reviews (place_id, reviews, source, cached_at, expires_at, hit_count)
select place_id, reviews, source, cached_at, expires_at, coalesce(hit_count, 0)
from public.cache_reviews
on conflict (place_id) do update set
  reviews = excluded.reviews,
  source = excluded.source,
  cached_at = excluded.cached_at,
  expires_at = excluded.expires_at,
  hit_count = excluded.hit_count;

comment on table gymsite.cache_reviews is
  'Cache SearchAPI google_maps_reviews por place_id (schema gymsite; GYMSITE_SCHEMA_SEP=1). TTL 7d.';
