-- GymSite: diagnose Supabase Auth 500 (admin list / signup / checking email)
-- Run each block in SQL Editor. Paste postgres_logs ERROR lines back if stuck.

-- A) Remaining NULLs in auth.users (GoTrue scan fails on these)
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
  role IS NULL AS role,
  instance_id IS NULL AS instance_id
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
   OR instance_id IS NULL;

-- B) Count bad rows
SELECT count(*) AS bad_user_rows
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
   OR role IS NULL;

-- C) Triggers on auth.users (broken trigger = signup 500)
SELECT tgname, pg_get_triggerdef(t.oid) AS definition
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'auth' AND c.relname = 'users' AND NOT t.tgisinternal;

-- D) Postgres errors — use Dashboard → Logs → Postgres (filter supabase_auth_admin)
--    SQL Editor has no `logs` view on all plans. Skip if relation "logs" does not exist.

-- E) Trigger function bodies (paste to agent if signup still 500)
SELECT p.proname, pg_get_functiondef(p.oid) AS definition
FROM pg_proc p
WHERE p.proname IN ('handle_new_user_profile', 'enforce_company_domain');
