-- Migration: 20260713_user_projects_consultor_v2_columns.sql
-- gymsite.user_projects já tem acoes/pesquisas_realizadas/custo_brl_ate_agora e
-- gymsite.project_messages já tem agente — mas as views de compat em public ficaram
-- desatualizadas (criadas antes dessas colunas). PostgREST lê public → PGRST204.

CREATE OR REPLACE VIEW public.user_projects
WITH (security_invoker = true) AS
SELECT
    id,
    user_id,
    org_id,
    status,
    nome,
    intencao_principal,
    localizacao,
    modelo_negocio,
    concorrencia,
    mercado,
    candidatos,
    financeiro,
    posicionamento,
    anexos,
    relatorio_id,
    created_at,
    updated_at,
    deleted_at,
    acoes,
    pesquisas_realizadas,
    custo_brl_ate_agora
FROM gymsite.user_projects;

CREATE OR REPLACE VIEW public.project_messages
WITH (security_invoker = true) AS
SELECT
    id,
    projeto_id,
    role,
    content,
    tool_calls,
    tool_results,
    tokens_entrada,
    tokens_saida,
    created_at,
    agente
FROM gymsite.project_messages;

COMMENT ON VIEW public.user_projects IS
    'Compat view → gymsite.user_projects (inclui colunas Consultor V2).';

COMMENT ON VIEW public.project_messages IS
    'Compat view → gymsite.project_messages (inclui agente ADK por resposta).';
