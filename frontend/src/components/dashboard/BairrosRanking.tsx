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
  dataSourceLabel,
  relatorioCount,
}: {
  data: BairroRankItem[]
  loading: boolean
  /** Ex.: v_relatorios_resumo · Supabase */
  dataSourceLabel?: string
  /** Total de relatórios que alimentam o ranking (após filtros). */
  relatorioCount?: number
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
        <CardDescription>
          {BAIRROS_RANKING_COPY.description}
          {dataSourceLabel ? (
            <>
              <br />
              <span className="text-muted-foreground/80">
                Dados de {dataSourceLabel}
                {relatorioCount != null ? ` · ${relatorioCount} relatório${relatorioCount === 1 ? '' : 's'} no filtro` : ''}
              </span>
            </>
          ) : null}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.map((item, idx) => (
          <BairroRankRow
            key={`${item.bairro}-${item.cidade}-${item.uf ?? ''}`}
            item={item}
            rank={idx}
            isLeader={idx === 0}
          />
        ))}
      </CardContent>
    </Card>
  )
}
