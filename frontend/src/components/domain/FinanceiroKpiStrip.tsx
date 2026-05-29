/**
 * FinanceiroKpiStrip — 4 KPIs acima da seção de viabilidade (GYM-23).
 */
import { cn } from '@/lib/utils'
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'
import { formatBRL, formatPayback } from '@/lib/format'

export interface FinanceiroKpiStripProps {
  areaM2Min?: number
  areaM2Max?: number
  aluguelMensal?: number | null
  cenarioMid?: CenarioJSON
  className?: string
}

export function FinanceiroKpiStrip({
  areaM2Min,
  areaM2Max,
  aluguelMensal,
  cenarioMid,
  className,
}: FinanceiroKpiStripProps) {
  const areaLabel = (() => {
    const hasMin = areaM2Min != null && !Number.isNaN(areaM2Min);
    const hasMax = areaM2Max != null && !Number.isNaN(areaM2Max);
    if (hasMin && hasMax) {
      return `${areaM2Min.toLocaleString('pt-BR')}–${areaM2Max.toLocaleString('pt-BR')} m²`
    }
    if (hasMin) {
      return `≥ ${areaM2Min.toLocaleString('pt-BR')} m²`
    }
    if (hasMax) {
      return `≤ ${areaM2Max.toLocaleString('pt-BR')} m²`
    }
    return '—'
  })()

  const aluguel =
    cenarioMid?.custos_detalhados?.aluguel ??
    aluguelMensal ??
    null

  const capexMid =
    cenarioMid?.capex_total ?? cenarioMid?.capex_detalhado?.total ?? null

  const payback = cenarioMid?.payback_meses ?? null
  const viabilidade = cenarioMid?.viabilidade

  return (
    <div
      className={cn(
        'grid grid-cols-2 lg:grid-cols-4 gap-3',
        className,
      )}
    >
      <KpiCard label="Área alvo" value={areaLabel} />
      <KpiCard label="Aluguel total (mid)" value={formatBRL(aluguel)} accent="emerald" />
      <KpiCard label="CAPEX mid" value={formatBRL(capexMid)} />
      <KpiCard
        label="Payback (mid)"
        value={formatPayback(payback)}
        sub={viabilidade ? `Viabilidade ${viabilidade}` : undefined}
        accent="amber"
      />
    </div>
  )
}

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string
  sub?: string
  accent?: 'emerald' | 'amber'
}) {
  const valueColor =
    accent === 'emerald'
      ? 'text-veredito-aprovado'
      : accent === 'amber'
        ? 'text-veredito-ressalvas'
        : 'text-foreground'

  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
        {label}
      </p>
      <p className={cn('mt-1 text-lg font-semibold tabular-nums', valueColor)}>
        {value}
      </p>
      {sub && (
        <p className="text-[10px] text-muted-foreground mt-0.5">{sub}</p>
      )}
    </div>
  )
}
