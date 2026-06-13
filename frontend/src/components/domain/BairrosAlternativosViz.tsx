/**
 * BairrosAlternativosViz — card rico por bairro alternativo.
 * Expõe status competitivo, prioridade, contagem e lista de academias.
 * Bairros fallback (dados_confiaveis=false) recebem aviso visual distinto.
 */
import { useState } from 'react'
import type { BairroAlternativoJSON } from '@/hooks/useRelatorioDetail'
import { MapPin, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface BairrosAlternativosVizProps {
  bairros: BairroAlternativoJSON[]
  className?: string
}

function prioridadeConfig(prioridade: string | undefined) {
  switch ((prioridade || '').toUpperCase()) {
    case 'ALTA':
      return { label: 'ALTA', className: 'bg-green-500/15 text-green-400 border-green-500/30' }
    case 'MEDIA':
      return { label: 'MÉDIA', className: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' }
    case 'BAIXA':
      return { label: 'BAIXA', className: 'bg-red-500/15 text-red-400 border-red-500/30' }
    default:
      return { label: prioridade || '—', className: 'bg-muted/50 text-muted-foreground border-border' }
  }
}

function statusColor(status: string | undefined) {
  const s = status || ''
  if (s.includes('🟢')) return 'text-green-400'
  if (s.includes('🟡')) return 'text-yellow-400'
  if (s.includes('🔴')) return 'text-red-400'
  return 'text-muted-foreground'
}

function BairroCard({ b, i }: { b: BairroAlternativoJSON; i: number }) {
  const [expanded, setExpanded] = useState(false)
  const isFallback = b.dados_confiaveis === false
  const prio = prioridadeConfig(b.prioridade_ajustada)
  const hasAcademias = (b.academias_existentes?.length ?? 0) > 0
  const count = b.concorrentes_no_bairro ?? null

  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-xl border p-4 transition-colors',
        isFallback
          ? 'border-dashed border-border/60 bg-muted/20 opacity-70'
          : 'border-border bg-card',
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-2">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 font-mono text-xs font-bold text-primary">
          {i + 1}
        </span>
        <MapPin size={14} className="mt-0.5 shrink-0 text-muted-foreground" />
        <p className="flex-1 text-sm font-semibold leading-tight">{b.bairro}</p>
        {/* Prioridade badge */}
        <span
          className={cn(
            'shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold',
            prio.className,
          )}
        >
          {prio.label}
        </span>
      </div>

      {/* Motivo */}
      {b.motivo && (
        <p className="text-sm leading-relaxed text-muted-foreground">{b.motivo}</p>
      )}

      {/* Status + contagem */}
      {!isFallback && (b.status || count !== null) && (
        <div className="flex items-center gap-3 text-xs">
          {b.status && (
            <span className={cn('font-medium', statusColor(b.status))}>{b.status}</span>
          )}
          {count !== null && (
            <span className="text-muted-foreground">
              {count === 0 ? 'Nenhuma academia mapeada' : `${count} academia${count > 1 ? 's' : ''} no raio`}
            </span>
          )}
        </div>
      )}

      {/* Lista de academias (colapsável) */}
      {hasAcademias && !isFallback && (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? 'Ocultar' : 'Ver academias concorrentes'}
          </button>
          {expanded && (
            <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
              {b.academias_existentes!.map((nome, idx) => (
                <li key={idx} className="flex items-start gap-1">
                  <span className="mt-0.5 text-border">•</span>
                  <span>{nome}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Aviso fallback */}
      {isFallback && (
        <div className="flex items-start gap-1.5 rounded-md bg-muted/40 p-2 text-xs text-muted-foreground">
          <AlertTriangle size={12} className="mt-0.5 shrink-0 text-yellow-500" />
          <span>Bairro não verificado — cidade sem mapeamento específico. Pesquise manualmente antes de decidir.</span>
        </div>
      )}
    </div>
  )
}

export function BairrosAlternativosViz({ bairros, className }: BairrosAlternativosVizProps) {
  if (!bairros || bairros.length === 0) return null
  return (
    <div className={cn('grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3', className)}>
      {bairros.map((b, i) => (
        <BairroCard key={`${b.bairro}-${i}`} b={b} i={i} />
      ))}
    </div>
  )
}
