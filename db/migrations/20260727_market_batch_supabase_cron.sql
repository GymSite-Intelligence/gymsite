-- Batch semanal: Supabase pg_cron + pg_net → Cloud Run gymsite-worker.
-- Python não roda no Postgres; cron só dispara HTTP POST autenticado.
--
-- Pós-migrate (uma vez, via SQL editor service_role):
--   update gymsite.cron_http_targets
--      set url = 'https://<worker-host>/api/internal/cron/weekly-market-batch',
--          secret = '<mesmo MARKET_BATCH_CRON_SECRET do Cloud Run>',
--          enabled = true
--    where job_name = 'weekly_market_batch';

create extension if not exists pg_net with schema extensions;

create schema if not exists gymsite;

create table if not exists gymsite.cron_http_targets (
  job_name    text primary key,
  url         text not null,
  secret      text not null,
  enabled     boolean not null default false,
  updated_at  timestamptz not null default now()
);

comment on table gymsite.cron_http_targets is
  'Destinos HTTP para pg_cron (service_role). secret = X-Cron-Secret no Cloud Run.';

alter table gymsite.cron_http_targets enable row level security;

grant all on gymsite.cron_http_targets to service_role;

insert into gymsite.cron_http_targets (job_name, url, secret, enabled)
values (
  'weekly_market_batch',
  'https://api.getgymsite.com.br/api/internal/cron/weekly-market-batch',
  'CONFIGURE_ME',
  false
)
on conflict (job_name) do nothing;

create or replace function gymsite.invoke_cron_http(p_job_name text)
returns bigint
language plpgsql
security definer
set search_path = gymsite, public, extensions
as $$
declare
  t record;
  req_id bigint;
begin
  select job_name, url, secret, enabled
    into t
    from gymsite.cron_http_targets
   where job_name = p_job_name;

  if not found then
    raise exception 'cron job % not configured', p_job_name;
  end if;

  if not t.enabled then
    raise notice 'cron job % disabled — skip', p_job_name;
    return null;
  end if;

  if t.secret is null or t.secret = '' or t.secret = 'CONFIGURE_ME' then
    raise exception 'cron job % secret not configured', p_job_name;
  end if;

  select net.http_post(
    url := t.url,
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Cron-Secret', t.secret
    ),
    body := jsonb_build_object(
      'skip_enrichment', true,
      'only_cvm', false,
      'sync', false
    ),
    timeout_milliseconds := 30000
  )
  into req_id;

  return req_id;
end;
$$;

comment on function gymsite.invoke_cron_http(text) is
  'Dispara POST pg_net para job em cron_http_targets (weekly market batch).';

revoke all on function gymsite.invoke_cron_http(text) from public;
grant execute on function gymsite.invoke_cron_http(text) to service_role;

-- Compat view (opcional leitura ops via service_role)
create or replace view public.v_cron_http_targets as
select job_name, url, enabled, updated_at
from gymsite.cron_http_targets;

-- Domingo 06:00 UTC (~03:00 BRT) — mesmo slot do workflow GHA legado.
do $$
begin
  perform cron.unschedule('weekly_market_batch_invoke');
exception
  when others then null;
end $$;

select cron.schedule(
  'weekly_market_batch_invoke',
  '0 6 * * 0',
  $$select gymsite.invoke_cron_http('weekly_market_batch')$$
);
