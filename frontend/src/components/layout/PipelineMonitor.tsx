/**
 * PipelineMonitor — polling global de relatórios queued/running.
 * Montado no AppShell: continua mesmo se o user sair da tela /aguardando.
 */
import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { notify } from '@/lib/notify'
import {
  getTrackedPipelines,
  subscribePipelineWatch,
  untrackPipeline,
  type TrackedPipeline,
} from '@/lib/pipeline-tracker'
import { pipelineEtaBackgroundLine } from '@/lib/pipeline-eta'

type PipelineStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled'

interface StatusRow {
  id: string
  status: PipelineStatus
  erro_mensagem: string | null
}

export function PipelineMonitor() {
  const queryClient = useQueryClient()
  const [tracked, setTracked] = useState<TrackedPipeline[]>(() => getTrackedPipelines())

  useEffect(() => subscribePipelineWatch(() => setTracked(getTrackedPipelines())), [])

  const ids = tracked.map((t) => t.id)

  const statusQuery = useQuery({
    queryKey: ['pipeline-monitor', ids],
    enabled: ids.length > 0,
    meta: { silent: true },
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
    queryFn: async (): Promise<StatusRow[]> => {
      const { data, error } = await supabase
        .from('relatorios')
        .select('id, status, erro_mensagem')
        .in('id', ids)
        .is('deleted_at', null)
      if (error) throw new Error(error.message)
      return (data ?? []) as StatusRow[]
    },
  })

  useEffect(() => {
    const rows = statusQuery.data
    if (!rows?.length) return

    let changed = false
    for (const row of rows) {
      if (row.status === 'done') {
        untrackPipeline(row.id)
        changed = true
        notify.success('Relatório pronto', {
          description: 'Pipeline concluído. Abra em Relatórios.',
          duration: 8000,
        })
      } else if (row.status === 'failed' || row.status === 'cancelled') {
        untrackPipeline(row.id)
        changed = true
        notify.error('Pipeline falhou', {
          description: row.erro_mensagem?.slice(0, 120) ?? 'Ver detalhes em Relatórios.',
          duration: 10000,
        })
      }
    }

    if (changed) {
      queryClient.invalidateQueries({ queryKey: ['relatorios'] })
      setTracked(getTrackedPipelines())
    }
  }, [statusQuery.data, queryClient])

  const active = tracked.filter((t) => {
    const row = statusQuery.data?.find((r) => r.id === t.id)
    return !row || row.status === 'queued' || row.status === 'running'
  })

  if (active.length === 0) return null

  const first = active[0]!

  return (
    <div className="border-b border-primary/30 bg-primary/5">
      <div className="container flex flex-wrap items-center gap-3 py-2 text-sm">
        <Loader2 size={14} className="animate-spin text-primary shrink-0" />
        <span>
          {active.length === 1
            ? pipelineEtaBackgroundLine()
            : `${active.length} relatórios gerando em background`}
          {first.label ? ` · ${first.label}` : ''}
        </span>
        <Link
          to="/relatorios/$relatorioId/aguardando"
          params={{ relatorioId: first.id }}
          className="text-primary underline-offset-2 hover:underline font-medium"
        >
          Ver progresso
        </Link>
        <Link
          to="/relatorios"
          className="text-muted-foreground underline-offset-2 hover:underline text-xs"
        >
          Ir para lista
        </Link>
      </div>
    </div>
  )
}
