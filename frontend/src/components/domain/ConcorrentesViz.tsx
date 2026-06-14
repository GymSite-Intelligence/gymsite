/**
 * ConcorrentesViz — concorrentes em mini-cards (visão scannável).
 *
 * Aditivo: fica ACIMA do CompetidorGroup (que mantém os reviews como drill-down).
 * Cada concorrente vira card compacto: nome, rating + estrelas, nº avaliações,
 * distância, bairro, 24h. Cor do rating por faixa (alto=verde, baixo=vermelho).
 */
import type { CompetidorJSON } from '@/hooks/useRelatorioDetail'
import { Clock, MapPin, Star } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ConcorrentesVizProps {
  competidores: CompetidorJSON[] | undefined
  className?: string
}

function ratingColor(r: number | null | undefined): string {
  if (r == null) return 'hsl(var(--status-neutral))'
  if (r >= 4) return 'hsl(var(--veredito-aprovado))'
  if (r >= 3) return 'hsl(var(--veredito-ressalvas))'
  return 'hsl(var(--veredito-reprovado))'
}

export function ConcorrentesViz({ competidores, className }: ConcorrentesVizProps) {
  if (!competidores || competidores.length === 0) return null

  const ordenado = [...competidores].sort(
    (a, b) => (b.rating_geral ?? b.rating_oficial ?? 0) - (a.rating_geral ?? a.rating_oficial ?? 0),
  )

  return (
    <div className={cn('grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4', className)}>
      {ordenado.map((c, i) => {
        const rating = c.rating_geral ?? c.rating_oficial ?? null
        const color = ratingColor(rating)
        const dist = typeof c.distancia_km === 'number' ? `${c.distancia_km.toFixed(1)} km` : null
        return (
          <div
            key={c.place_id ?? `${c.nome}-${i}`}
            className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3.5"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="line-clamp-2 text-sm font-semibold leading-tight" title={c.nome}>
                {c.nome}
              </p>
              {c.tem_24h && (
                <span
                  className="inline-flex shrink-0 items-center gap-0.5 rounded px-1 py-0.5 text-[9px] font-medium"
                  style={{
                    color: 'hsl(var(--veredito-aprovado))',
                    background: 'color-mix(in oklch, hsl(var(--veredito-aprovado)) 16%, transparent)',
                  }}
                >
                  <Clock size={9} /> 24h
                </span>
              )}
            </div>

            <div className="flex items-baseline gap-1.5">
              <Star size={14} className="shrink-0" style={{ color, fill: color }} />
              <span className="font-mono text-xl font-bold leading-none" style={{ color }}>
                {rating != null ? rating.toFixed(1) : '—'}
              </span>
              {c.num_avaliacoes != null && (
                <span className="text-xs text-muted-foreground">({c.num_avaliacoes})</span>
              )}
            </div>

            <div className="mt-auto flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
              {dist && (
                <span className="inline-flex items-center gap-1">
                  <MapPin size={10} /> {dist}
                </span>
              )}
              {c.bairro_concorrente && (
                <span className="truncate">· {c.bairro_concorrente}</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
