import { MapPin, Trophy } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { BairroRankItem } from '@/lib/dashboard/bairros-ranking'

/** Cor do score via tokens runtime (consistente com veredito do report). */
function scoreColor(score: number | null): string {
  if (score == null) return 'var(--muted-foreground)'
  if (score >= 7) return 'hsl(var(--veredito-aprovado))'
  if (score >= 5) return 'hsl(var(--veredito-ressalvas))'
  return 'hsl(var(--veredito-reprovado))'
}

export function BairroRankRow({
  item,
  rank,
  isLeader,
}: {
  item: BairroRankItem
  rank: number
  isLeader: boolean
}) {
  const color = scoreColor(item.scoreMedio)
  const pct = item.scoreMedio != null ? Math.min(100, (item.scoreMedio / 10) * 100) : 0

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border border-border p-3 transition-colors',
        isLeader && 'bg-accent/5 ring-1 ring-accent/40',
      )}
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold">
        {isLeader ? <Trophy size={14} className="text-accent" /> : rank + 1}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <MapPin size={12} className="shrink-0 text-muted-foreground" />
          <span className="truncate text-sm font-medium">{item.bairro}</span>
          <span className="truncate text-xs text-muted-foreground">
            · {item.cidade}
            {item.uf ? `/${item.uf}` : ''}
          </span>
        </div>
        <div className="mt-1 flex items-center gap-3">
          <span className="font-mono text-[10px] text-muted-foreground">
            {item.count} relatório{item.count === 1 ? '' : 's'}
          </span>
          <span className="font-mono text-[10px] text-muted-foreground">
            {item.aprovacaoPct}% aprov.
          </span>
        </div>
      </div>
      {/* Score: valor + mini barra de intensidade */}
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="font-mono text-sm font-semibold tabular-nums" style={{ color }}>
          {item.scoreMedio?.toFixed(1) ?? '—'}
        </span>
        <div className="h-1 w-12 overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
    </div>
  )
}
