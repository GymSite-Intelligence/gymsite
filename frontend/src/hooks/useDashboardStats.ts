/**
 * useDashboardStats — KPIs, série temporal, distribuição e insights
 * derivados de v_relatorios_resumo.
 */
import { useMemo } from 'react'
import { useRelatorios } from '@/hooks/useRelatorios'
import type { RelatorioResumo, Veredito, RelatorioStatus } from '@/types/domain'

export interface DashboardChartPoint {
  date: string
  relatorios: number
  custo_brl: number
}

export interface VereditoDistribution {
  veredito: Veredito | 'SEM_VEREDITO'
  count: number
  pct: number
}

export interface BairroRankItem {
  bairro: string
  cidade: string
  uf: string | null
  count: number
  scoreMedio: number | null
  aprovacaoPct: number
}

export interface DashboardInsight {
  tipo: 'warning' | 'success' | 'info' | 'danger'
  titulo: string
  descricao: string
}

export interface DashboardStats {
  total: number
  concluidos: number
  emAndamento: number
  aprovados: number
  reprovados: number
  investigar: number
  custoTotalBrl: number
  scoreMedio: number | null
  chartData: DashboardChartPoint[]
  vereditoDistribution: VereditoDistribution[]
  bairrosRanking: BairroRankItem[]
  insights: DashboardInsight[]
  scoreHistory: { date: string; scoreMedio: number | null; count: number }[]
}

export interface DashboardFilters {
  cidade?: string
  veredito?: Veredito
  status?: RelatorioStatus
  since?: string // ISO date
}

const APROVADOS: Veredito[] = ['APROVADO', 'APROVADO COM RESSALVAS']
const REPROVADOS: Veredito[] = ['REPROVADO']

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

function computeVereditoDistribution(
  rows: RelatorioResumo[],
): VereditoDistribution[] {
  const map = new Map<Veredito | 'SEM_VEREDITO', number>()
  for (const r of rows) {
    const key: Veredito | 'SEM_VEREDITO' = r.veredito ?? 'SEM_VEREDITO'
    map.set(key, (map.get(key) ?? 0) + 1)
  }
  const total = rows.length || 1
  return ([...map.entries()]
    .map(([veredito, count]) => ({ veredito, count, pct: Math.round((count / total) * 100) }))
    .sort((a, b) => b.count - a.count) as VereditoDistribution[])
}

function computeBairrosRanking(rows: RelatorioResumo[]): BairroRankItem[] {
  const map = new Map<string, RelatorioResumo[]>()
  for (const r of rows) {
    const key = `${r.bairro}|${r.cidade}|${r.uf ?? ''}`
    const arr = map.get(key) ?? []
    arr.push(r)
    map.set(key, arr)
  }

  const result: BairroRankItem[] = []
  for (const [key, arr] of map.entries()) {
    const [bairro, cidade, uf] = key.split('|')
    const concluidos = arr.filter((r) => r.status === 'done')
    const scores = concluidos
      .map((r) => r.score_top1_candidato)
      .filter((s): s is number => s != null)
    const aprovados = concluidos.filter(
      (r) => r.veredito && APROVADOS.includes(r.veredito),
    )
    result.push({
      bairro,
      cidade,
      uf: uf || null,
      count: arr.length,
      scoreMedio:
        scores.length > 0
          ? scores.reduce((a, b) => a + b, 0) / scores.length
          : null,
      aprovacaoPct:
        concluidos.length > 0
          ? Math.round((aprovados.length / concluidos.length) * 100)
          : 0,
    })
  }

  return result.sort((a, b) => (b.scoreMedio ?? 0) - (a.scoreMedio ?? 0)).slice(0, 10)
}

function computeInsights(
  rows: RelatorioResumo[],
  stats: Omit<DashboardStats, 'insights'>,
): DashboardInsight[] {
  const insights: DashboardInsight[] = []

  // 1. Relatórios em fila há muito tempo
  const emAndamento = rows.filter(
    (r) => r.status === 'queued' || r.status === 'running',
  )
  if (emAndamento.length >= 3) {
    insights.push({
      tipo: 'warning',
      titulo: `${emAndamento.length} relatórios em andamento`,
      descricao: 'Verifique se o pipeline não está congestionado.',
    })
  }

  // 2. Taxa de aprovação
  if (stats.concluidos > 0) {
    const taxa = Math.round((stats.aprovados / stats.concluidos) * 100)
    if (taxa >= 70) {
      insights.push({
        tipo: 'success',
        titulo: `${taxa}% de aprovação`,
        descricao: 'Boa taxa de viabilidade nas análises recentes.',
      })
    } else if (taxa <= 30) {
      insights.push({
        tipo: 'danger',
        titulo: `${taxa}% de aprovação`,
        descricao: 'Muitos pontos reprovados. Reveja critérios de entrada.',
      })
    }
  }

  // 3. Score médio em queda (se houver dados de pelo menos 2 semanas)
  const scoreHistory = stats.scoreHistory
  if (scoreHistory.length >= 2) {
    const primeiro = scoreHistory.find((s) => s.scoreMedio != null)
    const ultimo = [...scoreHistory].reverse().find((s) => s.scoreMedio != null)
    if (primeiro && ultimo && primeiro !== ultimo && ultimo.scoreMedio != null && primeiro.scoreMedio != null) {
      const diff = ultimo.scoreMedio - primeiro.scoreMedio
      if (diff <= -1.5) {
        insights.push({
          tipo: 'warning',
          titulo: 'Score médio em queda',
          descricao: `Caiu ${Math.abs(diff).toFixed(1)} pts desde ${new Date(primeiro.date).toLocaleDateString('pt-BR')}.`,
        })
      }
    }
  }

  // 4. Custo acumulado alto
  if (stats.custoTotalBrl > 500) {
    insights.push({
      tipo: 'info',
      titulo: `R$ ${stats.custoTotalBrl.toFixed(0)} em tokens Gemini`,
      descricao: 'Acompanhe o consumo mensal no dashboard de custos.',
    })
  }

  // 5. Bairro com mais análises
  if (stats.bairrosRanking.length > 0) {
    const top = stats.bairrosRanking[0]
    if (top.count >= 3) {
      insights.push({
        tipo: 'info',
        titulo: `${top.bairro} é o bairro mais analisado`,
        descricao: `${top.count} relatórios · score médio ${top.scoreMedio?.toFixed(1) ?? '—'}`,
      })
    }
  }

  return insights.slice(0, 4)
}

function computeScoreHistory(
  rows: RelatorioResumo[],
): { date: string; scoreMedio: number | null; count: number }[] {
  const map = new Map<string, number[]>()
  for (const r of rows) {
    if (r.status !== 'done' || r.score_top1_candidato == null) continue
    const day = (r.data_execucao ?? r.created_at).slice(0, 10)
    const arr = map.get(day) ?? []
    arr.push(r.score_top1_candidato)
    map.set(day, arr)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, scores]) => ({
      date,
      scoreMedio: scores.reduce((a, b) => a + b, 0) / scores.length,
      count: scores.length,
    }))
}

export function useDashboardStats(filters: DashboardFilters = {}) {
  const query = useRelatorios(filters)

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
    const reprovados = concluidos.filter(
      (r) => r.veredito && REPROVADOS.includes(r.veredito),
    )
    const investigar = concluidos.filter(
      (r) => r.veredito === 'INVESTIGAR MAIS',
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
    const vereditoDistribution = computeVereditoDistribution(rows)
    const bairrosRanking = computeBairrosRanking(rows)
    const scoreHistory = computeScoreHistory(rows)

    const baseStats = {
      total: rows.length,
      concluidos: concluidos.length,
      emAndamento: emAndamento.length,
      aprovados: aprovados.length,
      reprovados: reprovados.length,
      investigar: investigar.length,
      custoTotalBrl,
      scoreMedio,
      chartData: bucketByDay(chartSource),
      vereditoDistribution,
      bairrosRanking,
      scoreHistory,
    }

    return {
      ...baseStats,
      insights: computeInsights(rows, baseStats),
    }
  }, [query.data])

  return { ...query, stats }
}
