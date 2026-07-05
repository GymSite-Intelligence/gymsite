-- ============================================================================
-- P1.2 (docs/SECURITY_REVIEW.md): v_relatorios_resumo → security_invoker
-- Projeto: epgedaiukjippepujuzc — 2026-07-04
--
-- Problema: a view public.v_relatorios_resumo era SECURITY DEFINER (default do
-- Postgres) → rodava com permissão do owner, IGNORANDO o RLS das tabelas base.
-- Único ERROR de advisor que toca o GymSite. Como o front consome a view via
-- Supabase JS (authenticated, useRelatorios.ts), qualquer usuário logado veria
-- relatórios de TODAS as orgs (vazamento cross-tenant — inócuo hoje com 1 org,
-- crítico quando o signup público abrir).
--
-- Correção: security_invoker=on → a view roda com a permissão do CALLER, então
-- o RLS por org das tabelas base passa a valer (policies mt_relatorios_select /
-- mt_relatorio_inputs_all / mt_relatorio_outputs_all, via org_id in user_org_ids()).
--
-- Seguro (verificado antes): authenticated tem GRANT SELECT nas 3 tabelas base;
-- 72 relatórios ativos em 1 org; 2 membros nessa org (veem tudo); 0 relatórios
-- órfãos. A API (service_role) não é afetada (bypassa RLS).
-- ============================================================================

alter view public.v_relatorios_resumo set (security_invoker = on);

-- ROLLBACK:
--   alter view public.v_relatorios_resumo reset (security_invoker);
