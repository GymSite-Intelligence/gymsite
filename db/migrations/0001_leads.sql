-- 0001_leads.sql — tabela de captura de leads da landing (gym-insight-hub).
--
-- Aplicar no projeto Supabase cargo-flow-navigator (mesmo cluster do GymSite).
-- Idempotente: pode rodar mais de uma vez sem erro.
--
-- Consumida por backend/routers/leads.py (POST /api/leads). A landing e
-- anonima, entao a escrita acontece pelo backend com a service_role key;
-- nao ha leitura direta pelo anon role (RLS bloqueia por padrao).

create extension if not exists "pgcrypto";

create table if not exists public.leads (
    id                   uuid primary key default gen_random_uuid(),
    org_id               uuid not null default '00000000-0000-0000-0000-000000000001',
    nome                 text not null,
    email                text not null,
    telefone             text,
    cidade               text,
    bairro               text,
    perfil               text,              -- vou_abrir | ja_opero | ...
    empresa              text,
    mensagem             text,
    utm_source           text,
    utm_medium           text,
    utm_campaign         text,
    fonte                text not null default 'landing-getgymsite',
    apollo_sync_status   text not null default 'pendente',  -- pendente|sincronizado|erro
    apollo_contact_id    text,
    apollo_synced_at     timestamptz,
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

create index if not exists leads_email_idx       on public.leads (lower(email));
create index if not exists leads_org_created_idx  on public.leads (org_id, created_at desc);
create index if not exists leads_apollo_status_idx on public.leads (apollo_sync_status);

-- updated_at automatico
create or replace function public.tg_leads_touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists trg_leads_touch on public.leads;
create trigger trg_leads_touch
    before update on public.leads
    for each row execute function public.tg_leads_touch_updated_at();

-- RLS: ligado. Sem policies de SELECT/INSERT para anon/authenticated, ou seja
-- a landing NAO le nem escreve direto — quem grava e o backend (service_role,
-- que faz bypass de RLS). Membros da org podem LER os proprios leads via app.
alter table public.leads enable row level security;

drop policy if exists "leads_select_por_org" on public.leads;
create policy "leads_select_por_org" on public.leads
    for select
    using (org_id in (select user_org_ids()));

-- Nenhuma policy de INSERT/UPDATE para roles publicos: somente service_role.

comment on table public.leads is
    'Leads capturados na landing (gym-insight-hub). Escrita via backend service_role; sync com Apollo via tools/apollo_client.py.';
