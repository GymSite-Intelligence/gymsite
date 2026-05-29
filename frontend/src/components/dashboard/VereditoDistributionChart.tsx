/**
 * VereditoDistributionChart — donut chart de distribuição de vereditos.
 */
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { VereditoDistribution } from '@/hooks/useDashboardStats'

const COLORS: Record<string, string> = {
  APROVADO: 'hsl(142 70% 45%)',
  'APROVADO COM RESSALVAS': 'hsl(45 95% 55%)',
  'INVESTIGAR MAIS': 'hsl(210 80% 55%)',
  REPROVADO: 'hsl(0 70% 50%)',
  SEM_VEREDITO: 'hsl(220 10% 70%)',
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

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribuição de vereditos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">Nenhum dado disponível.</p>
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
        <CardTitle>Distribuição de vereditos</CardTitle>
        <CardDescription>Baseado em todos os relatórios visíveis</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={85}
              paddingAngle={3}
              dataKey="value"
              stroke="none"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: any, _name: any, props: any) => [
                `${value} (${props?.payload?.pct ?? 0}%)`,
                '',
              ]}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              iconSize={8}
              formatter={(value: string) => <span className="text-xs">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
