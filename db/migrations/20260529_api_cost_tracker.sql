-- db/migrations/20260529_api_cost_tracker.sql
-- Shadow Agent: Telemetria de Custos por Chamada de API

create table if not exists relatorio_api_calls (
  id uuid primary key default gen_random_uuid(),
  relatorio_id uuid not null references relatorios(id) on delete cascade,
  agente text not null,
  tool_name text not null,
  api_sku text not null,
  num_calls integer not null default 1,
  custo_brl numeric(10,6) not null default 0.0,
  created_at timestamptz not null default now()
);

create index if not exists idx_relatorio_api_calls_relatorio on relatorio_api_calls(relatorio_id);

-- Habilitar RLS
alter table relatorio_api_calls enable row level security;

-- Políticas de RLS
create policy "api_calls follow relatorio" on relatorio_api_calls
  for all using (
    relatorio_id in (
      select id from relatorios where org_id in (select user_org_ids())
    )
  );
