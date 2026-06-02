import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { OCEANO_CONFIG } from '@/lib/oceano'
import type { OceanoDistribution } from '@/hooks/useDashboardStats'

const COLORS: Record<string, string> = {
  OCEANO_AZUL: 'hsl(142 70% 45%)',
  TRANSICAO: 'hsl(45 95% 55%)',
  VERMELHO: 'hsl(0 70% 50%)',
  SEM_A9: 'hsl(220 10% 70%)',
}

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

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Posicionamento (A9)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhum relatório com posicionamento ainda.
          </p>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map((d) => ({
    name: LABELS[d.veredito] ?? d.veredito,
    value: d.count,
    pct: d.pct,
    color: COLORS[d.veredito] ?? 'hsl(220 10% 70%)',
  }))

  return (
    <Card className="@container/card min-h-[280px]">
      <CardHeader>
        <CardTitle>Posicionamento (A9)</CardTitle>
        <CardDescription>Oceano azul, transição e vermelho</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={2}
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: unknown, _name: unknown, props: { payload?: { pct?: number } }) => [
                `${value} (${props?.payload?.pct ?? 0}%)`,
                '',
              ]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
