import { useState, useCallback } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { GitCompare, X } from 'lucide-react'
import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { OceanoBadge } from '@/components/domain/OceanoBadge'
import { StatusPipelineBadge } from '@/components/domain/StatusPipelineBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { RerunPipelineButton } from '@/components/domain/RerunPipelineButton'
import { DeleteRelatorioButton } from '@/components/domain/DeleteRelatorioButton'
import { needsRelatorioRerun } from '@/lib/relatorio-completeness'
import { getDashboardDataSourceLabel } from '@/lib/dashboard/data-source'
import type { RelatorioResumo } from '@/types/domain'

function fmtData(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
  })
}

export interface DashboardRelatoriosTableProps {
  rows: RelatorioResumo[]
  loading: boolean
  onClickRow?: (id: string) => void
}

export function DashboardRelatoriosTable({
  rows,
  loading,
  onClickRow,
}: DashboardRelatoriosTableProps) {
  const navigate = useNavigate()
  const [modoComparar, setModoComparar] = useState(false)
  const [selecionados, setSelecionados] = useState<string[]>([])

  const recent = rows.slice(0, 12)

  const toggleSelecao = useCallback((id: string) => {
    setSelecionados((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 2) return [prev[1], id]
      return [...prev, id]
    })
  }, [])

  const irParaComparador = useCallback(() => {
    if (selecionados.length !== 2) return
    navigate({
      to: '/comparar',
      search: { a: selecionados[0], b: selecionados[1] },
    })
  }, [navigate, selecionados])

  const desativarModoComparar = useCallback(() => {
    setModoComparar(false)
    setSelecionados([])
  }, [])

  return (
    <div className="px-4 lg:px-6 relative">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div>
          <h2 className="text-base font-semibold">Relatórios recentes</h2>
          <p className="text-xs text-muted-foreground">
            Dados de {getDashboardDataSourceLabel()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={modoComparar ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setModoComparar((v) => !v)
              setSelecionados([])
            }}
          >
            <GitCompare size={14} className="mr-1.5" />
            {modoComparar ? 'Cancelar' : 'Comparar'}
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to="/relatorios">Ver todos</Link>
          </Button>
        </div>
      </div>

      {loading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : recent.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
          Nenhum relatório na org.{' '}
          <Link
            to="/relatorios/new"
            className="text-primary underline-offset-2 hover:underline"
          >
            Criar primeiro
          </Link>
        </p>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                {modoComparar && <TableHead className="w-10" />}
                <TableHead>Data</TableHead>
                <TableHead>Local</TableHead>
                <TableHead>Viabilidade</TableHead>
                <TableHead>Mercado</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead className="text-right">Custo</TableHead>
                <TableHead className="w-[140px] text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((r) => {
                const selecionado = selecionados.includes(r.id)
                return (
                  <TableRow
                    key={r.id}
                    className={cn(
                      'hover:bg-muted/30 transition-colors',
                      !modoComparar && 'cursor-pointer',
                      selecionado && 'bg-primary/5',
                    )}
                    onClick={() => {
                      if (!modoComparar && onClickRow) {
                        onClickRow(r.id)
                      }
                    }}
                  >
                    {modoComparar && (
                      <TableCell
                        className="py-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Checkbox
                          checked={selecionado}
                          onCheckedChange={() => toggleSelecao(r.id)}
                          aria-label={`Selecionar ${r.bairro}`}
                        />
                      </TableCell>
                    )}
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {fmtData(r.data_execucao ?? r.created_at)}
                    </TableCell>
                    <TableCell>
                      <Link
                        to="/relatorios/$relatorioId"
                        params={{ relatorioId: r.id }}
                        className="font-medium text-sm hover:underline"
                        onClick={(e) => e.stopPropagation()}
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
                      <OceanoBadge veredito={r.veredito_posicionamento} compact />
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
                    <TableCell
                      className="text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <DeleteRelatorioButton
                          relatorioId={r.id}
                          label={`${r.bairro} · ${r.cidade}`}
                        />
                        {needsRelatorioRerun(r) ? (
                          <RerunPipelineButton
                            relatorioId={r.id}
                            status={r.status}
                            label="Gerar novamente"
                            size="sm"
                            stopPropagation
                          />
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Barra flutuante de comparação */}
      {modoComparar && (
        <div
          className={cn(
            'fixed bottom-6 left-1/2 -translate-x-1/2 z-40 transition-all',
            selecionados.length === 0
              ? 'pointer-events-none opacity-0 translate-y-2'
              : 'opacity-100',
          )}
        >
          <div className="flex items-center gap-3 rounded-lg border border-border bg-card shadow-lg px-4 py-2.5">
            <button
              onClick={desativarModoComparar}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Cancelar"
            >
              <X size={14} />
            </button>
            <span className="text-xs font-mono text-muted-foreground">
              {selecionados.length}/2 selecionados
            </span>
            {selecionados.length === 2 && (
              <Button size="sm" onClick={irParaComparador}>
                <GitCompare size={14} /> Comparar
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
