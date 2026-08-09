-- 20260808_explorar_gratuita.sql — 1 pesquisa no mapa / e-mail (degustação site).
-- Separado de analise_gratuita: especialistas (chat + form) não queimam o mapa,
-- e 1 Analisar no Explorar não queima a análise gratuita dos especialistas.

create table if not exists gymsite.explorar_gratuita (
    id            uuid primary key default gen_random_uuid(),
    email         text not null,
    ip            text,
    user_agent    text,
    cidade        text,
    bairro        text,
    uf            text,
    created_at    timestamptz not null default now()
);

create unique index if not exists explorar_gratuita_email_uniq
    on gymsite.explorar_gratuita (lower(email));

create index if not exists explorar_gratuita_ip_idx
    on gymsite.explorar_gratuita (ip, created_at desc);

alter table gymsite.explorar_gratuita enable row level security;

comment on table gymsite.explorar_gratuita is
    'Entitlement de 1 pesquisa no mapa (/explorar) por e-mail na degustação do site. Service_role only.';

create or replace view public.explorar_gratuita
with (security_invoker = true) as
select id, email, ip, user_agent, cidade, bairro, uf, created_at
from gymsite.explorar_gratuita;

comment on view public.explorar_gratuita is
    'Compat view → gymsite.explorar_gratuita.';
