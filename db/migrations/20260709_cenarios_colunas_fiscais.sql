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

-- ARMADILHA (custou 3 runs): o worker grava via VIEW espelho public.cenarios_financeiros,
-- que tem lista EXPLÍCITA de colunas. Coluna nova no gymsite precisa entrar aqui também
-- (no FIM — CREATE OR REPLACE não reordena), senão a API devolve PGRST204.
CREATE OR REPLACE VIEW public.cenarios_financeiros AS
SELECT id, relatorio_id, modelo, ticket_medio, matriculas_conservador,
       matriculas_realista, matriculas_agressivo, matr_por_m2_realista,
       capacidade_simultanea_pico, frequencia_semanal_aluno, pico_share,
       alunos_pico_calculado, folga_capacidade_pct, capacidade_maxima_alunos,
       alunos_projetados, alunos_break_even, ticket_realizado_estimado,
       taxa_inadimplencia, taxa_cancelamento_mensal, receita_mensal,
       custo_aluguel, custo_condominio, custo_iptu, custo_energia, custo_agua,
       custo_internet, custo_folha, custo_manutencao, custo_contabilidade,
       custo_sistema_gestao, custo_seguro, custo_outros, custos_fixos_total,
       marketing_pct_faturamento, marketing_mensal, custos_totais,
       lucro_mensal_estimado, margem_percentual,
       capex_equipamentos, capex_obra_adaptacao, capex_projeto_arquitetonico,
       capex_alvara_e_taxas, capex_contingencia_pct, capex_contingencia_valor,
       capex_total, capital_giro_meses, capital_giro, investimento_total,
       payback_meses, tir_anual_pct, vpl_5_anos, viabilidade, justificativa,
       capex_estimado, custos_fixos,
       fator_r, anexo_simples, aliquota_tributos, tributos_mensal
FROM gymsite.cenarios_financeiros;

NOTIFY pgrst, 'reload schema';
