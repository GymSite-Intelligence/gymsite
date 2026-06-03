-- Layer 3: marca relatórios running/queued órfãos (sem relatorio_outputs) como failed.
-- Comparação em timestamptz no servidor evita drift de timezone no cliente.

create or replace function public.recover_stale_running_reports(
  p_orphan_minutes int default 35,
  p_relatorio_id uuid default null
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  n integer := 0;
  r record;
  stale_msg text := 'Pipeline interrompido (restart do servidor ou timeout). Use «Gerar novamente» para reprocessar.';
begin
  if p_orphan_minutes is null or p_orphan_minutes < 1 then
    p_orphan_minutes := 35;
  end if;

  for r in
    select rel.id, rel.status
    from public.relatorios rel
    where rel.status in ('running', 'queued')
      and rel.updated_at < (now() at time zone 'utc') - make_interval(mins => p_orphan_minutes)
      and (p_relatorio_id is null or rel.id = p_relatorio_id)
      and not exists (
        select 1
        from public.relatorio_outputs o
        where o.relatorio_id = rel.id
      )
  loop
    update public.relatorios
    set status = 'failed',
        erro_mensagem = stale_msg
    where id = r.id;

    n := n + 1;
  end loop;

  return n;
end;
$$;

comment on function public.recover_stale_running_reports(int, uuid) is
  'Marca como failed relatórios running/queued sem output e updated_at antigo (órfãos).';

grant execute on function public.recover_stale_running_reports(int, uuid) to service_role;
