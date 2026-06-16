-- =============================================================================
-- 20260613_criterio_verificacao.sql
-- Apêndice B (SIPOC/PDCA): critério de aceite por etapa = o que o Responsável
-- verifica no Check (Customer acceptance criteria). Afirmação verificável.
-- =============================================================================
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS criterio_verificacao TEXT;

-- ROLLBACK: ALTER TABLE tarefas DROP COLUMN IF EXISTS criterio_verificacao;
