-- DIAGNOSTIC ONLY — auth.users token NULLs (hosted Supabase)
-- Ref: https://supabase.com/docs/guides/troubleshooting/auth-error-500-database-error-querying-schema-eb6b44
--
-- WARNING (hosted Supabase):
--   - ALTER TABLE auth.users → 42501 must be owner; can break Auth migrations
--   - Broad UPDATE on auth.users → only with confirmed need + support guidance
--   - phone UNIQUE: never SET phone = '' for multiple rows
--
-- Preferred path for CI audit users: scripts/supabase_auth_audit_users_fix.sql (DELETE only)

-- 1) Count NULL token columns
SELECT
  count(*) FILTER (WHERE confirmation_token IS NULL) AS confirmation_token,
  count(*) FILTER (WHERE recovery_token IS NULL) AS recovery_token,
  count(*) FILTER (WHERE email_change_token_new IS NULL) AS email_change_token_new,
  count(*) FILTER (WHERE email_change IS NULL) AS email_change,
  count(*) FILTER (WHERE email_change_token_current IS NULL) AS email_change_token_current,
  count(*) FILTER (WHERE reauthentication_token IS NULL) AS reauthentication_token,
  count(*) FILTER (WHERE phone_change_token IS NULL) AS phone_change_token,
  count(*) FILTER (WHERE phone_change IS NULL) AS phone_change,
  count(*) FILTER (WHERE aud IS NULL) AS aud,
  count(*) FILTER (WHERE role IS NULL) AS role
FROM auth.users;

-- 2) If counts > 0: check Auth + Postgres logs (Dashboard → Logs) before any UPDATE.
--    scripts/supabase_auth_diagnose.sql — triggers, function bodies
--
-- 3) Optional UPDATE (run only if support/docs confirm; do NOT touch phone):
-- BEGIN;
-- UPDATE auth.users SET confirmation_token = COALESCE(confirmation_token, ''), ...
-- WHERE confirmation_token IS NULL OR ...;
-- COMMIT;
--
-- 4) Do NOT run ALTER TABLE auth.users on hosted projects.
