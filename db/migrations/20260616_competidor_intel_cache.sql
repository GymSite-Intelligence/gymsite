-- Cache persistente/compartilhado de inteligência de concorrente (SearchAPI Instagram
-- + planos + serviços), keyed por place_id. Substitui o cache de arquivo (não persiste
-- no Cloud Run). Freshness via collected_at + TTL (param). Aplicado em prod 2026-06-16.

create table if not exists public.competidor_intel_cache (
  place_id            text primary key,
  instagram_username  text,
  cidade              text,
  bairro              text,
  profile             jsonb,         -- followers, bio, external_link...
  posts_slim          jsonb,         -- por post: {type, likes, comments, views, date, caption} (sem URL)
  metricas            jsonb,         -- mix_formato, eng_rate, cadencia, post_campeao, servicos
  planos_precos       jsonb,         -- oferta (reaproveita o A3a grounding)
  servicos            jsonb,         -- serviços detectados (captions + inclui) → alimenta a ERRC
  collected_at        timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- Service-role only: RLS ON + 0 policy (deny anon/authenticated), como o demais ref data.
alter table public.competidor_intel_cache enable row level security;

create index if not exists idx_cic_collected on public.competidor_intel_cache (collected_at);
create index if not exists idx_cic_username  on public.competidor_intel_cache (instagram_username);

comment on table public.competidor_intel_cache is
  'Cache de inteligencia de concorrente (IG marketing + planos + servicos) keyed por place_id; freshness via collected_at + TTL param; service-role only.';
