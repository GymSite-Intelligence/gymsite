-- Armazém compartilhado de market_bundle + snapshots setoriais.
-- Substitui leitura/escrita FS-local por Supabase, pro batch (GitHub Actions)
-- alimentar a API (Cloud Run) sem rebuild de imagem.
-- Server-side only: service_role bypassa RLS; sem policy pública.

create table if not exists public.market_bundles (
  slug        text primary key,
  cidade      text not null,
  bairro      text,
  uf          text not null,
  gerado_em   timestamptz,
  valido_ate  timestamptz,
  stale       boolean not null default false,
  payload     jsonb not null,
  updated_at  timestamptz not null default now()
);

create index if not exists idx_market_bundles_cidade_uf
  on public.market_bundles (cidade, uf);

alter table public.market_bundles enable row level security;

-- Snapshots globais (benchmark_snapshots, etc.) por nome.
create table if not exists public.market_snapshots (
  nome        text primary key,
  payload     jsonb not null,
  gerado_em   timestamptz,
  updated_at  timestamptz not null default now()
);

alter table public.market_snapshots enable row level security;

-- Manutenção SQL (pg_cron já instalado): marca expirado diariamente 04:00 UTC.
-- Staleness "real" é recomputada em Python no build; isto é só rede de segurança
-- caso o batch atrase e bundles passem do valido_ate.
do $$
begin
  perform cron.unschedule('market_bundles_mark_expired');
exception
  when others then null;
end $$;

select cron.schedule(
  'market_bundles_mark_expired',
  '0 4 * * *',
  $$update public.market_bundles
       set stale = true, updated_at = now()
     where valido_ate is not null
       and valido_ate < now()
       and stale = false$$
);
