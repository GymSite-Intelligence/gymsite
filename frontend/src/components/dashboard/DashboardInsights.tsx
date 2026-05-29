/**
 * DashboardInsights — cards de alertas e insights automáticos.
 */
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { DashboardInsight } from '@/hooks/useDashboardStats'

const ICONS = {
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
  danger: XCircle,
}

const COLORS = {
  warning: 'text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-900',
  success: 'text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-900',
  info: 'text-sky-600 bg-sky-50 border-sky-200 dark:bg-sky-950/30 dark:border-sky-900',
  danger: 'text-red-600 bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-900',
}

export function DashboardInsights({
  insights,
  loading,
}: {
  insights: DashboardInsight[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    )
  }

  if (insights.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Nenhum insight no momento. Gere mais relatórios para obter análises automáticas.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {insights.map((insight, i) => {
        const Icon = ICONS[insight.tipo]
        return (
          <Card
            key={i}
            className={cn(
              'border flex items-start gap-3 p-4',
              COLORS[insight.tipo],
            )}
          >
            <Icon size={18} className="shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-sm font-semibold">{insight.titulo}</p>
              <p className="text-xs mt-0.5 opacity-90">{insight.descricao}</p>
            </div>
          </Card>
        )
      })}
    </div>
  )
}
