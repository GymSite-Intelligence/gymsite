-- Coluna categoria espelha o dict Python (_DEFAULTS):
--   benchmark | calibracao | aberto
-- Seed completo: python -m tools.parametros_seed
--
-- IMPORTANTE (schema split / GYMSITE_SCHEMA_SEP):
--   gymsite.parametros_metodologia = tabela real
--   public.parametros_metodologia  = VIEW de compat (PostgREST)
-- ADD COLUMN em view falha. Alterar sempre a tabela base.
-- Se a view NÃO refletir a coluna nova (SELECT * antigo / lista explícita),
-- recriar view no padrão de 20260713_user_projects_consultor_v2_columns.sql.

alter table gymsite.parametros_metodologia
  add column if not exists categoria text;

comment on column gymsite.parametros_metodologia.categoria is
  'benchmark | calibracao | aberto — ver tools/parametros_metodologia.py';
