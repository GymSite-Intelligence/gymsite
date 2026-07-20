-- Compat view: PostgREST expõe public.*; tabela viva em gymsite.analise_gratuita
-- (migration 20260621). Escrita/upsert deve usar tbl() com GYMSITE_SCHEMA_SEP=1
-- (sb.schema('gymsite').table) — INSERT via view simples não é suportado.

CREATE OR REPLACE VIEW public.analise_gratuita
WITH (security_invoker = true) AS
SELECT
    id,
    email,
    ip,
    relatorio_id,
    user_agent,
    utm,
    created_at
FROM gymsite.analise_gratuita;

COMMENT ON VIEW public.analise_gratuita IS
    'Compat view → gymsite.analise_gratuita (entitlement N3 landing).';
