-- A9 PositioningStrategist: relatório ERRC / oceano azul anexado ao output do A6
ALTER TABLE relatorio_outputs
  ADD COLUMN IF NOT EXISTS posicionamento_estrategico jsonb;

COMMENT ON COLUMN relatorio_outputs.posicionamento_estrategico IS
  'Output A9: framework_errc, mapa_servicos, gaps_identificados, recomendacao_ticket, veredito_posicionamento';
