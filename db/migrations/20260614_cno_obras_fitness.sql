-- Destino das obras fitness do CNO, mineradas do BigQuery basedosdados
-- (basedosdados.br_me_cno.microdados) — carga NACIONAL, consulta por município no read.
-- Espelha o padrão da Trilha 3 (parque CNPJ). Server-side: service_role bypassa RLS.
-- Detalhe da rota: docs/arquitetura/COMPILADO_FONTES_DADOS.md §7.

create table if not exists public.cno_obras_fitness (
  id_cno                  text primary key,
  nome                    text,            -- nome_empresarial || nome_responsavel (display)
  nome_empresarial        text,
  nome_responsavel        text,
  area_m2                 double precision,
  cep                     text,
  tipo_logradouro         text,
  logradouro              text,
  numero_logradouro       text,
  bairro                  text,
  sigla_uf                text,
  id_municipio            text,            -- código IBGE
  id_municipio_rf         text,            -- código Receita (o "1389" de Fortaleza)
  situacao                text,            -- 01-04 em curso · 15 encerrada
  em_curso                boolean,         -- situacao in (01..04)
  data_inicio             date,
  data_situacao           date,
  ni_responsavel          text,            -- CNPJ/CPF responsável (cruzamento CNAE 9313100)
  qualificacao_responsavel text,
  metodo_classificacao    text,            -- keyword | cnpj_cnae | cnpj_cnae_area_atipica
  fonte                   text not null default 'basedosdados.br_me_cno',
  raw                     jsonb,
  updated_at              timestamptz not null default now()
);

create index if not exists idx_cno_obras_municipio_rf on public.cno_obras_fitness (id_municipio_rf);
create index if not exists idx_cno_obras_uf            on public.cno_obras_fitness (sigla_uf);
create index if not exists idx_cno_obras_em_curso      on public.cno_obras_fitness (em_curso);
create index if not exists idx_cno_obras_ni            on public.cno_obras_fitness (ni_responsavel);

alter table public.cno_obras_fitness enable row level security;
