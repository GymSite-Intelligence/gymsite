/**
 * ScoreGauge — barra horizontal 0-10 com cor por faixa.
 *
 * Faixas (mesmas do veredito):
 *   8.0-10.0 → aprovado (verde)
 *   6.0-7.9  → ressalvas (amarelo)
 *   4.0-5.9  → investigar (azul)
 *   < 4.0    → reprovado (vermelho)
 *
 * Usado em ScoresDimensionais (3 dim regionais) e nos 2 cards principais
 * de Score Bairro / Score Top 1.
 */
import { cn } from '@/lib/utils'

export interface ScoreGaugeProps {
  /** Valor 0-10 (ou null pra mostrar "—") */
  value: number | null
  /** Label acima da barra */
  label?: string
  /** Texto descritivo abaixo (ex: classificação textual) */
  classification?: string
  /** Variante visual: bar (padrão) ou card (box destacada com score grande) */
  variant?: 'bar' | 'card'
  className?: string
}

function colorForScore(score: number | null) {
  if (score == null) return 'bg-muted-foreground/30'
  if (score >= 8.0) return 'bg-status-good'
  if (score >= 6.0) return 'bg-status-warning'
  if (score >= 4.0) return 'bg-status-investigate'
  return 'bg-status-critical'
}

function textColorForScore(score: number | null) {
  if (score == null) return 'text-muted-foreground'
  if (score >= 8.0) return 'text-status-good'
  if (score >= 6.0) return 'text-status-warning'
  if (score >= 4.0) return 'text-status-investigate'
  return 'text-status-critical'
}

function classifyScore(score: number | null): string {
  if (score == null) return 'sem dados'
  if (score >= 8.0) return 'BOM'
  if (score >= 6.0) return 'COM RESSALVAS'
  if (score >= 4.0) return 'INVESTIGAR'
  return 'CRÍTICO'
}

export function ScoreGauge({
  value,
  label,
  classification,
  variant = 'bar',
  className,
}: ScoreGaugeProps) {
  const pct = value == null ? 0 : Math.min(100, Math.max(0, (value / 10) * 100))
  const color = colorForScore(value)
  const tColor = textColorForScore(value)
  const klass = classification ?? classifyScore(value)
  const formatted = value == null ? '—' : value.toFixed(1)

  if (variant === 'card') {
    return (
      <div className={cn('rounded-lg border border-border bg-card p-5', className)}>
        {label && (
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-mono mb-1">
            {label}
          </div>
        )}
        <div className="flex items-baseline gap-2">
          <span
            className={cn('text-4xl font-bold font-mono tabular-nums', tColor)}
          >
            {formatted}
          </span>
          <span className="text-sm text-muted-foreground">/ 10</span>
        </div>
        <div className={cn('text-xs font-mono mt-1', tColor)}>{klass}</div>
        <div className="mt-3 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={cn('h-full transition-all', color)}
            style={{ width: `${pct}%` }}
            aria-hidden
          />
        </div>
      </div>
    )
  }

  // bar variant (horizontal compacta)
  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-muted-foreground">{label ?? 'Score'}</span>
        <span className="font-mono tabular-nums flex items-baseline gap-2">
          <span className={cn('font-semibold', tColor)}>{formatted}</span>
          <span className={cn('text-[10px] uppercase', tColor)}>{klass}</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={cn('h-full transition-all', color)}
          style={{ width: `${pct}%` }}
          aria-hidden
          role="meter"
          aria-valuenow={value ?? 0}
          aria-valuemin={0}
          aria-valuemax={10}
          aria-label={`${label ?? 'Score'}: ${formatted} de 10`}
        />
      </div>
    </div>
  )
}
