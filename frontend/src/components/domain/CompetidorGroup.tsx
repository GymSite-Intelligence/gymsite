/**
 * CompetidorGroup — agrupa competidores por bairro_concorrente.
 *
 * Cada bairro é uma seção com lista de academias. Cada academia tem header
 * (rating + nº avaliações + badge 24h) + reviews categorizadas.
 *
 * Quando bairro_concorrente está ausente (mocks antigos), todos caem em
 * um grupo "Outros".
 */
import { Clock, MapPin, Star } from 'lucide-react'
import { ReviewItem } from './ReviewItem'
import { cn } from '@/lib/utils'
import type { CompetidorJSON } from '@/hooks/useRelatorioDetail'

export interface CompetidorGroupProps {
  competidores: CompetidorJSON[]
  className?: string
}

function groupByBairro(
  competidores: CompetidorJSON[],
): { bairro: string; itens: CompetidorJSON[] }[] {
  const map = new Map<string, CompetidorJSON[]>()
  for (const c of competidores) {
    const key = c.bairro_concorrente ?? 'Outros'
    const arr = map.get(key) ?? []
    arr.push(c)
    map.set(key, arr)
  }
  return Array.from(map.entries())
    .map(([bairro, itens]) => ({ bairro, itens }))
    .sort((a, b) => b.itens.length - a.itens.length)
}

export function CompetidorGroup({ competidores, className }: CompetidorGroupProps) {
  if (!competidores || competidores.length === 0) {
    return (
      <div className={cn('rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground', className)}>
        Nenhum concorrente identificado neste relatório.
      </div>
    )
  }

  const grupos = groupByBairro(competidores)

  return (
    <div className={cn('space-y-6', className)}>
      {grupos.map(({ bairro, itens }) => (
        <section key={bairro} className="space-y-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <MapPin size={14} className="text-muted-foreground" />
            <span>{bairro}</span>
            <span className="text-muted-foreground font-normal font-mono text-xs">
              ({itens.length} {itens.length === 1 ? 'academia' : 'academias'})
            </span>
          </h3>

          <div className="space-y-3">
            {itens.map((comp, i) => (
              <CompetidorCard key={`${comp.nome}-${i}`} competidor={comp} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function CompetidorCard({ competidor }: { competidor: CompetidorJSON }) {
  const reviews = competidor.reviews_traduzidas ?? competidor.reviews ?? []
  const rating = competidor.rating_geral
  const numAval = competidor.num_avaliacoes

  return (
    <article className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <h4 className="font-semibold text-sm leading-tight">{competidor.nome}</h4>
          {competidor.endereco && (
            <p className="text-[10px] font-mono text-muted-foreground mt-0.5 truncate">
              {competidor.endereco}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs shrink-0">
          {rating != null && (
            <span className="inline-flex items-center gap-1 font-mono">
              <Star size={12} className="fill-veredito-ressalvas text-veredito-ressalvas" />
              {rating.toFixed(1)}
              {numAval != null && (
                <span className="text-muted-foreground">({numAval})</span>
              )}
            </span>
          )}
          {competidor.tem_24h && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0 rounded text-[10px] bg-veredito-aprovado/20 text-veredito-aprovado font-mono">
              <Clock size={10} /> 24h
            </span>
          )}
        </div>
      </div>

      {reviews.length > 0 ? (
        <div className="space-y-3 pt-2 border-t border-border">
          {reviews.slice(0, 5).map((r, i) => (
            <ReviewItem key={i} review={r} />
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground italic pt-2 border-t border-border">
          Nenhuma review categorizada para este concorrente.
        </p>
      )}
    </article>
  )
}
