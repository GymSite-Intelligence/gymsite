-- ============================================================================
-- Migration: Tabela relatorio_custos_agentes
-- Data: 2026-05-30
-- Objetivo: Telemetria de custos LLM por agente (breakdown do pipeline ADK)
--
-- Essa tabela estava sendo usada pelo código (api.py) mas nunca foi criada
-- formalmente no schema. Esta migration corrige essa inconsistência.
-- ============================================================================

create table if not exists relatorio_custos_agentes (
  relatorio_id uuid not null references relatorios(id) on delete cascade,
  agente text not null,
  modelo text not null default '',
  tokens_in bigint not null default 0,
  tokens_out bigint not null default 0,
  custo_brl numeric(10,6) not null default 0.0,

  -- Chave composta: um registro por relatório + agente
  primary key (relatorio_id, agente)
);

create index if not exists idx_custos_agentes_relatorio on relatorio_custos_agentes(relatorio_id);

comment on table relatorio_custos_agentes is
  'Breakdown de custos LLM por agente e por relatório. Populado automaticamente pelo pipeline ADK via _agregar_e_persistir_custos.';

-- RLS: herda acesso do relatorio
alter table relatorio_custos_agentes enable row level security;

create policy "custos_agentes follow relatorio" on relatorio_custos_agentes
  for all using (
    relatorio_id in (
      select id from relatorios where org_id in (select user_org_ids())
    )
  );
