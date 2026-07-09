-- Task #30 (auditoria quadro Receita e Custos, run b7199c7c):
-- O motor fiscal v1.3 calcula Fator R / Anexo / tributos e já desconta do lucro,
-- mas os campos não eram persistidos — o quadro não fechava na conferência
-- (Receita − Custos ≠ Lucro) e auditor externo concluiu "ausência de tributação".
-- Colunas aditivas; runs antigos ficam NULL (viewer mostra "—").

ALTER TABLE gymsite.cenarios_financeiros
  ADD COLUMN IF NOT EXISTS fator_r numeric,
  ADD COLUMN IF NOT EXISTS anexo_simples text,
  ADD COLUMN IF NOT EXISTS aliquota_tributos numeric,
  ADD COLUMN IF NOT EXISTS tributos_mensal numeric(12,2);

COMMENT ON COLUMN gymsite.cenarios_financeiros.fator_r IS
  'Folha/receita (LC 123/2006). >=0.28 -> Anexo III, senão Anexo V.';
COMMENT ON COLUMN gymsite.cenarios_financeiros.tributos_mensal IS
  'Simples Nacional estimado/mês (receita x alíquota do anexo). Lucro já é líquido deste valor.';
