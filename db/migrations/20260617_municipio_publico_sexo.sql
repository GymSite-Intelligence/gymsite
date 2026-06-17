-- Espelho município → split sexo×idade do público fitness (Censo 2022), populado do
-- BigQuery basedosdados.populacao_idade_sexo via tools/municipio_publico_sexo_loader.py.
-- Motivo: BQ-runtime falha no Cloud Run (sem acesso BigQuery); o gancho sexo×idade lê
-- daqui (Supabase funciona em prod). Mesmo padrão de censo_setor / IPECE.
create table if not exists municipio_publico_sexo (
  id_municipio text primary key,
  faixa_idade  text not null,
  homens       integer not null,
  mulheres     integer not null,
  total        integer not null,
  pct_homens   numeric(4,1) not null,
  pct_mulheres numeric(4,1) not null,
  fonte        text default 'IBGE Censo 2022 (populacao_idade_sexo via BigQuery basedosdados)',
  updated_at   timestamptz default now()
);
-- RLS on, service-role-only (sem policies) — padrão do projeto.
alter table municipio_publico_sexo enable row level security;
