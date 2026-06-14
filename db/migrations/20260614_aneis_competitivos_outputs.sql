-- Anéis competitivos (Apêndice D) no output do relatório: score ponderado por
-- proximidade (NO_BAIRRO 1.0 / FRONTEIRA 0.5 / REGIONAL 0.2) — corrige score puxado
-- pela força do vizinho (caso Wally/Cocó).
alter table public.relatorio_outputs
  add column if not exists aneis_competitivos jsonb not null default '{}'::jsonb;

comment on column public.relatorio_outputs.aneis_competitivos is
  'Anéis competitivos (Apêndice D): por_anel, score_competitivo_ponderado, '
  'concorrentes_no_bairro, no_bairro_por_porte.';
