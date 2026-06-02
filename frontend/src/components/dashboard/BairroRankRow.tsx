import { MapPin, Trophy } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { BairroRankItem } from '@/lib/dashboard/bairros-ranking'

function scoreBadgeVariant(
  score: number | null,
): 'success' | 'warning' | 'destructive' {
  if (score == null) return 'destructive'
  if (score >= 7) return 'success'
  if (score >= 5) return 'warning'
  return 'destructive'
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
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border border-border p-3',
        isLeader &&
          'bg-amber-50/50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900',
      )}
    >
      <div className="flex items-center justify-center w-7 h-7 rounded-full bg-muted text-xs font-bold shrink-0">
        {isLeader ? (
          <Trophy size={14} className="text-amber-600" />
        ) : (
          rank + 1
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <MapPin size={12} className="text-muted-foreground shrink-0" />
          <span className="text-sm font-medium truncate">{item.bairro}</span>
          <span className="text-xs text-muted-foreground truncate">
            · {item.cidade}
            {item.uf ? `/${item.uf}` : ''}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] text-muted-foreground font-mono">
            {item.count} relatório{item.count === 1 ? '' : 's'}
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">
            {item.aprovacaoPct}% aprov.
          </span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <Badge variant={scoreBadgeVariant(item.scoreMedio)}>
          {item.scoreMedio?.toFixed(1) ?? '—'}
        </Badge>
      </div>
    </div>
  )
}
