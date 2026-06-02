/**
 * BairrosRanking — top N bairros por score médio do top candidato (dados do hook).
 */
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  BAIRROS_RANKING_COPY,
  type BairroRankItem,
} from '@/lib/dashboard/bairros-ranking'
import { BairroRankRow } from '@/components/dashboard/BairroRankRow'

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
          <CardTitle>{BAIRROS_RANKING_COPY.emptyTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            {BAIRROS_RANKING_COPY.emptyMessage}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>{BAIRROS_RANKING_COPY.title}</CardTitle>
        <CardDescription>{BAIRROS_RANKING_COPY.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.map((item, idx) => (
          <BairroRankRow
            key={`${item.bairro}-${item.cidade}`}
            item={item}
            rank={idx}
            isLeader={idx === 0}
          />
        ))}
      </CardContent>
    </Card>
  )
}
