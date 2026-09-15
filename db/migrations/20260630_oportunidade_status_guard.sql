-- Invariante de status das oportunidades de prospecção.
--
-- Problema: o status (novo/qualificado/webhook_enviado/...) podia regredir pra
-- 'novo'/'qualificado' mesmo depois do lead já ter sido enviado ao Navi
-- (webhook_enviado_at setado), exigindo backfills manuais. O fluxo bulk
-- "Qualificar + Enviar ao Navi" fazia patchStatus('qualificado') e, quando o
-- webhook era idempotente (já enviado), o status ficava preso em 'qualificado'.
--
-- Fonte do problema atacada em 2 camadas:
--   1. App (commit ff464ec): bulk só qualifica 'novo'; idempotente reafirma status.
--   2. Banco (esta migration): trigger BEFORE na TABELA BASE garante o invariante
--      independente de quem escreve (app, bulk, manual, código futuro).
--
-- Obs: public.oportunidades_prospeccao é uma VIEW; a base real é
-- gymsite.oportunidades_prospeccao (schema gymsite). O trigger vai na base — a
-- view propaga o UPDATE pra cá. Convive com trg_oportunidades_updated_at e
-- trg_sync_gymsite_to_prospect (BEFORE 'o' < 't' → corrige status antes do sync).

CREATE OR REPLACE FUNCTION gymsite.trg_oportunidade_status_guard()
RETURNS trigger AS $$
BEGIN
  -- Depois de enviado ao Navi, status nunca volta pra novo/qualificado.
  -- Estados forward (engajado/fechado/descartado) seguem permitidos.
  IF NEW.webhook_enviado_at IS NOT NULL
     AND NEW.status IN ('novo', 'qualificado') THEN
    NEW.status := 'webhook_enviado';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS oportunidade_status_guard ON gymsite.oportunidades_prospeccao;
CREATE TRIGGER oportunidade_status_guard
  BEFORE INSERT OR UPDATE ON gymsite.oportunidades_prospeccao
  FOR EACH ROW EXECUTE FUNCTION gymsite.trg_oportunidade_status_guard();

-- Backfill idempotente: alinha qualquer lead já enviado que esteja atrasado.
UPDATE gymsite.oportunidades_prospeccao
SET status = 'webhook_enviado'
WHERE webhook_enviado_at IS NOT NULL
  AND status IN ('novo', 'qualificado');
