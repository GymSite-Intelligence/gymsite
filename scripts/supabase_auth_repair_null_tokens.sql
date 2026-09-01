-- Repair NULL token fields on ALL auth.users rows that need it (no ALTER, no phone).
-- GoTrue list/login scans the whole table — one bad row breaks every auth read path.
-- Run AFTER supabase_auth_find_bad_users.sql shows bad_rows > 0.

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
WHERE confirmation_token IS NULL
   OR recovery_token IS NULL
   OR email_change_token_new IS NULL
   OR email_change IS NULL
   OR email_change_token_current IS NULL
   OR reauthentication_token IS NULL
   OR phone_change_token IS NULL
   OR phone_change IS NULL
   OR aud IS NULL
   OR role IS NULL;

COMMIT;

-- Optional: remove dev test user
-- DELETE FROM auth.identities WHERE user_id IN (SELECT id FROM auth.users WHERE email LIKE 'gymsite-security-audit-test-%');
-- DELETE FROM public.profiles WHERE email LIKE 'gymsite-security-audit-test-%';
-- DELETE FROM auth.users WHERE email LIKE 'gymsite-security-audit-test-%';
