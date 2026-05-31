-- ============================================================================
-- Hardening: prospecção + webhook log (RLS, GRANT, trigger search_path)
-- Projeto: epgedaiukjippepujuzc — aplicado em produção 2026-05-31
-- ============================================================================

-- 1) Trigger function — search_path fixo (anti hijacking)
create or replace function public.update_updated_at_column()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- 2) RLS
alter table public.oportunidades_prospeccao enable row level security;
alter table public.webhook_claw_log enable row level security;

-- 3) Policies — oportunidades_prospeccao
drop policy if exists oportunidades_select_org on public.oportunidades_prospeccao;
drop policy if exists oportunidades_insert_org on public.oportunidades_prospeccao;
drop policy if exists oportunidades_update_org on public.oportunidades_prospeccao;
drop policy if exists oportunidades_delete_org on public.oportunidades_prospeccao;
drop policy if exists oportunidades_service_role_all on public.oportunidades_prospeccao;

create policy oportunidades_select_org on public.oportunidades_prospeccao
  for select to authenticated
  using (org_id in (select public.user_org_ids()));

create policy oportunidades_insert_org on public.oportunidades_prospeccao
  for insert to authenticated
  with check (org_id in (select public.user_org_ids()));

create policy oportunidades_update_org on public.oportunidades_prospeccao
  for update to authenticated
  using (org_id in (select public.user_org_ids()))
  with check (org_id in (select public.user_org_ids()));

create policy oportunidades_delete_org on public.oportunidades_prospeccao
  for delete to authenticated
  using (org_id in (select public.user_org_ids()));

create policy oportunidades_service_role_all on public.oportunidades_prospeccao
  for all to service_role
  using (true)
  with check (true);

-- 4) Policies — webhook_claw_log
drop policy if exists webhook_log_select_org on public.webhook_claw_log;
drop policy if exists webhook_log_service_role_all on public.webhook_claw_log;

create policy webhook_log_select_org on public.webhook_claw_log
  for select to authenticated
  using (
    exists (
      select 1
      from public.oportunidades_prospeccao o
      where o.id = webhook_claw_log.oportunidade_id
        and o.org_id in (select public.user_org_ids())
    )
  );

create policy webhook_log_service_role_all on public.webhook_claw_log
  for all to service_role
  using (true)
  with check (true);

-- 5) Privilégios de tabela (camada abaixo do RLS)
revoke all on public.oportunidades_prospeccao from anon;
revoke all on public.webhook_claw_log from anon;

grant select, insert, update, delete on public.oportunidades_prospeccao to authenticated;
grant select on public.webhook_claw_log to authenticated;

grant all on public.oportunidades_prospeccao to service_role;
grant all on public.webhook_claw_log to service_role;
