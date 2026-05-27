import * as React from 'react'
import { Area, AreaChart, CartesianGrid, XAxis } from 'recharts'
import { useIsMobile } from '@/hooks/use-mobile'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ToggleGroup,
  ToggleGroupItem,
} from '@/components/ui/toggle-group'
import { Skeleton } from '@/components/ui/skeleton'
import type { DashboardChartPoint } from '@/hooks/useDashboardStats'

const chartConfig = {
  relatorios: {
    label: 'Relatórios',
    color: 'var(--chart-1)',
  },
  custo_brl: {
    label: 'Custo (R$)',
    color: 'var(--chart-2)',
  },
} satisfies ChartConfig

export function DashboardRelatoriosChart({
  data,
  loading,
}: {
  data: DashboardChartPoint[]
  loading: boolean
}) {
  const isMobile = useIsMobile()
  const [timeRange, setTimeRange] = React.useState('90d')

  React.useEffect(() => {
    if (isMobile) setTimeRange('30d')
  }, [isMobile])

  const filteredData = React.useMemo(() => {
    if (data.length === 0) return []
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    const ref = new Date(data[data.length - 1]!.date)
    const start = new Date(ref)
    start.setDate(start.getDate() - days)
    const startIso = start.toISOString().slice(0, 10)
    return data.filter((d) => d.date >= startIso)
  }, [data, timeRange])

  if (loading) {
    return <Skeleton className="mx-4 h-80 rounded-xl lg:mx-6" />
  }

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>Atividade</CardTitle>
        <CardDescription>
          Relatórios concluídos e custo Gemini por dia
        </CardDescription>
        <div className="flex items-center gap-2 @[767px]/card:ml-auto">
          <ToggleGroup
            type="single"
            value={timeRange}
            onValueChange={(v) => v && setTimeRange(v)}
            variant="outline"
            className="hidden *:data-[slot=toggle-group-item]:px-4! @[767px]/card:flex"
          >
            <ToggleGroupItem value="90d">90 dias</ToggleGroupItem>
            <ToggleGroupItem value="30d">30 dias</ToggleGroupItem>
            <ToggleGroupItem value="7d">7 dias</ToggleGroupItem>
          </ToggleGroup>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger
              className="w-32 **:data-[slot=select-value]:block **:data-[slot=select-value]:truncate @[767px]/card:hidden"
              size="sm"
            >
              <SelectValue placeholder="Período" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="90d">90 dias</SelectItem>
              <SelectItem value="30d">30 dias</SelectItem>
              <SelectItem value="7d">7 dias</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        {filteredData.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Nenhum relatório no período selecionado.
          </p>
        ) : (
          <ChartContainer config={chartConfig} className="aspect-auto h-[280px] w-full">
            <AreaChart data={filteredData}>
              <defs>
                <linearGradient id="fillRelatorios" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-relatorios)" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="var(--color-relatorios)" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={32}
                tickFormatter={(v) =>
                  new Date(v).toLocaleDateString('pt-BR', {
                    day: '2-digit',
                    month: 'short',
                  })
                }
              />
              <ChartTooltip
                cursor={false}
                content={
                  <ChartTooltipContent
                    labelFormatter={(v) =>
                      new Date(v).toLocaleDateString('pt-BR', {
                        day: '2-digit',
                        month: 'long',
                        year: 'numeric',
                      })
                    }
                    formatter={(value, name) => {
                      if (name === 'custo_brl') {
                        return [
                          Number(value).toLocaleString('pt-BR', {
                            style: 'currency',
                            currency: 'BRL',
                          }),
                          'Custo',
                        ]
                      }
                      return [value, 'Relatórios']
                    }}
                  />
                }
              />
              <Area
                dataKey="relatorios"
                type="natural"
                fill="url(#fillRelatorios)"
                stroke="var(--color-relatorios)"
                stackId="a"
              />
              <Area
                dataKey="custo_brl"
                type="natural"
                fill="var(--color-custo_brl)"
                fillOpacity={0.15}
                stroke="var(--color-custo_brl)"
                stackId="b"
              />
            </AreaChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
