-- Migration: adiciona estados do fluxo de confirmação à CHECK de sessions
-- O fix do BUG-001 (conversational_engine) introduziu o estado
-- aguardando_confirmacao, mas a CHECK original de sessions só aceitava
-- coletando_slots|pipeline_rodando|respondendo|encerrado — o UPDATE do
-- engine violaria a constraint e derrubaria o chat com 500.

ALTER TABLE sessions DROP CONSTRAINT IF EXISTS chat_sessions_status_check;
ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_status_check;
ALTER TABLE sessions ADD CONSTRAINT sessions_status_check
    CHECK (status IN (
        'coletando_slots',
        'aguardando_confirmacao',
        'pronto_para_pipeline',
        'pipeline_rodando',
        'respondendo',
        'encerrado'
    ));
