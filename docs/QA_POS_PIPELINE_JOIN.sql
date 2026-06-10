-- Regra de ouro (fase de testes): rodar após cada relatório status = 'done'
-- Substitua o UUID em WHERE r.id = '...'::uuid
--
-- Uso: Supabase SQL Editor ou psql. Exporte JSON da 1ª linha para diff com golden.

select
  r.*,
  ri.cidade,
  ri.uf,
  ri.bairro,
  ri.area_m2_min,
  ri.area_m2_max,
  ri.tamanho_preset,
  ri.publico_alvo,
  ri.genero_alvo,
  ri.tipo_negocio,
  ri.estacionamento_obrigatorio,
  ri.bairros_indicados,
  ri.metadados as input_metadados,
  ro.veredito,
  ro.score_bairro,
  ro.score_top1_candidato,
  ro.score_demografico,
  ro.score_concorrencia,
  ro.score_viabilidade,
  ro.nivel_saturacao,
  ro.rating_medio_concorrentes,
  ro.total_concorrentes_analisados,
  ro.modelo_recomendado,
  ro.aluguel_mensal,
  ro.fonte_aluguel,
  ro.posicionamento_recomendado,
  ro.resumo_executivo,
  ro.justificativa_financeira,
  ro.market_context,
  ro.alertas as output_alertas,
  coalesce(c.candidatos, '[]'::json) as candidatos,
  coalesce(cp.competidores, '[]'::json) as competidores,
  coalesce(cf.cenarios_financeiros, '[]'::json) as cenarios_financeiros,
  coalesce(sc.sensibilidade_cenarios, '[]'::json) as sensibilidade_cenarios,
  coalesce(ba.bairros_alternativos, '[]'::json) as bairros_alternativos,
  coalesce(ca.custos_agentes, '[]'::json) as custos_agentes,
  coalesce(ac.api_calls, '[]'::json) as api_calls,
  v.validacao_id,
  v.status_validacao,
  v.score_validacao,
  v.alertas as validacao_alertas,
  v.claims_verificadas,
  v.claims_com_alertas,
  v.fontes_independentes,
  v.resumo_executivo_validacao,
  v.revisar_manual,
  v.payload as validacao_payload
from public.relatorios r
left join public.relatorio_inputs ri on ri.relatorio_id = r.id
left join public.relatorio_outputs ro on ro.relatorio_id = r.id
left join lateral (
  select json_agg(to_jsonb(x) order by x.posicao) as candidatos
  from public.candidatos x
  where x.relatorio_id = r.id
) c on true
left join lateral (
  select json_agg(to_jsonb(x) order by x.rating_oficial desc nulls last, x.num_avaliacoes desc nulls last) as competidores
  from public.competidores x
  where x.relatorio_id = r.id
) cp on true
left join lateral (
  select json_agg(to_jsonb(x) order by x.modelo) as cenarios_financeiros
  from public.cenarios_financeiros x
  where x.relatorio_id = r.id
) cf on true
left join lateral (
  select json_agg(to_jsonb(x) order by x.modelo, x.stress_id) as sensibilidade_cenarios
  from public.sensibilidade_cenarios x
  where x.relatorio_id = r.id
) sc on true
left join lateral (
  select json_agg(to_jsonb(x) order by x.ordem, x.prioridade desc nulls last) as bairros_alternativos
  from public.bairros_alternativos x
  where x.relatorio_id = r.id
) ba on true
left join lateral (
  select json_agg(to_jsonb(x) order by x.custo_brl desc nulls last) as custos_agentes
  from public.relatorio_custos_agentes x
  where x.relatorio_id = r.id
) ca on true
left join lateral (
  select json_agg(to_jsonb(x) order by x.created_at) as api_calls
  from public.relatorio_api_calls x
  where x.relatorio_id = r.id
) ac on true
left join public.validacoes v on v.relatorio_id = r.id
where r.id = '828df620-c299-433d-b568-9b9fe724d7f3'::uuid;

-- Checklist rápido (fase teste) — falhar QA se:
--   json_array_length(candidatos::json) = 0 mas markdown cita Top 3
--   json_array_length(competidores::json) = 0 mas markdown lista academias
--   ro.veredito <> trecho "Decisão Recomendada" do markdown_completo
--   (ro.market_context->>'cached')::boolean = true e data_coleta > 90 dias
--   ro.score_concorrencia is null e total_concorrentes_analisados = 0 com alerta zero conc
