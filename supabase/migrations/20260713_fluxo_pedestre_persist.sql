-- Persistência fluxo pedestre — tabelas base gymsite.* + views public.*

ALTER TABLE gymsite.relatorio_outputs
  ADD COLUMN IF NOT EXISTS fluxo_pedestre jsonb;

ALTER TABLE gymsite.candidatos
  ADD COLUMN IF NOT EXISTS fluxo_score numeric,
  ADD COLUMN IF NOT EXISTS fluxo_norm numeric,
  ADD COLUMN IF NOT EXISTS fluxo_confianca text,
  ADD COLUMN IF NOT EXISTS fluxo_segmento text,
  ADD COLUMN IF NOT EXISTS fluxo_carimbo jsonb;

COMMENT ON COLUMN gymsite.relatorio_outputs.fluxo_pedestre IS
  'Bloco A6: fluxo estrutural (OSM walk network + choice/integration + carimbo P-010).';
COMMENT ON COLUMN gymsite.candidatos.fluxo_score IS
  'Score 0-100 do candidato no segmento viário mais próximo (A1 enrich, raio 2km).';

CREATE OR REPLACE VIEW public.relatorio_outputs AS
 SELECT relatorio_id,
    veredito,
    score_bairro,
    score_top1_candidato,
    score_demografico,
    score_concorrencia,
    score_viabilidade,
    nivel_saturacao,
    rating_medio_concorrentes,
    total_concorrentes_analisados,
    modelo_recomendado,
    aluguel_mensal,
    fonte_aluguel,
    aluguel_min_m2,
    aluguel_max_m2,
    aluguel_mediana_m2,
    queries_aluguel_com_dados,
    posicionamento_recomendado,
    resumo_executivo,
    justificativa_financeira,
    contato_decisor,
    market_context,
    cobertura_redes_a0,
    alertas,
    embedding,
    entrantes_cnpj_90d,
    obras_cno_em_curso,
    posicionamento_estrategico,
    aluguel_amostras,
    aluguel_fonte_meta,
    demanda_futura,
    aneis_competitivos,
    demografia_bairro,
    zoneamento,
    fluxo_pedestre
   FROM gymsite.relatorio_outputs;

CREATE OR REPLACE VIEW public.candidatos AS
 SELECT id,
    relatorio_id,
    posicao,
    nome,
    endereco,
    place_id,
    tipo,
    area_estimada_m2,
    lat,
    lng,
    score_geoscout,
    score_ancoragem,
    score_geral,
    motivo,
    estimativa_visibilidade,
    avenida_principal,
    qualidade_sinal,
    polos_geradores,
    tipos_google,
    street_view_url,
    status_business,
    telefone,
    website,
    tem_24h,
    proximo_passo,
    created_at,
    listing_url,
    listing_id,
    price_raw,
    listing_source,
    tipo_imovel_codigo_onr,
    tipo_imovel_label,
    modalidade,
    cartorio,
    fluxo_score,
    fluxo_norm,
    fluxo_confianca,
    fluxo_segmento,
    fluxo_carimbo
   FROM gymsite.candidatos;
