-- Crosswalk código RFB ↔ código IBGE de município (5570). Destrava a leitura das
-- tabelas CNO (RFB dá só o código RFB; o pipeline consulta por IBGE de buscar_municipio).
-- Carregado de basedosdados.br_bd_diretorios_brasil.municipio (crosswalk timeless).
-- Dados curados em data/municipio_rf_ibge.json (o loader usa o JSON; tabela serve SQL/backfill).

create table if not exists public.municipio_rf_ibge (
  id_municipio_rf text primary key,
  id_municipio    text not null,
  fonte           text not null default 'basedosdados.br_bd_diretorios_brasil.municipio',
  updated_at      timestamptz not null default now()
);
create index if not exists idx_mun_rf_ibge_ibge on public.municipio_rf_ibge (id_municipio);
alter table public.municipio_rf_ibge enable row level security;

-- Backfill id_municipio (IBGE) nas obras CNO carregadas só com código RFB:
-- update public.cno_obras_grande_porte g set id_municipio = m.id_municipio
--   from public.municipio_rf_ibge m
--   where g.id_municipio_rf = m.id_municipio_rf and g.id_municipio is null;
-- (idem cno_obras_fitness). Seed dos 5570 via scripts (BQ → tabela), não no DDL.