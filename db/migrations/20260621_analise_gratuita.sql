-- 20260621_analise_gratuita.sql — entitlement "1 análise gratuita" da landing (N3).
--
-- Aplicado 2026-06-22 nos schemas gymsite/shared (flags GYMSITE_SCHEMA_SEP=1 +
-- SHARED_SCHEMA_SEP=1 já ON em prod). A versão original apontava pra public.* —
-- corrigida pra os schemas vivos. Idempotente.
-- Consumida por backend/routers/site_agent.py (que DEVE usar tools.db_schema.tbl()
-- p/ rotear gymsite/shared — sb.table() cru bate em public e não enxerga estas tabelas).
--
-- Run anônimo: gymsite.relatorios.user_id NULL + org_id = ANON_ORG (isola
-- métricas/custo do tenant real). Leitura do resultado pela landing acontece via
-- backend (service_role) validando gymsite.relatorios.access_token — anon role
-- bloqueado por RLS.

create extension if not exists "pgcrypto";

-- 1. Org dedicada aos runs gratuitos anônimos (schema SHARED — tenancy).
--    limite_relatorios_mes alto: o teto real é o entitlement por email + cap
--    diário por IP + allowance do SearchAPI, não a org.
insert into shared.organizations (id, nome, slug, plano, limite_relatorios_mes)
values (
    '00000000-0000-0000-0000-0000000000a0',
    'Landing — Análise Gratuita (anon)',
    'landing-anon',
    'free',
    1000000
)
on conflict (id) do nothing;

-- 2. gymsite.relatorios.access_token — token não-adivinhável p/ leitura anônima via backend.
alter table gymsite.relatorios add column if not exists access_token uuid;
create index if not exists idx_relatorios_access_token
    on gymsite.relatorios (access_token);

-- 3. Entitlement: 1 análise gratuita por email; IP rastreado p/ cap diário.
create table if not exists gymsite.analise_gratuita (
    id            uuid primary key default gen_random_uuid(),
    email         text not null,
    ip            inet,
    relatorio_id  uuid references gymsite.relatorios(id) on delete set null,
    user_agent    text,
    utm           jsonb,
    created_at    timestamptz not null default now()
);

-- 1 grátis por email (case-insensitive): a 2ª tentativa do mesmo email falha o
-- insert → backend trata como quota_used (vira lead quente).
create unique index if not exists analise_gratuita_email_uniq
    on gymsite.analise_gratuita (lower(email));

-- cap por IP/dia: consulta por (ip, created_at desc).
create index if not exists analise_gratuita_ip_idx
    on gymsite.analise_gratuita (ip, created_at desc);

-- RLS: ligado, sem policies públicas — só o backend (service_role) escreve/lê.
alter table gymsite.analise_gratuita enable row level security;

comment on table gymsite.analise_gratuita is
    'Entitlement de 1 análise gratuita por visitante (email) na landing. Escrita via backend service_role; relatorio_id liga ao run anônimo (gymsite.relatorios.user_id NULL, org ANON 00000000-0000-0000-0000-0000000000a0 em shared.organizations).';
