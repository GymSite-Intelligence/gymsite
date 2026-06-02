import { Link } from '@tanstack/react-router'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import type { DashboardStats } from '@/hooks/useDashboardStats'

function KpiCard({
  title,
  value,
  description,
  loading,
}: {
  title: string
  value: string
  description: string
  loading: boolean
}) {
  if (loading) return <Skeleton className="h-24 rounded-xl" />
  return (
    <Card className="@container/card">
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums">{value}</CardTitle>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardHeader>
    </Card>
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
          loading={loading}
        />
        <KpiCard
          title="Transição"
          value={String(stats?.oceanoTransicao ?? 0)}
          description={`${pct(stats?.oceanoTransicao ?? 0)} dos concluídos`}
          loading={loading}
        />
        <KpiCard
          title="Oceano vermelho"
          value={String(stats?.oceanoVermelho ?? 0)}
          description={`${pct(stats?.oceanoVermelho ?? 0)} dos concluídos`}
          loading={loading}
        />
        <KpiCard
          title="Ticket médio A9"
          value={
            stats?.ticketMedioA9 != null
              ? `R$ ${Math.round(stats.ticketMedioA9)}`
              : '—'
          }
          description={
            stats?.semA9
              ? `${stats.semA9} sem posicionamento`
              : 'Recomendação mensal'
          }
          loading={loading}
        />
      </div>
    </section>
  )
}
