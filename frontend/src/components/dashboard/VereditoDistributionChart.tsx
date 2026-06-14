/**
 * VereditoDistributionChart — distribuição de vereditos como barra segmentada
 * horizontal + breakdown (linguagem Geo-Intel, consistente com o report).
 * Cores via tokens runtime hsl(var(--veredito-*)) — mesmos do PosicionamentoCard.
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { VereditoDistribution } from '@/hooks/useDashboardStats'

const COLORS: Record<string, string> = {
  APROVADO: 'hsl(var(--veredito-aprovado))',
  'APROVADO COM RESSALVAS': 'hsl(var(--veredito-ressalvas))',
  'INVESTIGAR MAIS': 'hsl(var(--status-investigate))',
  REPROVADO: 'hsl(var(--veredito-reprovado))',
  SEM_VEREDITO: 'var(--muted-foreground)',
}

const LABELS: Record<string, string> = {
  APROVADO: 'Aprovado',
  'APROVADO COM RESSALVAS': 'Ressalvas',
  'INVESTIGAR MAIS': 'Investigar',
  REPROVADO: 'Reprovado',
  SEM_VEREDITO: 'Sem veredito',
}

export function VereditoDistributionChart({
  data,
  loading,
}: {
  data: VereditoDistribution[]
  loading: boolean
}) {
  if (loading) {
    return <Skeleton className="h-72 rounded-xl" />
  }

  const rows = data
    .map((d) => ({
      key: d.veredito,
      label: LABELS[d.veredito] ?? d.veredito,
      color: COLORS[d.veredito] ?? 'var(--muted-foreground)',
      count: d.count,
      pct: d.pct,
    }))
    .sort((a, b) => b.count - a.count)

  return (
    <Card className="@container/card min-h-[280px]">
      <CardHeader>
        <CardTitle>Distribuição de vereditos</CardTitle>
        <CardDescription>Baseado em todos os relatórios visíveis</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Nenhum dado disponível.</p>
        ) : (
          <>
            {/* Barra segmentada — proporção de cada veredito */}
            <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
              {rows.map((r) => (
                <div
                  key={r.key}
                  style={{ width: `${r.pct}%`, background: r.color }}
                  title={`${r.label}: ${r.count} (${r.pct}%)`}
                />
              ))}
            </div>
            {/* Breakdown */}
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
