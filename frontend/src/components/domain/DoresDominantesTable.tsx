/**
 * DoresDominantesTable — tabela cross-concorrência das dores mais
 * mencionadas com nominação (quais academias e quantas vezes).
 */
import { CategoriaDorBadge } from './CategoriaDorBadge'
import { cn } from '@/lib/utils'
import type { DorDominanteJSON } from '@/hooks/useRelatorioDetail'
import type { CategoriaDor } from '@/types/domain'

export interface DoresDominantesTableProps {
  dores: DorDominanteJSON[] | undefined
  servicosNaoOferecidos?: string[]
  className?: string
}

export function DoresDominantesTable({
  dores,
  servicosNaoOferecidos,
  className,
}: DoresDominantesTableProps) {
  const temDores = dores && dores.length > 0

  return (
    <div className={cn('space-y-4', className)}>
      {/* Dores dominantes */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <header className="px-4 py-2.5 border-b border-border bg-muted/20">
          <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium">
            Dores dominantes (cross-concorrência)
          </h3>
        </header>
        {!temDores ? (
          <p className="p-4 text-xs text-muted-foreground italic">
            Nenhuma dor dominante consistente foi identificada nos concorrentes analisados.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono border-b border-border">
                  <th className="text-left p-3 font-medium">Dor</th>
                  <th className="text-center p-3 font-medium w-20">Menções</th>
                  <th className="text-left p-3 font-medium">Mencionado por</th>
                </tr>
              </thead>
              <tbody>
                {dores!.map((d, i) => (
                  <tr key={i} className="border-b border-border last:border-b-0">
                    <td className="p-3">
                      <CategoriaDorBadge
                        categoria={d.dor as CategoriaDor}
                        sinal="negativo"
                      />
                    </td>
                    <td className="p-3 text-center font-mono tabular-nums font-semibold">
                      {d.mencoes}
                    </td>
                    <td className="p-3 text-xs">
                      {d.mencionado_por && d.mencionado_por.length > 0 ? (
                        <ul className="space-y-0.5">
                          {d.mencionado_por.map((m, j) => (
                            <li key={j} className="text-muted-foreground">
                              {m.academia}{' '}
                              <span className="font-mono text-[10px]">({m.vezes}x)</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-muted-foreground italic">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Gaps de mercado (serviços que ninguém oferece) */}
      {servicosNaoOferecidos && servicosNaoOferecidos.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium mb-2">
            Gaps de mercado (NINGUÉM oferece)
          </h3>
          <ul className="flex flex-wrap gap-1.5">
            {servicosNaoOferecidos.map((s) => (
              <li
                key={s}
                className="px-2 py-0.5 rounded-md bg-veredito-investigar/20 text-veredito-investigar text-xs font-mono"
              >
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
