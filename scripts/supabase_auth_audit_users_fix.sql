-- Reset CI audit users only (hosted Supabase — no ALTER on auth.users).
--
-- Use when:
--   - admin API returns 500 / invalid_credentials
--   - audit users have providers=[] (no auth.identities email row)
--
-- Do NOT ALTER auth.users in hosted projects (42501 must be owner; can break Auth migrations).
-- Token/default repair: inspect Auth + Postgres logs first; escalate to Supabase support if needed.

BEGIN;

DELETE FROM public.profiles
WHERE email LIKE 'gymsite-security-audit-%';

DELETE FROM auth.identities
WHERE user_id IN (
  SELECT id FROM auth.users WHERE email LIKE 'gymsite-security-audit-%'
);

DELETE FROM auth.users
WHERE email LIKE 'gymsite-security-audit-%';

COMMIT;

-- Then locally:
--   1) .venv\Scripts\python.exe scripts\setup_github_security_audit_secrets.py --bootstrap
--   2) scripts/supabase_auth_audit_users_token_patch.sql  (if login HTTP 500)
--   3) gh secret list  /  gh workflow run security-audit.yml
