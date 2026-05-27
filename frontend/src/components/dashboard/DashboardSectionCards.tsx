import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { DashboardStats } from '@/hooks/useDashboardStats'

function brl(v: number): string {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export function DashboardSectionCards({
  stats,
  loading,
}: {
  stats: DashboardStats | null
  loading: boolean
}) {
  if (loading) {
    return (
      <div
        className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4"
      >
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-36 rounded-xl" />
        ))}
      </div>
    )
  }

  const taxaAprovacao =
    stats && stats.concluidos > 0
      ? Math.round((stats.aprovados / stats.concluidos) * 100)
      : 0

  const cards = [
    {
      label: 'Relatórios',
      value: String(stats?.total ?? 0),
      hint: `${stats?.concluidos ?? 0} concluídos · ${stats?.emAndamento ?? 0} em fila`,
    },
    {
      label: 'Aprovados',
      value: String(stats?.aprovados ?? 0),
      hint: `${taxaAprovacao}% dos concluídos`,
      badge: taxaAprovacao >= 50 ? 'success' : 'warning',
    },
    {
      label: 'Custo Gemini',
      value: brl(stats?.custoTotalBrl ?? 0),
      hint: 'Soma custo_brl dos relatórios',
    },
    {
      label: 'Score médio',
      value:
        stats?.scoreMedio != null ? stats.scoreMedio.toFixed(1) : '—',
      hint: 'Top candidato · relatórios concluídos',
    },
  ] as const

  return (
    <div className="grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 dark:*:data-[slot=card]:bg-card">
      {cards.map((c) => (
        <Card key={c.label} className="@container/card">
          <CardHeader>
            <CardDescription>{c.label}</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
              {c.value}
            </CardTitle>
            {'badge' in c && c.badge && (
              <Badge variant={c.badge} className="w-fit">
                {taxaAprovacao}% aprovação
              </Badge>
            )}
          </CardHeader>
          <CardFooter className="text-sm text-muted-foreground">{c.hint}</CardFooter>
        </Card>
      ))}
    </div>
  )
}
