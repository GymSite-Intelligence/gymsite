-- Obras de grande porte do CNO (proxy de empreendimento residencial multi-unidade)
-- mineradas do BigQuery basedosdados → demanda futura datada (Apêndice B do Motor v2).
-- Proxy: area > 2000 m² + não-fitness + não-comercial-óbvio. Confiança declarada.
-- Carga nacional, consulta por município no read. Server-side: service_role bypassa RLS.
-- Plano: docs/arquitetura/PLANO_ENRIQUECIMENTO_RELATORIO.md §2.1.

create table if not exists public.cno_obras_grande_porte (
  id_cno              text primary key,
  nome                text,
  area_m2             double precision,
  cep                 text,
  tipo_logradouro     text,
  logradouro          text,
  numero_logradouro   text,
  bairro              text,
  sigla_uf            text,
  id_municipio        text,
  id_municipio_rf     text,
  situacao            text,
  em_curso            boolean,
  data_inicio         date,
  data_situacao       date,
  ni_responsavel      text,
  fonte               text not null default 'basedosdados.br_me_cno',
  raw                 jsonb,
  updated_at          timestamptz not null default now()
);

create index if not exists idx_cno_gp_municipio_rf on public.cno_obras_grande_porte (id_municipio_rf);
create index if not exists idx_cno_gp_uf            on public.cno_obras_grande_porte (sigla_uf);
create index if not exists idx_cno_gp_em_curso      on public.cno_obras_grande_porte (em_curso);

alter table public.cno_obras_grande_porte enable row level security;
