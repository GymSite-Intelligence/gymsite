-- Market Atlas: expõe A9 na listagem + metadados de wave (opcional por relatório).

alter table relatorios
  add column if not exists market_wave text
    check (market_wave is null or market_wave in ('red', 'transition', 'blue'));

alter table relatorios
  add column if not exists market_tier_qwen text;

comment on column relatorios.market_wave is
  'Onda do Market Atlas: red | transition | blue (catalogo data/market_waves.csv).';
comment on column relatorios.market_tier_qwen is
  'Arquetipo Qwen: capital_bairro, primeiro_movimento, ultra_premium, etc.';

-- Postgres exige que colunas novas fiquem no FINAL da view (CREATE OR REPLACE).
create or replace view v_relatorios_resumo as
select
  r.id,
  r.org_id,
  r.user_id,
  r.tipo_relatorio,
  r.status,
  r.data_execucao,
  r.tempo_execucao_segundos,
  r.custo_brl,
  i.cidade,
  i.uf,
  i.bairro,
  i.area_m2_min,
  i.area_m2_max,
  i.publico_alvo,
  i.tipo_negocio,
  o.veredito,
  o.score_bairro,
  o.score_top1_candidato,
  o.modelo_recomendado,
  o.aluguel_mediana_m2,
  o.nivel_saturacao,
  r.created_at,
  upper(trim(o.posicionamento_estrategico->>'veredito_posicionamento')) as veredito_posicionamento,
  (o.posicionamento_estrategico->'recomendacao_ticket'->>'ticket_recomendado')::numeric as ticket_recomendado,
  case
    when o.posicionamento_estrategico->'gaps_identificados' is null then null
    when jsonb_typeof(o.posicionamento_estrategico->'gaps_identificados') = 'array'
      then jsonb_array_length(o.posicionamento_estrategico->'gaps_identificados')
    else null
  end as gaps_count,
  r.market_wave,
  r.market_tier_qwen
from relatorios r
left join relatorio_inputs i on i.relatorio_id = r.id
left join relatorio_outputs o on o.relatorio_id = r.id;

comment on view v_relatorios_resumo is
  'Listagem flat: A6 veredito + A9 posicionamento (oceano) + wave Atlas.';
