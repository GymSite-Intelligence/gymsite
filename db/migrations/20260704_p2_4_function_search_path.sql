-- ============================================================================
-- P2.4 (docs/SECURITY_REVIEW.md): search_path fixo + revoke da SECURITY DEFINER
-- Projeto: epgedaiukjippepujuzc — 2026-07-04 (JÁ APLICADA em prod via MCP)
--
-- 1) search_path mutável (risco de hijack via schema) nas 3 funções flagadas.
--    Todas as refs de tabela já são qualificadas (gymsite.user_projects,
--    vectraclip.prospect_profiles) + built-ins pg_catalog → search_path='' não
--    altera a lógica, só fixa a resolução de nomes.
-- 2) public.sync_gymsite_oportunidade_to_prospect é SECURITY DEFINER com EXECUTE
--    default a PUBLIC (o vetor "anon executa função definer"). É trigger function
--    (RETURNS trigger → não chamável via RPC), então revogar de PUBLIC não afeta o
--    disparo do trigger GymSite→Vectra (verificado: trigger segue ativo).
-- ============================================================================

alter function gymsite.marcar_pesquisa(uuid, text, uuid) set search_path = '';
alter function gymsite.trg_oportunidade_status_guard() set search_path = '';
alter function public.sync_gymsite_oportunidade_to_prospect() set search_path = '';

revoke execute on function public.sync_gymsite_oportunidade_to_prospect() from public, anon, authenticated;

-- ROLLBACK:
--   alter function gymsite.marcar_pesquisa(uuid, text, uuid) reset search_path;
--   alter function gymsite.trg_oportunidade_status_guard() reset search_path;
--   alter function public.sync_gymsite_oportunidade_to_prospect() reset search_path;
--   grant execute on function public.sync_gymsite_oportunidade_to_prospect() to public;
