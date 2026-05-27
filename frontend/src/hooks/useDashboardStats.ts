/**
 * useDashboardStats — KPIs e série temporal derivados de v_relatorios_resumo.
 */
import { useMemo } from 'react'
import { useRelatorios } from '@/hooks/useRelatorios'
import type { RelatorioResumo, Veredito } from '@/types/domain'

export interface DashboardChartPoint {
  date: string
  relatorios: number
  custo_brl: number
}

export interface DashboardStats {
  total: number
  concluidos: number
  emAndamento: number
  aprovados: number
  custoTotalBrl: number
  scoreMedio: number | null
  chartData: DashboardChartPoint[]
}

const APROVADOS: Veredito[] = ['APROVADO', 'APROVADO COM RESSALVAS']

function bucketByDay(rows: RelatorioResumo[]): DashboardChartPoint[] {
  const map = new Map<string, { relatorios: number; custo_brl: number }>()
  for (const r of rows) {
    const day = (r.data_execucao ?? r.created_at).slice(0, 10)
    const prev = map.get(day) ?? { relatorios: 0, custo_brl: 0 }
    map.set(day, {
      relatorios: prev.relatorios + 1,
      custo_brl: prev.custo_brl + (r.custo_brl ?? 0),
    })
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, v]) => ({ date, ...v }))
}

export function useDashboardStats() {
  const query = useRelatorios()

  const stats = useMemo((): DashboardStats | null => {
    const rows = query.data
    if (!rows) return null

    const concluidos = rows.filter((r) => r.status === 'done')
    const emAndamento = rows.filter(
      (r) => r.status === 'queued' || r.status === 'running',
    )
    const aprovados = concluidos.filter(
      (r) => r.veredito && APROVADOS.includes(r.veredito),
    )
    const scores = concluidos
      .map((r) => r.score_top1_candidato)
      .filter((s): s is number => s != null)
    const custoTotalBrl = rows.reduce((acc, r) => acc + (r.custo_brl ?? 0), 0)
    const scoreMedio =
      scores.length > 0
        ? scores.reduce((a, b) => a + b, 0) / scores.length
        : null

    const chartSource = concluidos.length ? concluidos : rows

    return {
      total: rows.length,
      concluidos: concluidos.length,
      emAndamento: emAndamento.length,
      aprovados: aprovados.length,
      custoTotalBrl,
      scoreMedio,
      chartData: bucketByDay(chartSource),
    }
  }, [query.data])

  return { ...query, stats }
}
