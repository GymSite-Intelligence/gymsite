/**
 * DashboardSectionCards — KPIs do dashboard em mini-cards (linguagem Geo-Intel).
 *
 * Cards user-facing: Relatórios, Aprovados (taxa), Reprovados, Score médio.
 * O card de CUSTO (custoTotalBrl) é economia operacional INTERNA (base de margem
 * — ver docs/produto/MODELO_NEGOCIO.md) e só aparece para admin via useIsAdmin().
 *
 * NOTA: useIsAdmin() apenas ESCONDE a UI. O campo custo_brl ainda viaja no payload
 * dos relatórios — o gate de verdade (backend não enviar custo a não-admin) é
 * item separado de release.
 */
import { CheckCircle2, FileText, Gauge, Lock, XCircle } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useIsAdmin } from '@/hooks/useIsAdmin'
import type { DashboardStats } from '@/hooks/useDashboardStats'

function brl(v: number): string {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

interface KpiCard {
  label: string
  value: string
  hint: string
  accent: string
  Icon: typeof FileText
  badge?: { text: string; tone: 'success' | 'warning' }
  internal?: boolean
}

export function DashboardSectionCards({
  stats,
  loading,
}: {
  stats: DashboardStats | null
  loading: boolean
}) {
  const isAdmin = useIsAdmin()

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 sm:grid-cols-2 @5xl/main:grid-cols-4">
        {Array.from({ length: isAdmin ? 5 : 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    )
  }

  const taxaAprovacao =
    stats && stats.concluidos > 0
      ? Math.round((stats.aprovados / stats.concluidos) * 100)
      : 0
  const taxaReprovacao =
    stats && stats.concluidos > 0
      ? Math.round((stats.reprovados / stats.concluidos) * 100)
      : 0

  const cards: KpiCard[] = [
    {
      label: 'Relatórios',
      value: String(stats?.total ?? 0),
      hint: `${stats?.concluidos ?? 0} concluídos · ${stats?.emAndamento ?? 0} em fila`,
      accent: 'var(--chart-1)',
      Icon: FileText,
    },
    {
      label: 'Aprovados',
      value: String(stats?.aprovados ?? 0),
      hint: `${taxaAprovacao}% dos concluídos`,
      accent: 'hsl(var(--veredito-aprovado))',
      Icon: CheckCircle2,
      badge:
        stats && stats.concluidos > 0
          ? { text: `${taxaAprovacao}% aprovação`, tone: taxaAprovacao >= 50 ? 'success' : 'warning' }
          : undefined,
    },
    {
      label: 'Reprovados',
      value: String(stats?.reprovados ?? 0),
      hint: `${taxaReprovacao}% dos concluídos`,
      accent: 'hsl(var(--veredito-reprovado))',
      Icon: XCircle,
    },
    {
      label: 'Score médio',
      value: stats?.scoreMedio != null ? stats.scoreMedio.toFixed(1) : '—',
      hint: 'Top candidato · concluídos',
      accent: 'var(--chart-2)',
      Icon: Gauge,
    },
  ]

  // Custo: economia operacional interna — só admin.
  if (isAdmin) {
    cards.push({
      label: 'Custo Gemini',
      value: brl(stats?.custoTotalBrl ?? 0),
      hint: 'Soma custo_brl dos relatórios',
      accent: 'hsl(var(--veredito-ressalvas))',
      Icon: Lock,
      internal: true,
    })
  }

  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 sm:grid-cols-2 @5xl/main:grid-cols-4">
      {cards.map((c) => (
        <div
          key={c.label}
          data-slot="card"
          className="relative flex flex-col gap-2 overflow-hidden rounded-xl border border-border bg-card p-4 shadow-xs"
          style={{ borderLeft: `3px solid ${c.accent}` }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {c.label}
            </span>
            <c.Icon size={15} className="shrink-0" style={{ color: c.accent }} />
          </div>
          <span className="text-3xl font-semibold leading-none tabular-nums">{c.value}</span>
          <div className="flex flex-wrap items-center gap-2">
            {c.badge && (
              <span
                className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                style={{
                  color:
                    c.badge.tone === 'success'
                      ? 'hsl(var(--veredito-aprovado))'
                      : 'hsl(var(--veredito-ressalvas))',
                  background: `color-mix(in oklch, ${
                    c.badge.tone === 'success'
                      ? 'hsl(var(--veredito-aprovado))'
                      : 'hsl(var(--veredito-ressalvas))'
                  } 14%, transparent)`,
                }}
              >
                {c.badge.text}
              </span>
            )}
            {c.internal && (
              <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                <Lock size={9} /> interno
              </span>
            )}
            <span className="text-xs text-muted-foreground">{c.hint}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
