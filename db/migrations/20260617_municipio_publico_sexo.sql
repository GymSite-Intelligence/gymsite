-- Espelho município → split sexo×idade do público fitness (Censo 2022), populado do
-- BigQuery basedosdados.populacao_idade_sexo via tools/municipio_publico_sexo_loader.py.
-- Motivo: BQ-runtime falha no Cloud Run (sem acesso BigQuery); o gancho sexo×idade lê
-- daqui (Supabase funciona em prod). Mesmo padrão de censo_setor / IPECE.
-- PK composta (id_municipio, faixa_idade): TODAS as faixas por município (granular 5 anos
-- 0-4…100+ + segmentos fitness 15-24/25-39/40-59/60+/18-45/25-40). 149k linhas.
create table if not exists municipio_publico_sexo (
  id_municipio text not null,
  faixa_idade  text not null,
  homens       integer not null,
  mulheres     integer not null,
  total        integer not null,
  pct_homens   numeric(4,1) not null,
  pct_mulheres numeric(4,1) not null,
  fonte        text default 'IBGE Censo 2022 (populacao_idade_sexo via BigQuery basedosdados)',
  updated_at   timestamptz default now(),
  primary key (id_municipio, faixa_idade)
);
create index if not exists idx_mps_faixa on municipio_publico_sexo(faixa_idade);
-- RLS on, service-role-only (sem policies) — padrão do projeto.
alter table municipio_publico_sexo enable row level security;
