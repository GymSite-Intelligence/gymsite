/**
 * DistribuicaoViz — distribuição geográfica dos concorrentes (ranking heatmap).
 * Drop-in da DistribuicaoBairrosTable: barra de densidade por bairro, intensidade
 * pela rampa heatmap, bairro-alvo destacado. Não recalcula nada.
 */
import type { DistribuicaoBairroJSON } from '@/hooks/useRelatorioDetail'
import { cn } from '@/lib/utils'

export interface DistribuicaoVizProps {
  distribuicao: DistribuicaoBairroJSON[]
  bairroAlvo?: string
  className?: string
}

/** count relativo → bin da rampa heatmap (--chart-1..5). Mais concorrentes = mais quente. */
function densVar(ratio: number): string {
  const bin = Math.min(5, Math.max(1, Math.ceil(ratio * 5)))
  return `var(--chart-${bin})`
}

export function DistribuicaoViz({ distribuicao, bairroAlvo, className }: DistribuicaoVizProps) {
  if (!distribuicao || distribuicao.length === 0) return null
  const max = Math.max(...distribuicao.map((d) => d.count), 1)
  const ordenado = [...distribuicao].sort((a, b) => b.count - a.count)

  return (
    <div className={cn('rounded-xl border border-border bg-card p-4', className)}>
      <div className="space-y-2.5">
        {ordenado.map((d) => {
          const ratio = d.count / max
          const isAlvo =
            !!bairroAlvo && d.bairro.toLowerCase() === bairroAlvo.toLowerCase()
          return (
            <div key={d.bairro} className="flex items-center gap-3">
              <span
                className={cn(
                  'w-36 shrink-0 truncate text-sm',
                  isAlvo ? 'font-semibold text-primary' : 'text-foreground',
                )}
                title={d.bairro}
              >
                {d.bairro}
                {isAlvo && <span className="ml-1 text-[10px] text-primary">● alvo</span>}
              </span>
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn('h-full rounded-full transition-all', isAlvo && 'ring-1 ring-primary')}
                  style={{ width: `${Math.max(4, ratio * 100)}%`, background: densVar(ratio) }}
                />
              </div>
              <span className="w-8 shrink-0 text-right font-mono text-sm tabular-nums">
                {d.count}
              </span>
            </div>
          )
        })}
      </div>
      <p className="mt-3 border-t border-border pt-2 text-[11px] text-muted-foreground">
        Densidade de concorrentes por bairro · cor = intensidade (frio→quente)
      </p>
    </div>
  )
}
