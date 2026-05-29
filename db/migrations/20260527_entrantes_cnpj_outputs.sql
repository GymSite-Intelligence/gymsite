-- Lista de novos entrantes CNPJ (90d) no output do relatório (schema v1.7)

alter table relatorio_outputs
  add column if not exists entrantes_cnpj_90d jsonb not null default '{}'::jsonb;

comment on column relatorio_outputs.entrantes_cnpj_90d is
  'Novos estabelecimentos fitness (CNAE 9313100) com abertura nos últimos N dias — snapshot RFB.';
