-- =============================================================================
-- Notas de progresso da tarefa (Playbook F2, item 1)
-- Diário de andamento append-only: a nota é o próprio registro histórico,
-- nunca é editada nem apagada fisicamente (deleted_at para ocultar).
-- =============================================================================

CREATE TABLE IF NOT EXISTS tarefa_notas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
    autor_user_id UUID,
    autor_nome TEXT NOT NULL,
    origem TEXT NOT NULL DEFAULT 'DONO' CHECK (origem IN ('DONO','EXTERNO','IA')),
    texto TEXT NOT NULL CHECK (length(trim(texto)) > 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tarefa_notas_tarefa ON tarefa_notas(tarefa_id, criado_em DESC);

ALTER TABLE tarefa_notas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tarefa_notas_user" ON tarefa_notas;
CREATE POLICY "tarefa_notas_user" ON tarefa_notas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM tarefas t
            JOIN user_projects up ON up.id = t.projeto_id
            WHERE t.id = tarefa_notas.tarefa_id
            AND up.user_id = auth.uid()
        )
    );
