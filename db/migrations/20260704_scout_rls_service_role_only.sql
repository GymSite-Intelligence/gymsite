-- ============================================================================
-- Hardening scout: gymsite.prospects / scout_cadencia / scout_messages
-- Projeto: epgedaiukjippepujuzc — 2026-07-04
-- P1.1 do docs/SECURITY_REVIEW.md (defesa em profundidade do gate require_admin)
--
-- Contexto: o módulo scout é interno/admin-only e SINGLE-TENANT (as tabelas não
-- têm org_id). O único acesso legítimo é a API backend do GymSite via
-- service_role. Verificado: o front NÃO usa PostgREST direto p/ scout, e NENHUMA
-- edge function do projeto toca essas tabelas (todas são do cargo-flow-navigator).
--
-- Problema: policies "always true" + grants totais para authenticated/anon
-- expunham dado pessoal de sócios/decisores (prospects.decisor,
-- prospects.receita_federal, scout_messages.destinatario/conteudo) via PostgREST
-- a QUALQUER usuário logado. Quando o signup público do MVP abrir, cada cliente
-- teria JWT válido e alcançaria o módulo interno pela porta do PostgREST.
--
-- Correção: fecha authenticated/anon em DUAS camadas (policy + grant de tabela),
-- deixando apenas service_role. RLS permanece habilitado; sem policy aplicável,
-- authenticated/anon caem em deny-all. Reversível (rollback no fim).
-- ============================================================================

-- 1) Policies — remove as always-true de authenticated.
--    As policies scout_service_all_* (service_role, ALL) são preservadas.
--    Fecha LEITURA e ESCRITA (não só escrita): os SELECT authenticated=true
--    também vazavam o dado pessoal.
drop policy if exists scout_prospects_select on gymsite.prospects;
drop policy if exists scout_prospects_insert on gymsite.prospects;
drop policy if exists scout_prospects_update on gymsite.prospects;

drop policy if exists scout_cadencia_select on gymsite.scout_cadencia;
drop policy if exists scout_cadencia_update on gymsite.scout_cadencia;

drop policy if exists scout_msgs_select on gymsite.scout_messages;
drop policy if exists scout_msgs_update on gymsite.scout_messages;

-- 2) Grants de tabela — revoga anon/authenticated (camada abaixo do RLS).
--    service_role NÃO é tocado: mantém acesso total (a API).
revoke all on gymsite.prospects      from anon, authenticated;
revoke all on gymsite.scout_cadencia from anon, authenticated;
revoke all on gymsite.scout_messages from anon, authenticated;

-- ============================================================================
-- ROLLBACK (se algum acesso legítimo via authenticated for descoberto):
--
--   grant select, insert, update, delete
--     on gymsite.prospects, gymsite.scout_cadencia, gymsite.scout_messages
--     to authenticated;
--
--   create policy scout_prospects_select on gymsite.prospects
--     for select to authenticated using (true);
--   create policy scout_prospects_insert on gymsite.prospects
--     for insert to authenticated with check (true);
--   create policy scout_prospects_update on gymsite.prospects
--     for update to authenticated using (true);
--   create policy scout_cadencia_select on gymsite.scout_cadencia
--     for select to authenticated using (true);
--   create policy scout_cadencia_update on gymsite.scout_cadencia
--     for update to authenticated using (true);
--   create policy scout_msgs_select on gymsite.scout_messages
--     for select to authenticated using (true);
--   create policy scout_msgs_update on gymsite.scout_messages
--     for update to authenticated using (true);
-- ============================================================================
