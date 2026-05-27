import { Link } from '@tanstack/react-router'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { StatusPipelineBadge } from '@/components/domain/StatusPipelineBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { RelatorioResumo } from '@/types/domain'

function fmtData(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
  })
}

export function DashboardRelatoriosTable({
  rows,
  loading,
}: {
  rows: RelatorioResumo[]
  loading: boolean
}) {
  const recent = rows.slice(0, 12)

  return (
    <div className="px-4 lg:px-6">
      <div
        className="flex items-center justify-between gap-2 mb-3"
      >
        <div>
          <h2 className="text-base font-semibold">Relatórios recentes</h2>
          <p className="text-xs text-muted-foreground">
            Dados de v_relatorios_resumo · Supabase
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/relatorios">Ver todos</Link>
        </Button>
      </div>

      {loading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : recent.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
          Nenhum relatório na org.{' '}
          <Link to="/relatorios/new" className="text-primary underline-offset-2 hover:underline">
            Criar primeiro
          </Link>
        </p>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Data</TableHead>
                <TableHead>Local</TableHead>
                <TableHead>Veredito</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead className="text-right">Custo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((r) => (
                <TableRow key={r.id} className="hover:bg-muted/30">
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {fmtData(r.data_execucao ?? r.created_at)}
                  </TableCell>
                  <TableCell>
                    <Link
                      to="/relatorios/$relatorioId"
                      params={{ relatorioId: r.id }}
                      className="font-medium text-sm hover:underline"
                    >
                      {r.bairro}
                      <span className="text-muted-foreground font-normal">
                        {' · '}
                        {r.cidade}
                        {r.uf ? `/${r.uf}` : ''}
                      </span>
                    </Link>
                  </TableCell>
                  <TableCell>
                    {r.veredito ? (
                      <VeredictoBadge veredito={r.veredito} />
                    ) : (
                      <Badge variant="outline">—</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusPipelineBadge status={r.status} />
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">
                    {r.score_top1_candidato?.toFixed(1) ?? '—'}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-xs text-muted-foreground">
                    {r.custo_brl != null
                      ? r.custo_brl.toLocaleString('pt-BR', {
                          style: 'currency',
                          currency: 'BRL',
                        })
                      : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
