-- =============================================================================
-- 20260613_execucao_raci_aprovacao.sql
-- Wave 0 do PLAN: RACI (tarefa_participantes), areas, tarefa_okrs,
-- status AGUARDANDO_APROVACAO, entrega/aprovação em tarefa_notas, setor da pessoa.
--
-- SPEC:  docs/produto/EXECUCAO_RESPONSAVEIS_INTERDEPENDENCIA.md (Apêndice A)
-- PLAN:  docs/produto/EXECUCAO_RESPONSAVEIS_INTERDEPENDENCIA_PLAN.md
--
-- Idempotente. Drops de CHECK via DO-block dinâmico (não depende do nome do
-- constraint). Aplicar em BRANCH do Supabase primeiro; validar contadores; merge.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 0.2  areas — vocabulário fixo (seed; sem CRUD de usuário — F2 §2/§7)
--      Criado antes de projeto_pessoas.area_slug (0.5) que o referencia.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS areas (
  slug         TEXT PRIMARY KEY,
  rotulo       TEXT NOT NULL,
  cor          TEXT NOT NULL,                  -- token de cor (ex.: 'var(--chart-1)')
  ordem        INT  NOT NULL DEFAULT 0,
  tipo_negocio TEXT NOT NULL DEFAULT 'academia'
);

INSERT INTO areas (slug, rotulo, cor, ordem) VALUES
  ('IMOBILIARIO','Imóvel','var(--chart-1)',1),
  ('LEGAL','Documentação','var(--chart-4)',2),
  ('OBRAS','Obra','var(--chart-3)',3),
  ('EQUIPAMENTOS','Equipamentos','var(--chart-5)',4),
  ('TECNOLOGIA','Tecnologia','var(--chart-2)',5),
  ('RH','Equipe','var(--chart-1)',6),
  ('MARKETING','Marketing','var(--chart-5)',7),
  ('FINANCEIRO','Financeiro','var(--chart-4)',8),
  ('OPERACIONAL','Operação','var(--chart-2)',9),
  ('OUTRO','Outros','var(--muted-foreground)',10)
ON CONFLICT (slug) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 0.1  Novo status AGUARDANDO_APROVACAO (drop dinâmico do CHECK de status)
-- -----------------------------------------------------------------------------
DO $$
DECLARE cname text;
BEGIN
  SELECT conname INTO cname
  FROM pg_constraint
  WHERE conrelid = 'tarefas'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) ILIKE '%A_FAZER%'
    AND pg_get_constraintdef(oid) ILIKE '%status%';
  IF cname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE tarefas DROP CONSTRAINT %I', cname);
  END IF;
END $$;

ALTER TABLE tarefas ADD CONSTRAINT tarefas_status_check
  CHECK (status IN ('A_FAZER','EM_ANDAMENTO','AGUARDANDO_APROVACAO','CONCLUIDA','BLOQUEADA','CANCELADA'));

-- -----------------------------------------------------------------------------
-- 0.3  tarefa_participantes — RACI N:N (RESPONDE/EXECUTA/CONSULTADO/INFORMADO)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tarefa_participantes (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tarefa_id  UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  pessoa_id  UUID NOT NULL REFERENCES projeto_pessoas(id) ON DELETE CASCADE,
  papel      TEXT NOT NULL DEFAULT 'EXECUTA'
             CHECK (papel IN ('RESPONDE','EXECUTA','CONSULTADO','INFORMADO')),
  criado_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (tarefa_id, pessoa_id, papel)
);
CREATE INDEX IF NOT EXISTS idx_tarefa_part_tarefa ON tarefa_participantes(tarefa_id);

ALTER TABLE tarefa_participantes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_part_user" ON tarefa_participantes;
CREATE POLICY "tarefa_part_user" ON tarefa_participantes FOR ALL USING (
  EXISTS (
    SELECT 1 FROM tarefas t
    JOIN playbooks p ON p.id = t.playbook_id
    WHERE t.id = tarefa_participantes.tarefa_id
      AND p.user_id = auth.uid()
  )
);

-- Migração de dados: responsável atual da tarefa vira participante RESPONDE
INSERT INTO tarefa_participantes (tarefa_id, pessoa_id, papel)
SELECT id, responsavel_pessoa_id, 'RESPONDE'
FROM tarefas
WHERE responsavel_pessoa_id IS NOT NULL
ON CONFLICT (tarefa_id, pessoa_id, papel) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 0.4  tarefa_okrs — N:N (substitui tarefas.okr_id morto; okr_id mantido por ora)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tarefa_okrs (
  tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  okr_id    UUID NOT NULL REFERENCES okrs(id) ON DELETE CASCADE,
  PRIMARY KEY (tarefa_id, okr_id)
);
ALTER TABLE tarefa_okrs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_okrs_user" ON tarefa_okrs;
CREATE POLICY "tarefa_okrs_user" ON tarefa_okrs FOR ALL USING (
  EXISTS (
    SELECT 1 FROM tarefas t
    JOIN playbooks p ON p.id = t.playbook_id
    WHERE t.id = tarefa_okrs.tarefa_id
      AND p.user_id = auth.uid()
  )
);

INSERT INTO tarefa_okrs (tarefa_id, okr_id)
SELECT id, okr_id FROM tarefas WHERE okr_id IS NOT NULL
ON CONFLICT (tarefa_id, okr_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 0.5  tarefa_notas: tipo (entrega/aprovação) + origem EXECUTOR ; pessoa.area_slug
--      O `texto` da nota tipo ENTREGA é o "o que foi entregue" (sem coluna nova).
-- -----------------------------------------------------------------------------
ALTER TABLE tarefa_notas
  ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'PROGRESSO'
  CHECK (tipo IN ('PROGRESSO','ENTREGA','APROVACAO','REPROVACAO'));

DO $$
DECLARE cname text;
BEGIN
  SELECT conname INTO cname
  FROM pg_constraint
  WHERE conrelid = 'tarefa_notas'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) ILIKE '%origem%'
    AND pg_get_constraintdef(oid) ILIKE '%DONO%';
  IF cname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE tarefa_notas DROP CONSTRAINT %I', cname);
  END IF;
END $$;
ALTER TABLE tarefa_notas ADD CONSTRAINT tarefa_notas_origem_check
  CHECK (origem IN ('DONO','EXTERNO','IA','EXECUTOR'));

ALTER TABLE projeto_pessoas
  ADD COLUMN IF NOT EXISTS area_slug TEXT REFERENCES areas(slug);

COMMIT;

-- =============================================================================
-- VALIDAÇÃO (rodar após o COMMIT, em branch):
--   SELECT count(*) FROM tarefa_participantes WHERE papel='RESPONDE';
--     -- deve = SELECT count(*) FROM tarefas WHERE responsavel_pessoa_id IS NOT NULL;
--   SELECT count(*) FROM tarefa_okrs;
--     -- deve = SELECT count(*) FROM tarefas WHERE okr_id IS NOT NULL;
--   SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--     WHERE conrelid='tarefas'::regclass AND contype='c';  -- confere AGUARDANDO_APROVACAO
-- =============================================================================

-- ROLLBACK (manual, se necessário — ordem inversa; exige nenhuma linha nos
-- estados/valores novos):
--   UPDATE tarefas SET status='EM_ANDAMENTO' WHERE status='AGUARDANDO_APROVACAO';
--   ALTER TABLE tarefas DROP CONSTRAINT tarefas_status_check;
--   ALTER TABLE tarefas ADD CONSTRAINT tarefas_status_check
--     CHECK (status IN ('A_FAZER','EM_ANDAMENTO','CONCLUIDA','BLOQUEADA','CANCELADA'));
--   ALTER TABLE projeto_pessoas DROP COLUMN IF EXISTS area_slug;
--   ALTER TABLE tarefa_notas DROP COLUMN IF EXISTS tipo;
--   ALTER TABLE tarefa_notas DROP CONSTRAINT tarefa_notas_origem_check;
--   ALTER TABLE tarefa_notas ADD CONSTRAINT tarefa_notas_origem_check
--     CHECK (origem IN ('DONO','EXTERNO','IA'));
--   DROP TABLE IF EXISTS tarefa_okrs;
--   DROP TABLE IF EXISTS tarefa_participantes;
--   DROP TABLE IF EXISTS areas;
