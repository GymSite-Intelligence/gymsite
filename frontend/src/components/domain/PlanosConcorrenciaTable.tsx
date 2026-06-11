/**
 * PlanosConcorrenciaTable — planos × preços × oferta da concorrência.
 *
 * Metodologia docs/metodologia/analise_mercado_fitness_fortaleza.md: o
 * posicionamento nasce de saber exatamente o que cada concorrente cobra e
 * entrega por plano. Dados via pesquisa fundamentada (site oficial + fontes
 * recentes); academia sem preço público confiável fica fora — nada inventado.
 */
import { Wallet } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { CompetidorJSON, PlanoPrecoJSON } from '@/hooks/useRelatorioDetail'

const MAX_INCLUI = 4

function PlanoMiniCard({ plano }: { plano: PlanoPrecoJSON }) {
  const inclui = plano.inclui ?? []
  const extras = inclui.length - MAX_INCLUI
  return (
    <div className="rounded-md border border-border bg-background px-3 py-2.5 min-w-[180px] max-w-[240px] flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-xs font-medium truncate">{plano.plano || 'Plano'}</p>
        <p className="text-sm font-semibold font-mono text-primary whitespace-nowrap">
          {plano.preco_mensal || '—'}
        </p>
      </div>
      {plano.fidelidade && (
        <p className="text-[10px] text-muted-foreground font-mono">{plano.fidelidade}</p>
      )}
      {inclui.length > 0 && (
        <ul className="space-y-0.5">
          {inclui.slice(0, MAX_INCLUI).map((item, i) => (
            <li key={i} className="text-[10px] text-muted-foreground leading-snug truncate" title={item}>
              · {item}
            </li>
          ))}
          {extras > 0 && (
            <li className="text-[10px] text-muted-foreground/70 italic">+{extras} itens</li>
          )}
        </ul>
      )}
    </div>
  )
}

export function PlanosConcorrenciaTable({
  competidores,
  className,
}: {
  competidores: CompetidorJSON[]
  className?: string
}) {
  const comPlanos = competidores.filter(
    (c) => Array.isArray(c.planos_precos) && c.planos_precos.length > 0,
  )
  if (comPlanos.length === 0) return null

  return (
    <div className={cn('rounded-lg border border-border bg-card overflow-hidden', className)}>
      <header className="px-4 py-2.5 border-b border-border bg-muted/20 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Wallet size={14} className="text-muted-foreground" />
          <div>
            <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-mono font-medium">
              Planos e preços da concorrência
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Pesquisa em site oficial e fontes recentes · academias sem preço público ficam fora
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground shrink-0">
          {comPlanos.length} de {competidores.length} com preço público
        </span>
      </header>
      <div className="divide-y divide-border">
        {comPlanos.map((c) => (
          <div key={c.place_id ?? c.nome} className="px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <p className="text-sm font-medium">{c.nome}</p>
              {c.bairro_concorrente && (
                <Badge variant="secondary" className="rounded-full px-2 text-[10px] font-normal">
                  {c.bairro_concorrente}
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {(c.planos_precos ?? []).map((p, i) => (
                <PlanoMiniCard key={i} plano={p} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
