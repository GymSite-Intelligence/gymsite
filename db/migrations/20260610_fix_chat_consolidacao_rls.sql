-- Migration: consolida chat_sessions/sessions duplicadas e cria RLS de chat
-- Contexto (auditoria 360 de 2026-06-10):
--   1. A migration de rename rodou, mas a CREATE de chat_sessions rodou de novo
--      depois — as duas tabelas coexistem em produção e o código gravava na antiga.
--   2. sessions/messages estavam com RLS ativa e ZERO policies — o insert direto
--      do frontend em messages (useConversationalChat) era bloqueado em silêncio.

-- 1. Migrar dados remanescentes da tabela antiga (mesmas colunas)
INSERT INTO sessions (id, user_id, intencao, slots, relatorio_id, status, messages, created_at, updated_at)
SELECT id, user_id, intencao, slots, relatorio_id, status, messages, created_at, updated_at
FROM chat_sessions
ON CONFLICT (id) DO NOTHING;

-- 2. Aposentar a tabela antiga sem apagar dados (P-007: nada é destruído)
ALTER TABLE chat_sessions RENAME TO chat_sessions_deprecated_20260610;

-- 3. RLS de sessions: usuário opera apenas as próprias sessões
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "sessions_own" ON sessions;
CREATE POLICY "sessions_own" ON sessions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 4. RLS de messages: acesso via posse da sessão (frontend insere direto)
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "messages_own_select" ON messages;
CREATE POLICY "messages_own_select" ON messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.id = messages.session_id
            AND s.user_id = auth.uid()
        )
    );
DROP POLICY IF EXISTS "messages_own_insert" ON messages;
CREATE POLICY "messages_own_insert" ON messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.id = messages.session_id
            AND s.user_id = auth.uid()
        )
    );

-- 5. Tabela aposentada fica trancada (RLS ativa, sem policies = só service role)
ALTER TABLE chat_sessions_deprecated_20260610 ENABLE ROW LEVEL SECURITY;
