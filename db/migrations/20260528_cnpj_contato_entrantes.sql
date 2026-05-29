-- Contato e identificação nos estabelecimentos RFB + cache de enriquecimento QSA

alter table cnpj_fitness_estabelecimentos
  add column if not exists bairro text,
  add column if not exists email text,
  add column if not exists telefone text,
  add column if not exists razao_social text;

comment on column cnpj_fitness_estabelecimentos.bairro is
  'Bairro do layout Estabelecimentos RFB (coluna 17).';
comment on column cnpj_fitness_estabelecimentos.email is
  'E-mail do estabelecimento no cartão CNPJ (RFB).';
comment on column cnpj_fitness_estabelecimentos.telefone is
  'Telefone DDD+numero do estabelecimento (RFB).';
comment on column cnpj_fitness_estabelecimentos.razao_social is
  'Razão social da empresa (Empresas RFB ou cache ReceitaWS).';

create index if not exists idx_cnpj_fitness_bairro
  on cnpj_fitness_estabelecimentos (cidade, bairro);

-- Cache de consulta ReceitaWS / enriquecimento QSA (evita 3 req/min em todo relatório)
create table if not exists cnpj_contato_cache (
  cnpj text primary key,
  razao_social text,
  nome_fantasia text,
  email text,
  telefone text,
  bairro text,
  municipio text,
  uf text,
  qsa jsonb not null default '[]'::jsonb,
  socio_administrador jsonb,
  fonte text not null default 'receitaws',
  enriched_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create index if not exists idx_cnpj_contato_cache_expires
  on cnpj_contato_cache (expires_at);

comment on table cnpj_contato_cache is
  'Cache server-side de cartão CNPJ (QSA, contatos). TTL ~90 dias.';
