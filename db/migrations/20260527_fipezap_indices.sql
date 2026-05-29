-- ============================================================================
-- Migration: Tabela fipezap_indices
-- Data: 2026-05-27
-- Objetivo: Armazenar séries históricas do Índice FipeZap (residencial + comercial)
-- para consulta no A4 FinancialEstimator em vez de benchmarks hardcoded.
-- ============================================================================

create type fipezap_tipo_indice as enum (
  'venda_residencial',
  'locacao_residencial',
  'rentabilidade_residencial',
  'venda_comercial',
  'locacao_comercial',
  'rentabilidade_comercial'
);

comment on type fipezap_tipo_indice is 'Tipos de índice disponibilizados pelo FipeZap.';


create table fipezap_indices (
  id uuid primary key default gen_random_uuid(),

  cidade text not null,
  uf char(2),
  tipo_indice fipezap_tipo_indice not null,
  data_referencia date not null,  -- primeiro dia do mês

  -- Valores principais
  numero_indice numeric(12,4),          -- índice com base 100
  variacao_mensal_pct numeric(6,3),     -- variação vs mês anterior
  variacao_12m_pct numeric(6,3),        -- variação vs 12 meses atrás
  preco_medio_m2 numeric(10,2),         -- R$/m² médio do mês

  -- Metadados
  fonte text not null default 'FipeZap',
  arquivo_origem text,                  -- nome do arquivo Excel processado
  updated_by text,                      -- quem/script que fez o último upsert

  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  -- Um registro por cidade + tipo + mês
  unique (cidade, tipo_indice, data_referencia)
);

comment on table fipezap_indices is 'Série histórica mensal do Índice FipeZap por cidade e tipo de índice. Atualizada mensalmente via script tools/fipezap_loader.py.';

-- Índices para lookup rápido no A4
create index idx_fipezap_lookup on fipezap_indices(cidade, tipo_indice, data_referencia desc);
create index idx_fipezap_data on fipezap_indices(data_referencia desc);
create index idx_fipezap_cidade_uf on fipezap_indices(cidade, uf);

-- Trigger updated_at
 create or replace function _update_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_fipezap_indices_updated_at
  before update on fipezap_indices
  for each row execute function _update_updated_at();


-- ============================================================================
-- VIEW: último valor disponível por cidade + tipo (lookup rápido pro A4)
-- ============================================================================
create or replace view v_fipezap_ultimo as
select distinct on (cidade, tipo_indice)
  id,
  cidade,
  uf,
  tipo_indice,
  data_referencia,
  numero_indice,
  variacao_mensal_pct,
  variacao_12m_pct,
  preco_medio_m2,
  fonte,
  updated_at
from fipezap_indices
order by cidade, tipo_indice, data_referencia desc;

comment on view v_fipezap_ultimo is 'Snapshot do último mês disponível do FipeZap por cidade e tipo. Usada pelo A4 como Tier 1.5 de aluguel.';


-- ============================================================================
-- Política RLS (tabela de referência pública — readable por todos, writable só service role)
-- ============================================================================
alter table fipezap_indices enable row level security;

-- Todos os usuários autenticados podem ler (dados de mercado são referência pública)
create policy "fipezap readable by all auth users" on fipezap_indices
  for select using (auth.role() = 'authenticated' or auth.role() = 'anon');

-- Escrita fica restrita ao service role (bypass RLS) ou via script local com service key
