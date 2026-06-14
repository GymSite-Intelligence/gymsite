-- =============================================================================
-- 20260613_passo_granular.sql
-- Granulariza o passo (checklist): critério de aceite por passo + vínculo
-- nota(andamento)->passo. Excluir o passo apaga as notas dele (feito no service,
-- pois o checklist é soft-delete; a FK CASCADE cobre hard-delete eventual).
-- =============================================================================
ALTER TABLE tarefa_checklist ADD COLUMN IF NOT EXISTS criterio_aceite TEXT;

ALTER TABLE tarefa_notas ADD COLUMN IF NOT EXISTS checklist_item_id UUID
  REFERENCES tarefa_checklist(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_tarefa_notas_checklist ON tarefa_notas(checklist_item_id);

-- ROLLBACK:
--   DROP INDEX IF EXISTS idx_tarefa_notas_checklist;
--   ALTER TABLE tarefa_notas DROP COLUMN IF EXISTS checklist_item_id;
--   ALTER TABLE tarefa_checklist DROP COLUMN IF EXISTS criterio_aceite;
