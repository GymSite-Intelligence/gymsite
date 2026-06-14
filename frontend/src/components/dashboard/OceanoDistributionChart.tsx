/**
 * OceanoDistributionChart — distribuição de posicionamento (A9) como barra
 * segmentada + breakdown (linguagem Geo-Intel). Cores de OCEANO_CHART_COLORS.
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { OCEANO_CHART_COLORS, OCEANO_CONFIG } from '@/lib/oceano'
import type { OceanoDistribution } from '@/hooks/useDashboardStats'

const LABELS: Record<string, string> = {
  OCEANO_AZUL: OCEANO_CONFIG.OCEANO_AZUL.label,
  TRANSICAO: OCEANO_CONFIG.TRANSICAO.label,
  VERMELHO: OCEANO_CONFIG.VERMELHO.label,
  SEM_A9: 'Sem A9',
}

export function OceanoDistributionChart({
  data,
  loading,
}: {
  data: OceanoDistribution[]
  loading: boolean
}) {
  if (loading) {
    return <Skeleton className="h-72 rounded-xl" />
  }

  const rows = data
    .map((d) => ({
      key: d.veredito,
      label: LABELS[d.veredito] ?? d.veredito,
      color: OCEANO_CHART_COLORS[d.veredito] ?? OCEANO_CHART_COLORS.SEM_A9,
      count: d.count,
      pct: d.pct,
    }))
    .sort((a, b) => b.count - a.count)

  return (
    <Card className="@container/card min-h-[280px]">
      <CardHeader>
        <CardTitle>Posicionamento (A9)</CardTitle>
        <CardDescription>Oceano azul, transição e vermelho</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Nenhum relatório com posicionamento ainda.
          </p>
        ) : (
          <>
            <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
              {rows.map((r) => (
                <div
                  key={r.key}
                  style={{ width: `${r.pct}%`, background: r.color }}
                  title={`${r.label}: ${r.count} (${r.pct}%)`}
                />
              ))}
            </div>
            <ul className="space-y-1.5">
              {rows.map((r) => (
                <li key={r.key} className="flex items-center gap-2 text-sm">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ background: r.color }}
                  />
                  <span className="min-w-0 flex-1 truncate">{r.label}</span>
                  <span className="font-mono tabular-nums">{r.count}</span>
                  <span className="w-10 text-right font-mono text-xs text-muted-foreground">
                    {r.pct}%
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  )
}
