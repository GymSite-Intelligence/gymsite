/**
 * DistribuicaoBairrosTable — tabela compacta mostrando contagem de
 * concorrentes por bairro (no raio de 3km do bairro alvo).
 */
import { cn } from '@/lib/utils'
import type { DistribuicaoBairroJSON } from '@/hooks/useRelatorioDetail'

export interface DistribuicaoBairrosTableProps {
  distribuicao: DistribuicaoBairroJSON[] | undefined
  bairroAlvo?: string
  className?: string
}

export function DistribuicaoBairrosTable({
  distribuicao,
  bairroAlvo,
  className,
}: DistribuicaoBairrosTableProps) {
  if (!distribuicao || distribuicao.length === 0) {
    return null
  }

  const max = Math.max(...distribuicao.map((d) => d.count))

  return (
    <div className={cn('rounded-lg border border-border bg-card overflow-hidden', className)}>
      <header className="px-4 py-2.5 border-b border-border bg-muted/20">
        <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium">
          Distribuição geográfica dos concorrentes
        </h3>
      </header>
      <ul className="divide-y divide-border">
        {distribuicao.map((d) => {
          const isAlvo = bairroAlvo && d.bairro.toLowerCase() === bairroAlvo.toLowerCase()
          const widthPct = (d.count / max) * 100
          return (
            <li
              key={d.bairro}
              className={cn(
                'flex items-center gap-3 px-4 py-2.5',
                isAlvo && 'bg-primary/10',
              )}
            >
              <div className="w-32 shrink-0 text-sm font-medium flex items-center gap-2">
                {d.bairro}
                {isAlvo && (
                  <span className="text-[9px] px-1 rounded bg-primary text-primary-foreground font-mono">
                    ALVO
                  </span>
                )}
              </div>
              <div className="flex-1 relative h-5">
                <div className="absolute inset-y-0 left-0 bg-veredito-investigar/60 rounded" style={{ width: `${widthPct}%` }} />
                <div className="absolute inset-0 flex items-center px-2 text-[10px] font-mono">
                  <span className="text-foreground/70 truncate">
                    {d.academias.slice(0, 3).join(', ')}
                    {d.academias.length > 3 && ` +${d.academias.length - 3}`}
                  </span>
                </div>
              </div>
              <div className="w-10 text-right font-mono text-sm tabular-nums">
                {d.count}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
