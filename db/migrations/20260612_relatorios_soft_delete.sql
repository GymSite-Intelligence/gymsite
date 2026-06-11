-- Migration: soft delete em relatorios (P-007)
-- DeleteRelatorioButton fazia DELETE físico com cascade — relatório, outputs,
-- candidatos e validações sumiam de verdade. Agora deleted_at marca e a view
-- do dashboard filtra; tabelas filhas permanecem intactas para auditoria.

ALTER TABLE relatorios ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_relatorios_deleted ON relatorios(deleted_at) WHERE deleted_at IS NOT NULL;

CREATE OR REPLACE VIEW v_relatorios_resumo AS
 SELECT r.id,
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
    upper(TRIM(BOTH FROM o.posicionamento_estrategico ->> 'veredito_posicionamento'::text)) AS veredito_posicionamento,
    ((o.posicionamento_estrategico -> 'recomendacao_ticket'::text) ->> 'ticket_recomendado'::text)::numeric AS ticket_recomendado,
        CASE
            WHEN (o.posicionamento_estrategico -> 'gaps_identificados'::text) IS NULL THEN NULL::integer
            WHEN jsonb_typeof(o.posicionamento_estrategico -> 'gaps_identificados'::text) = 'array'::text THEN jsonb_array_length(o.posicionamento_estrategico -> 'gaps_identificados'::text)
            ELSE NULL::integer
        END AS gaps_count,
    r.market_wave,
    r.market_tier_qwen
   FROM relatorios r
     LEFT JOIN relatorio_inputs i ON i.relatorio_id = r.id
     LEFT JOIN relatorio_outputs o ON o.relatorio_id = r.id
  WHERE r.deleted_at IS NULL;
