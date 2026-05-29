-- CNPJ Fitness (CNAE 9313-1/00 = 9313100) — snapshots mensais RFB
--
-- Objetivo:
-- - Medir histórico de aberturas/entrantes (mensal) por município
-- - Detectar "novos entrantes" (ex: últimos 90 dias) para enriquecer A0/A6
--
-- Fonte: Dados Abertos CNPJ (RFB) — Estabelecimentos*.zip (layout oficial)
-- https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/

create table if not exists cnpj_fitness_estabelecimentos (
  id uuid primary key default gen_random_uuid(),

  -- Snapshot de referência (YYYY-MM-01). Ex: 2026-05-01 para pasta 2026-05.
  ref_month date not null,

  -- Identificador da unidade (CNPJ completo 14 dígitos)
  cnpj text not null,

  -- Localização (código município conforme layout RFB)
  municipio_codigo text,
  uf text,
  cidade text,

  -- Atividade econômica
  cnae_fiscal_principal text,
  cnaes_secundarios text,

  -- Datas e situação
  data_inicio_atividade date,
  situacao_cadastral integer,
  data_situacao_cadastral date,

  -- Identificação
  nome_fantasia text,

  -- Endereço (para geocode posterior; bairro não é confiável na RFB)
  cep text,
  logradouro text,
  numero text,
  complemento text,

  created_at timestamptz not null default now()
);

-- Evita duplicação no mesmo snapshot
create unique index if not exists uq_cnpj_fitness_ref_cnpj
  on cnpj_fitness_estabelecimentos(ref_month, cnpj);

create index if not exists idx_cnpj_fitness_ref_month
  on cnpj_fitness_estabelecimentos(ref_month);

create index if not exists idx_cnpj_fitness_municipio
  on cnpj_fitness_estabelecimentos(municipio_codigo);

create index if not exists idx_cnpj_fitness_cnae_principal
  on cnpj_fitness_estabelecimentos(cnae_fiscal_principal);

create index if not exists idx_cnpj_fitness_data_inicio
  on cnpj_fitness_estabelecimentos(data_inicio_atividade);

comment on table cnpj_fitness_estabelecimentos is
  'Snapshots mensais de estabelecimentos com CNAE fitness (9313100) do CNPJ Aberto RFB.';

