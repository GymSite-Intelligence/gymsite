-- A8 Validador Cruzado — resultados pós-A6

create table if not exists validacoes (
  id uuid primary key default gen_random_uuid(),
  relatorio_id uuid not null references relatorios(id) on delete cascade,
  org_id uuid not null references organizations(id) on delete cascade,
  validacao_id text not null,
  status_validacao text not null,
  score_validacao numeric(4,2) not null default 0,
  alertas jsonb not null default '[]'::jsonb,
  claims_verificadas int not null default 0,
  claims_com_alertas int not null default 0,
  fontes_independentes text[] not null default '{}',
  resumo_executivo_validacao text not null default '',
  revisar_manual boolean not null default false,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_validacoes_relatorio on validacoes(relatorio_id);
create index if not exists idx_validacoes_org on validacoes(org_id);

alter table validacoes enable row level security;

create policy "validacoes_select_org" on validacoes
  for select using (org_id in (select user_org_ids()));

create policy "validacoes_insert_org" on validacoes
  for insert with check (org_id in (select user_org_ids()));

-- Pesquisa A0 por relatório (A/B Gemini vs Kimi no form)
alter table relatorio_inputs
  add column if not exists a0_research_provider text;

comment on column relatorio_inputs.a0_research_provider is
  'gemini | kimi | auto — provedor de Deep Research do A0 para este relatório.';
