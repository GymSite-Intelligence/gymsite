-- Patch token NULLs on CI audit users ONLY (no ALTER, no broad backfill).
-- Run AFTER bootstrap creates gymsite-security-audit-a/b@getgymsite.com.br
-- and BEFORE password login / GitHub Actions CI.
--
-- Hosted Supabase: UPDATE on specific rows usually works; ALTER auth.users does not.

BEGIN;

UPDATE auth.users
SET
  confirmation_token         = COALESCE(confirmation_token, ''),
  recovery_token             = COALESCE(recovery_token, ''),
  email_change_token_new     = COALESCE(email_change_token_new, ''),
  email_change               = COALESCE(email_change, ''),
  email_change_token_current = COALESCE(email_change_token_current, ''),
  reauthentication_token     = COALESCE(reauthentication_token, ''),
  phone_change_token         = COALESCE(phone_change_token, ''),
  phone_change               = COALESCE(phone_change, ''),
  aud                        = COALESCE(aud, 'authenticated'),
  role                       = COALESCE(role, 'authenticated')
WHERE email LIKE 'gymsite-security-audit-%';

COMMIT;

-- Verify (expect all false)
SELECT email,
  confirmation_token IS NULL AS confirmation_token_null,
  recovery_token IS NULL AS recovery_token_null
FROM auth.users
WHERE email LIKE 'gymsite-security-audit-%';

-- Then test login:
--   .venv\Scripts\python.exe scripts\setup_github_security_audit_secrets.py --push-credentials
-- (with SECURITY_AUDIT_USER_A_EMAIL/PASSWORD from bootstrap output or gh secrets)
