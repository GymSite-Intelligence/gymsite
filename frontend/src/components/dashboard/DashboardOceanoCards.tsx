/**
 * DashboardOceanoCards — KPIs de posicionamento (A9) em mini-cards Geo-Intel.
 * Cores via OCEANO_CHART_COLORS (consistente com OceanoDistributionChart).
 */
import { Link } from '@tanstack/react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { OCEANO_CHART_COLORS } from '@/lib/oceano'
import type { DashboardStats } from '@/hooks/useDashboardStats'

function KpiCard({
  title,
  value,
  description,
  accent,
  loading,
}: {
  title: string
  value: string
  description: string
  accent: string
  loading: boolean
}) {
  if (loading) return <Skeleton className="h-24 rounded-xl" />
  return (
    <div
      className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-xs"
      style={{ borderLeft: `3px solid ${accent}` }}
    >
      <div className="flex items-center gap-2">
        <span className="size-2.5 shrink-0 rounded-full" style={{ background: accent }} />
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
      </div>
      <span className="text-2xl font-semibold leading-none tabular-nums">{value}</span>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  )
}

export function DashboardOceanoCards({
  stats,
  loading,
}: {
  stats: DashboardStats | null | undefined
  loading: boolean
}) {
  const done = stats?.concluidos ?? 0
  const pct = (n: number) => (done > 0 ? `${Math.round((n / done) * 100)}%` : '—')

  return (
    <section className="space-y-3 px-4 lg:px-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Estratégia de mercado (A9)</h2>
          <p className="text-sm text-muted-foreground">
            Complementa o veredito de viabilidade do ponto
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/market-atlas">Market Atlas</Link>
        </Button>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Oceano azul"
          value={String(stats?.oceanoAzul ?? 0)}
          description={`${pct(stats?.oceanoAzul ?? 0)} dos concluídos`}
          accent={OCEANO_CHART_COLORS.OCEANO_AZUL}
          loading={loading}
        />
        <KpiCard
          title="Transição"
          value={String(stats?.oceanoTransicao ?? 0)}
          description={`${pct(stats?.oceanoTransicao ?? 0)} dos concluídos`}
          accent={OCEANO_CHART_COLORS.TRANSICAO}
          loading={loading}
        />
        <KpiCard
          title="Oceano vermelho"
          value={String(stats?.oceanoVermelho ?? 0)}
          description={`${pct(stats?.oceanoVermelho ?? 0)} dos concluídos`}
          accent={OCEANO_CHART_COLORS.VERMELHO}
          loading={loading}
        />
        <KpiCard
          title="Ticket médio A9"
          value={
            stats?.ticketMedioA9 != null ? `R$ ${Math.round(stats.ticketMedioA9)}` : '—'
          }
          description={
            stats?.semA9 ? `${stats.semA9} sem posicionamento` : 'Recomendação mensal'
          }
          accent="var(--chart-2)"
          loading={loading}
        />
      </div>
    </section>
  )
}
