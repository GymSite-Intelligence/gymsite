-- ============================================================================
-- GymSite Intelligence — Seed inicial
-- Cria organização Vectra interna + bootstrap. Aplicar APÓS schema.sql.
-- ============================================================================

-- Org interna Vectra (sua org de uso pessoal/equipe)
insert into organizations (id, nome, slug, plano, limite_relatorios_mes)
values (
  '00000000-0000-0000-0000-000000000001',
  'Vectra Cargo',
  'vectra',
  'enterprise',
  9999
)
on conflict (slug) do nothing;

-- IMPORTANTE: depois que você criar seu user via Supabase Auth (signup),
-- pegue o user_id e rode manualmente:
--
--   insert into organization_members (org_id, user_id, role)
--   values (
--     '00000000-0000-0000-0000-000000000001',
--     '<seu-user-id>',
--     'owner'
--   );
--
-- Ou execute o script seed_link_user.sql passando o user_id como variável.
