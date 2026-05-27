/**
 * CapexBreakdownChart — composição do investimento inicial (obra, equipamentos, reserva)
 * nos 3 modelos financeiros (econômico, padrão, premium).
 */
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { cn } from '@/lib/utils'
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'

const chartConfig = {
  obra: {
    label: 'Obra e adaptação',
    theme: {
      light: 'oklch(0.52 0.17 250)',
      dark: 'oklch(0.68 0.15 250)',
    },
  },
  equipamentos: {
    label: 'Equipamentos',
    theme: {
      light: 'oklch(0.52 0.16 155)',
      dark: 'oklch(0.68 0.14 155)',
    },
  },
  contingencia: {
    label: 'Reserva de imprevistos (~10%)',
    theme: {
      light: 'oklch(0.62 0.14 75)',
      dark: 'oklch(0.76 0.12 75)',
    },
  },
} satisfies ChartConfig

const MODELO_LABEL: Record<'low' | 'mid' | 'premium', string> = {
  low: 'Econômico',
  mid: 'Padrão ★',
  premium: 'Premium',
}

function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatCompactBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(value)
}

function extrairBreakdown(cenario: CenarioJSON | undefined) {
  const d = cenario?.capex_detalhado
  if (!d) return null
  const obra =
    (d.obra_adaptacao ?? 0) +
    (d.projeto_arquitetonico ?? 0) +
    (d.alvara_e_taxas ?? 0) +
    (d.frete_equipamentos ?? 0)
  const equipamentos = d.equipamentos ?? 0
  const contingencia = d.contingencia_valor ?? 0
  const total = obra + equipamentos + contingencia
  if (total <= 0) return null
  return { obra, equipamentos, contingencia }
}

export interface CapexBreakdownChartProps {
  cenarios: Record<'low' | 'mid' | 'premium', CenarioJSON> | undefined
  className?: string
}

export function CapexBreakdownChart({ cenarios, className }: CapexBreakdownChartProps) {
  if (!cenarios) return null

  const data = (['low', 'mid', 'premium'] as const)
    .map((key) => {
      const breakdown = extrairBreakdown(cenarios[key])
      if (!breakdown) return null
      return {
        cenario: MODELO_LABEL[key],
        ...breakdown,
      }
    })
    .filter((row): row is NonNullable<typeof row> => row != null)

  if (data.length === 0) {
    return (
      <div className={cn('space-y-2', className)}>
        <div>
          <h4 className="text-sm font-medium">De onde vem o investimento (CAPEX)</h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            Estimativa do pipeline para os 3 modelos (econômico, padrão, premium)
          </p>
        </div>
        <div className="flex h-[220px] items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 px-4 text-center">
          <p className="text-sm text-muted-foreground">
            O detalhamento do investimento ainda não está disponível neste relatório.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div>
        <h4 className="text-sm font-medium">De onde vem o investimento (CAPEX)</h4>
        <p className="text-xs text-muted-foreground mt-0.5">
          Estimativa do pipeline para os 3 modelos (econômico, padrão, premium)
        </p>
      </div>
      <ChartContainer config={chartConfig} className="h-[220px] w-full">
        <BarChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis
            dataKey="cenario"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatCompactBRL(Number(v))}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value, name) => {
                  const key = String(name)
                  const label =
                    chartConfig[key as keyof typeof chartConfig]?.label ?? name
                  return (
                    <div className="flex w-full min-w-[12rem] items-center justify-between gap-4">
                      <span className="text-muted-foreground">{label}</span>
                      <span className="font-mono font-medium tabular-nums text-foreground">
                        {formatBRL(Number(value))}
                      </span>
                    </div>
                  )
                }}
              />
            }
          />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar
            dataKey="obra"
            stackId="capex"
            fill="var(--color-obra)"
            radius={[0, 0, 0, 0]}
          />
          <Bar
            dataKey="equipamentos"
            stackId="capex"
            fill="var(--color-equipamentos)"
          />
          <Bar
            dataKey="contingencia"
            stackId="capex"
            fill="var(--color-contingencia)"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ChartContainer>
    </div>
  )
}
