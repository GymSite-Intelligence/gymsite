-- Find ANY auth.users rows with NULL token fields (causes GoTrue list/login 500).
-- Does not ALTER schema. Run in SQL Editor.

SELECT id, email,
  confirmation_token IS NULL AS confirmation_token,
  recovery_token IS NULL AS recovery_token,
  email_change_token_new IS NULL AS email_change_token_new,
  email_change IS NULL AS email_change,
  email_change_token_current IS NULL AS email_change_token_current,
  reauthentication_token IS NULL AS reauthentication_token,
  phone_change_token IS NULL AS phone_change_token,
  phone_change IS NULL AS phone_change,
  aud IS NULL AS aud,
  role IS NULL AS role
FROM auth.users
WHERE confirmation_token IS NULL
   OR recovery_token IS NULL
   OR email_change_token_new IS NULL
   OR email_change IS NULL
   OR email_change_token_current IS NULL
   OR reauthentication_token IS NULL
   OR phone_change_token IS NULL
   OR phone_change IS NULL
   OR aud IS NULL
   OR role IS NULL
ORDER BY email;

-- Count only
SELECT count(*) AS bad_rows FROM auth.users
WHERE confirmation_token IS NULL OR recovery_token IS NULL
   OR email_change_token_new IS NULL OR email_change IS NULL
   OR email_change_token_current IS NULL OR reauthentication_token IS NULL
   OR phone_change_token IS NULL OR phone_change IS NULL
   OR aud IS NULL OR role IS NULL;

-- If bad_rows > 0: patch those rows (no phone column — UNIQUE):
-- UPDATE auth.users SET confirmation_token = COALESCE(confirmation_token,''), ...
-- WHERE <same WHERE as above>;

-- Orphan test user from dev (optional cleanup):
-- DELETE FROM auth.identities WHERE user_id IN (SELECT id FROM auth.users WHERE email LIKE 'gymsite-security-audit-test-%');
-- DELETE FROM auth.users WHERE email LIKE 'gymsite-security-audit-test-%';
