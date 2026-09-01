-- GymSite: auth.users triggers (found in prod)
--   on_auth_user_created_profile  → handle_new_user_profile()
--   trg_enforce_company_domain    → enforce_company_domain()
--
-- Signup/admin 500 often = trigger raises or INSERT into missing table/column.
-- "logs" table: use Dashboard → Logs → Postgres (not SQL Editor).

-- 1) Read trigger function source (paste output back for fix)
SELECT p.proname, pg_get_functiondef(p.oid) AS definition
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.proname IN ('handle_new_user_profile', 'enforce_company_domain');

-- 2) profiles table exists? (handle_new_user_profile target)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'profiles'
ORDER BY ordinal_position;

-- 3) Isolate: disable triggers, test signup from app or bootstrap, re-enable
--    (run disable → test → enable in one session if nervous)
-- ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created_profile;
-- ALTER TABLE auth.users DISABLE TRIGGER trg_enforce_company_domain;
-- … test …
-- ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created_profile;
-- ALTER TABLE auth.users ENABLE TRIGGER trg_enforce_company_domain;

-- 4) Safe pattern for enforce_company_domain — allow CI audit mailboxes
--    (adapt domain list after reading function body from step 1)
/*
CREATE OR REPLACE FUNCTION public.enforce_company_domain()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.email ~* '@(getgymsite\.com\.br|vectra[^.]*\.com\.br)$'
     OR NEW.email ~* '^gymsite-security-audit-[ab]@'
  THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'signup blocked: email domain not allowed (%', NEW.email;
END;
$$;
*/

-- 5) Safe pattern for handle_new_user_profile — minimal insert, no missing cols
/*
CREATE OR REPLACE FUNCTION public.handle_new_user_profile()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;
*/

-- 6) Cleanup half-created audit users before re-bootstrap
-- DELETE FROM auth.users WHERE email LIKE 'gymsite-security-audit-%';
