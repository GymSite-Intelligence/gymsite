-- Obras fitness em andamento (CNO) no output do relatório
alter table relatorio_outputs
  add column if not exists obras_cno_em_curso jsonb not null default '{}'::jsonb;

comment on column relatorio_outputs.obras_cno_em_curso is
  'Obras fitness em curso no município (CNO RFB), pré-computado no A6.';
