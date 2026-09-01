-- bad_rows = 0 but GoTrue still 500: check auth.identities for NULL string columns
SELECT i.id, u.email, i.provider,
  i.provider_id IS NULL AS provider_id_null,
  i.identity_data IS NULL AS identity_data_null
FROM auth.identities i
JOIN auth.users u ON u.id = i.user_id
WHERE i.provider_id IS NULL OR i.identity_data IS NULL;

SELECT count(*) AS bad_identities FROM auth.identities
WHERE provider_id IS NULL OR identity_data IS NULL;

-- Dashboard → Logs → Postgres (filter supabase_auth_admin) at login time
-- If identities clean: open Supabase support ticket — auth read path broken despite clean token columns
