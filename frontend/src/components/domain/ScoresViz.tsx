/**
 * ScoresViz — scores regionais na linguagem de card (mesma do CenariosViz).
 *
 * Drop-in da ScoresDimensionais: mesmas props. 5 cards (3 dimensões + Score
 * Bairro + Top-1 candidato), cada um com número-herói + barra de intensidade
 * (rampa heatmap: baixo→alto = frio→quente). Não recalcula nada.
 */
import type { OutputConsolidado } from '@/hooks/useRelatorioDetail'
import { cn } from '@/lib/utils'

export interface ScoresVizProps {
  scoreBairro: number | null
  scoreTop1: number | null
  scoresRegionais: OutputConsolidado['scores_regionais']
  className?: string
}

/** 0-100 → bin da rampa heatmap (--chart-1..5). Alto score = quente (chart-5). */
function scoreVar(v: number | null): string {
  if (v == null) return 'var(--muted)'
  const bin = Math.min(5, Math.max(1, Math.ceil(v / 20)))
  return `var(--chart-${bin})`
}

function faixa(v: number | null): string {
  if (v == null) return '—'
  if (v >= 70) return 'Alto'
  if (v >= 45) return 'Médio'
  return 'Baixo'
}

export function ScoresViz({
  scoreBairro,
  scoreTop1,
  scoresRegionais,
  className,
}: ScoresVizProps) {
  const demografico = scoresRegionais?.demografico ?? null
  const competitivo =
    scoresRegionais?.competitivo ?? scoresRegionais?.concorrencia ?? null
  const viabilidade = scoresRegionais?.viabilidade ?? null

  const cards: { label: string; value: number | null; hint?: string }[] = [
    { label: 'Demográfico', value: demografico },
    { label: 'Competitivo', value: competitivo },
    { label: 'Viabilidade', value: viabilidade },
    { label: 'Score do Bairro', value: scoreBairro, hint: 'consolidado regional' },
    { label: 'Top-1 Candidato', value: scoreTop1, hint: 'melhor imóvel' },
  ]

  return (
    <div className={cn('grid grid-cols-2 gap-3 lg:grid-cols-5', className)}>
      {cards.map((c) => (
        <div
          key={c.label}
          className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
        >
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {c.label}
          </p>
          <p className="font-mono text-3xl font-bold leading-none">
            {c.value != null ? Math.round(c.value) : '—'}
            <span className="text-base font-normal text-muted-foreground">/100</span>
          </p>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(100, Math.max(0, c.value ?? 0))}%`,
                background: scoreVar(c.value),
              }}
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            <span className="font-medium text-foreground">{faixa(c.value)}</span>
            {c.hint ? ` · ${c.hint}` : ''}
          </p>
        </div>
      ))}
    </div>
  )
}
