-- Coluna do bloco de demanda futura datada no output do relatório (Apêndice B).
-- Obras residenciais no raio → moradores → pool/captura fitness em T+24 + refino A4.
alter table public.relatorio_outputs
  add column if not exists demanda_futura jsonb not null default '{}'::jsonb;

comment on column public.relatorio_outputs.demanda_futura is
  'Demanda futura datada: CNO grande porte (RFB) + refino A4 das top obras. '
  'Campos: n_obras, provavel_residencial_n, obras[], captura_total_est, janela_entrega.';
