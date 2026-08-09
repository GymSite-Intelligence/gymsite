-- cnpj_basico on shared base table; public view is a thin SELECT *
-- (GymSite: public.cnpj_fitness_estabelecimentos → shared.cnpj_fitness_estabelecimentos)

alter table shared.cnpj_fitness_estabelecimentos
  add column if not exists cnpj_basico text;

update shared.cnpj_fitness_estabelecimentos
set cnpj_basico = left(cnpj, 8)
where cnpj_basico is null
  and cnpj is not null
  and length(cnpj) >= 8;

create index if not exists idx_cnpj_fitness_basico
  on shared.cnpj_fitness_estabelecimentos (cnpj_basico);

create index if not exists idx_cnpj_fitness_situacao_data
  on shared.cnpj_fitness_estabelecimentos (situacao_cadastral, data_situacao_cadastral);

comment on column shared.cnpj_fitness_estabelecimentos.cnpj_basico is
  'CNPJ raiz (8 dígitos). Cluster multiunidade = mesma raiz com >=2 estab. ativos fitness no BR.';

-- Recreate public view so cnpj_basico is visible to PostgREST / clients
create or replace view public.cnpj_fitness_estabelecimentos as
select
  id,
  ref_month,
  cnpj,
  municipio_codigo,
  uf,
  cidade,
  cnae_fiscal_principal,
  cnaes_secundarios,
  data_inicio_atividade,
  situacao_cadastral,
  data_situacao_cadastral,
  nome_fantasia,
  cep,
  logradouro,
  numero,
  complemento,
  created_at,
  segmento_operacao,
  bairro,
  email,
  telefone,
  razao_social,
  cnpj_basico
from shared.cnpj_fitness_estabelecimentos;
