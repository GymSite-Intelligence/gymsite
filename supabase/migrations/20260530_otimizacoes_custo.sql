-- ============================================================================
-- Migration: Governança de Otimização de Custo
-- Data: 2026-05-30
-- Objetivo: Workflow formal de análise, proposta, aprovação e implementação
-- de otimizações de custo no pipeline ADK.
--
-- Fonte: docs/GOVERNANCA_CUSTO.md
-- ============================================================================

create type if not exists otimizacao_status as enum (
  'pendente', 'aprovada', 'rejeitada', 'implementada', 'cancelada'
);

create type if not exists otimizacao_tipo as enum (
  'MODELO_OVERPRICED',
  'FLASH_PARA_LITE',
  'AGENTE_VORAZ',
  'ERRO_REPETIDO',
  'CACHE_GEOCODING',
  'OUTRO'
);

create table if not exists otimizacoes_custo (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,

  -- Quem criou a proposta (sistema ou usuário)
  criado_por uuid references auth.users(id) on delete set null,
  criado_em timestamptz default now(),

  -- Identificação da proposta
  tipo otimizacao_tipo not null,
  agente text not null,
  modelo_atual text,
  modelo_sugerido text,
  titulo text not null,
  descricao text not null,
  economia_brl_estimada numeric(10,4) not null default 0,
  severidade text not null check (severidade in ('alta', 'media', 'baixa')),

  -- Status do workflow
  status otimizacao_status not null default 'pendente',

  -- Aprovação
  aprovado_por uuid references auth.users(id) on delete set null,
  aprovado_em timestamptz,
  justificativa_aprovacao text,

  -- Implementação
  implementado_por uuid references auth.users(id) on delete set null,
  implementado_em timestamptz,
  resultado_observacao text,
  economia_brl_real numeric(10,4),

  -- Metadata
  referencia_dados jsonb  -- snapshot dos dados que geraram a proposta
);

create index if not exists idx_otimizacoes_org on otimizacoes_custo(org_id);
create index if not exists idx_otimizacoes_status on otimizacoes_custo(status);
create index if not exists idx_otimizacoes_agente on otimizacoes_custo(agente);
create index if not exists idx_otimizacoes_severidade on otimizacoes_custo(severidade);

comment on table otimizacoes_custo is
  'Propostas de otimização de custo do pipeline. Workflow: pendente → aprovada → implementada (ou rejeitada/cancelada).';

-- RLS
alter table otimizacoes_custo enable row level security;

create policy "otimizacoes follow org" on otimizacoes_custo
  for all
  to authenticated
  using (org_id in (select org_id from organization_members where user_id = auth.uid()))
  with check (org_id in (select org_id from organization_members where user_id = auth.uid()));
