/**
 * BairrosRanking — top 10 bairros com melhores scores e mais análises.
 */
import { Trophy, MapPin } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { BairroRankItem } from '@/hooks/useDashboardStats'

export function BairrosRanking({
  data,
  loading,
}: {
  data: BairroRankItem[]
  loading: boolean
}) {
  if (loading) {
    return <Skeleton className="h-96 rounded-xl" />
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top bairros</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhum bairro analisado ainda.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>Top bairros analisados</CardTitle>
        <CardDescription>Ranking por score médio do top candidato</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.map((b, idx) => (
          <div
            key={`${b.bairro}-${b.cidade}`}
            className={cn(
              'flex items-center gap-3 rounded-lg border border-border p-3',
              idx === 0 && 'bg-amber-50/50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900',
            )}
          >
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-muted text-xs font-bold shrink-0">
              {idx === 0 ? <Trophy size={14} className="text-amber-600" /> : idx + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <MapPin size={12} className="text-muted-foreground shrink-0" />
                <span className="text-sm font-medium truncate">{b.bairro}</span>
                <span className="text-xs text-muted-foreground truncate">
                  · {b.cidade}{b.uf ? `/${b.uf}` : ''}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-[10px] text-muted-foreground font-mono">
                  {b.count} relatório{b.count === 1 ? '' : 's'}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {b.aprovacaoPct}% aprov.
                </span>
              </div>
            </div>
            <div className="text-right shrink-0">
              <Badge variant={b.scoreMedio != null && b.scoreMedio >= 7 ? 'success' : b.scoreMedio != null && b.scoreMedio >= 5 ? 'warning' : 'destructive'}>
                {b.scoreMedio?.toFixed(1) ?? '—'}
              </Badge>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
