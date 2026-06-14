/**
 * CenariosViz — camada visual radical dos 3 cenários financeiros (low/mid/premium).
 *
 * Fica ACIMA da CenarioFinanceiroTable (que vira drill-down). Não recalcula nada:
 * consome o mesmo `CenarioJSON` já computado pelo pipeline. Progressive disclosure —
 * leitura visual primeiro (cards + barras + cenário recomendado em destaque),
 * tabela auditável detalhada logo abaixo.
 */
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type ModeloKey = 'low' | 'mid' | 'premium'

const MODELOS: ModeloKey[] = ['low', 'mid', 'premium']
const LABELS: Record<ModeloKey, string> = {
  low: 'Low Cost',
  mid: 'Mid Market',
  premium: 'Premium',
}

const brl = (n: number | null | undefined) =>
  typeof n === 'number'
    ? new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        maximumFractionDigits: 0,
      }).format(n)
    : '—'

const num = (n: number | null | undefined, suffix = '') =>
  typeof n === 'number' ? `${Math.round(n)}${suffix}` : '—'

function isRecomendado(c: CenarioJSON | undefined, m: ModeloKey, rec?: string): boolean {
  if (!c) return false
  if (c.modelo_key === m && rec) {
    const r = rec.toLowerCase()
    return (
      (m === 'low' && r.includes('low')) ||
      (m === 'mid' && (r.includes('mid') || r.includes('méd'))) ||
      (m === 'premium' && r.includes('premium'))
    )
  }
  const n = (rec ?? '').toLowerCase()
  return (
    (m === 'low' && n.includes('low')) ||
    (m === 'mid' && (n.includes('mid') || n.includes('méd'))) ||
    (m === 'premium' && n.includes('premium'))
  )
}

export interface CenariosVizProps {
  cenarios: Record<ModeloKey, CenarioJSON> | undefined
  modeloRecomendado?: string
  className?: string
}

export function CenariosViz({ cenarios, modeloRecomendado, className }: CenariosVizProps) {
  if (!cenarios) return null

  const lucros = MODELOS.map((m) => cenarios[m]?.lucro_mensal_estimado ?? 0)
  const maxLucro = Math.max(...lucros.map((v) => Math.abs(v)), 1)
  const paybacks = MODELOS.map((m) => cenarios[m]?.payback_meses ?? 0)
  const maxPayback = Math.max(...paybacks, 1)

  return (
    <div className={cn('grid grid-cols-1 gap-4 md:grid-cols-3', className)}>
      {MODELOS.map((m, i) => {
        const c = cenarios[m]
        const rec = isRecomendado(c, m, modeloRecomendado)
        const lucro = c?.lucro_mensal_estimado ?? null
        const margem = c?.margem_percentual ?? null
        const payback = c?.payback_meses ?? null
        const capex = c?.capex_total ?? c?.capex_estimado ?? c?.investimento_total ?? null
        const tir = c?.tir_anual_pct ?? null
        const breakEven = c?.alunos_break_even ?? null
        const chart = `var(--chart-${i + 2})` // mid-ramp por cenário

        return (
          <div
            key={m}
            className={cn(
              'relative flex flex-col gap-4 rounded-xl border bg-card p-5 transition-shadow',
              rec
                ? 'border-primary/60 shadow-lg ring-1 ring-primary/30'
                : 'border-border',
            )}
          >
            {rec && (
              <Badge className="absolute -top-2.5 left-4">★ Recomendado</Badge>
            )}

            <div>
              <p className="text-sm font-semibold tracking-tight">{LABELS[m]}</p>
              {c?.descricao && (
                <p className="line-clamp-1 text-xs text-muted-foreground">{c.descricao}</p>
              )}
            </div>

            {/* Lucro mensal — métrica-herói + barra relativa entre cenários */}
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Lucro mensal
              </p>
              <p
                className={cn(
                  'font-mono text-2xl font-bold',
                  (lucro ?? 0) < 0 ? 'text-destructive' : 'text-foreground',
                )}
              >
                {brl(lucro)}
              </p>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(100, (Math.abs(lucro ?? 0) / maxLucro) * 100)}%`,
                    background: (lucro ?? 0) < 0 ? 'var(--destructive)' : chart,
                  }}
                />
              </div>
            </div>

            {/* Margem — gauge linear */}
            <Metric label="Margem">
              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(0, margem ?? 0))}%`,
                      background: chart,
                    }}
                  />
                </div>
                <span className="w-10 text-right font-mono text-sm">{num(margem, '%')}</span>
              </div>
            </Metric>

            {/* Payback — barra (menor = melhor) */}
            <Metric label="Payback">
              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${Math.min(100, ((payback ?? 0) / maxPayback) * 100)}%` }}
                  />
                </div>
                <span className="w-14 text-right font-mono text-sm">{num(payback, ' m')}</span>
              </div>
            </Metric>

            {/* Mini-grid de indicadores secundários */}
            <div className="mt-auto grid grid-cols-2 gap-x-3 gap-y-2 border-t border-border pt-3 text-sm">
              <Kpi label="CAPEX" value={brl(capex)} />
              <Kpi label="TIR a.a." value={num(tir, '%')} />
              <Kpi label="Break-even" value={num(breakEven, ' al.')} />
              <Kpi label="Ticket" value={brl(c?.ticket_realizado_estimado ?? c?.ticket_medio)} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      {children}
    </div>
  )
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-mono">{value}</p>
    </div>
  )
}
