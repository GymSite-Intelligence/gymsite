-- =============================================================================
-- Playbook F2, item 3 — fundação para formulários por papel:
-- pessoas do projeto, anexos de tarefa/nota e responsável por passo.
-- =============================================================================

-- 1. Pessoas do projeto (contador, arquiteto, sócio — externos sem login)
CREATE TABLE IF NOT EXISTS projeto_pessoas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID NOT NULL REFERENCES user_projects(id) ON DELETE CASCADE,
    nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    papel TEXT,
    email TEXT,
    telefone TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_projeto_pessoas_projeto ON projeto_pessoas(projeto_id);

ALTER TABLE projeto_pessoas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "projeto_pessoas_user" ON projeto_pessoas;
CREATE POLICY "projeto_pessoas_user" ON projeto_pessoas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_projects up
            WHERE up.id = projeto_pessoas.projeto_id
            AND up.user_id = auth.uid()
        )
    );

-- 2. Vínculo pessoa → tarefa (dono da entrega) e → passo (executor do passo)
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS responsavel_pessoa_id UUID REFERENCES projeto_pessoas(id);
ALTER TABLE tarefa_checklist ADD COLUMN IF NOT EXISTS responsavel_pessoa_id UUID REFERENCES projeto_pessoas(id);

-- 3. Anexos (GUIA, comprovante, contrato) — arquivo no Storage, metadado aqui.
--    nota_id opcional: anexo pode chegar grudado numa anotação.
CREATE TABLE IF NOT EXISTS tarefa_anexos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    nota_id UUID REFERENCES tarefa_notas(id),
    nome_arquivo TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    content_type TEXT,
    tamanho_bytes BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tarefa_anexos_tarefa ON tarefa_anexos(tarefa_id, criado_em DESC);

ALTER TABLE tarefa_anexos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_anexos_user" ON tarefa_anexos;
CREATE POLICY "tarefa_anexos_user" ON tarefa_anexos
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM tarefas t
            JOIN user_projects up ON up.id = t.projeto_id
            WHERE t.id = tarefa_anexos.tarefa_id
            AND up.user_id = auth.uid()
        )
    );

-- 4. Bucket privado. Sem policy em storage.objects: só o backend
--    (service role) lê/escreve; download pro usuário via signed URL.
INSERT INTO storage.buckets (id, name, public)
VALUES ('execucao-anexos', 'execucao-anexos', false)
ON CONFLICT (id) DO NOTHING;
