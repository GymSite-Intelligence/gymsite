/**
 * DoresPorCategoria — reclamações SEGMENTADAS por categoria de dor,
 * CONSOLIDADAS por academia (ranking).
 *
 * O quote é irrelevante (há link pro review no Google Maps do concorrente).
 * Cada categoria vira um grupo; dentro, 1 linha por academia (não por review):
 * academia · nº de reclamações nessa dor · pior nota · link. Ranqueado por volume.
 */
import type { CompetidorJSON } from '@/hooks/useRelatorioDetail'
import { ExternalLink, Star } from 'lucide-react'
import { cn } from '@/lib/utils'

const LABELS: Record<string, string> = {
  atendimento: 'Atendimento',
  lotacao: 'Lotação',
  equipamento: 'Equipamento',
  seguranca: 'Segurança',
  climatizacao: 'Climatização',
  contrato: 'Contrato',
  ausencia: 'Serviço ausente',
  servico: 'Serviço',
  ruido: 'Ruído',
  estrutura: 'Estrutura',
  preco: 'Preço',
  limpeza: 'Limpeza',
  horarios: 'Horários',
  estacionamento: 'Estacionamento',
}

function label(cat: string): string {
  const base = cat.split('_')[0]
  return LABELS[base] ?? cat.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

interface AcadDor {
  competidor: string
  count: number
  piorNota: number
  link?: string | null
}

export interface DoresPorCategoriaProps {
  competidores: CompetidorJSON[] | undefined
  className?: string
}

export function DoresPorCategoria({ competidores, className }: DoresPorCategoriaProps) {
  if (!competidores || competidores.length === 0) return null

  // cat → (academia → consolidado)
  const grupos = new Map<string, Map<string, AcadDor>>()
  for (const c of competidores) {
    const reviews = c.reviews ?? c.reviews_traduzidas ?? []
    for (const r of reviews) {
      if ((r.rating ?? 5) > 3) continue
      const cat = (r.categoria_dor || '').trim()
      if (!cat || cat === 'outra') continue
      const porAcad = grupos.get(cat) ?? new Map<string, AcadDor>()
      const slot = porAcad.get(c.nome)
      const nota = r.rating ?? 0
      if (slot) {
        slot.count += 1
        slot.piorNota = Math.min(slot.piorNota, nota)
      } else {
        porAcad.set(c.nome, {
          competidor: c.nome,
          count: 1,
          piorNota: nota,
          link: c.google_maps_uri,
        })
      }
      grupos.set(cat, porAcad)
    }
  }
  if (grupos.size === 0) return null

  const ordenado = Array.from(grupos.entries())
    .map(([cat, porAcad]) => {
      const acads = Array.from(porAcad.values()).sort((a, b) => b.count - a.count)
      const total = acads.reduce((s, a) => s + a.count, 0)
      return { cat, acads, total }
    })
    .sort((a, b) => b.total - a.total)

  const maxTotal = Math.max(...ordenado.map((g) => g.total), 1)

  return (
    <div className={cn('grid grid-cols-1 gap-3 md:grid-cols-2', className)}>
      {ordenado.map(({ cat, acads, total }) => {
        const bin = Math.min(5, Math.max(1, Math.ceil((total / maxTotal) * 5)))
        const color = `var(--chart-${bin})`
        return (
          <div key={cat} className="flex flex-col rounded-xl border border-border bg-card">
            <div
              className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5"
              style={{ borderLeftWidth: 3, borderLeftColor: color }}
            >
              <span className="flex items-center gap-2 text-sm font-semibold">
                <span className="size-2 rounded-full" style={{ background: color }} />
                {label(cat)}
              </span>
              <span className="font-mono text-xs text-muted-foreground">
                {acads.length} academia{acads.length === 1 ? '' : 's'} · {total} reclamaç
                {total === 1 ? 'ão' : 'ões'}
              </span>
            </div>
            <ul className="divide-y divide-border">
              {acads.map((a, i) => {
                const row = (
                  <>
                    <span className="w-5 shrink-0 text-center font-mono text-xs text-muted-foreground">
                      {i + 1}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium" title={a.competidor}>
                      {a.competidor}
                    </span>
                    <span
                      className="shrink-0 rounded-full px-2 py-0.5 font-mono text-xs font-semibold"
                      style={{ color, background: `color-mix(in oklch, ${color} 15%, transparent)` }}
                    >
                      {a.count}×
                    </span>
                    <span className="inline-flex shrink-0 items-center gap-0.5 font-mono text-xs text-muted-foreground">
                      <Star size={10} className="fill-veredito-reprovado text-veredito-reprovado" />
                      {a.piorNota}
                    </span>
                    {a.link && (
                      <ExternalLink
                        size={12}
                        className="shrink-0 text-muted-foreground group-hover:text-foreground"
                      />
                    )}
                  </>
                )
                return a.link ? (
                  <li key={i}>
                    <a
                      href={a.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-center gap-2 px-4 py-2 transition-colors hover:bg-muted"
                    >
                      {row}
                    </a>
                  </li>
                ) : (
                  <li key={i} className="flex items-center gap-2 px-4 py-2">
                    {row}
                  </li>
                )
              })}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
