/**
 * CustosPage — dashboard de custos (admin/owner only).
 *
 * Estrutura:
 *   - 4 cards de resumo (período, total, médio, total tokens)
 *   - Filtro de período (este mês / últimos 30d / tudo)
 *   - Tabela de relatórios com cidade/status/tempo/tokens/custo
 *   - Click numa row → expande in-place mostrando breakdown por agente
 *
 * Gate: render só se useMembership().isOwnerOrAdmin. Quem cair aqui sem
 * permissão (URL direta) vê uma mensagem de bloqueio.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { ChevronDown, ChevronRight, Loader2, BarChart3 } from 'lucide-react'
import { useMembership } from '@/hooks/useMembership'
import {
  useCustosRelatorios,
  useCustosAgentes,
  type Periodo,
  type RelatorioCustoRow,
} from '@/hooks/useCustos'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'

const FMT_BRL = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 4,
})

const FMT_BRL_SHORT = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const FMT_INT = new Intl.NumberFormat('pt-BR')

const FMT_DATE = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const PERIODOS: { value: Periodo; label: string }[] = [
  { value: 'mes', label: 'Este mês' },
  { value: '30d', label: 'Últimos 30 dias' },
  { value: 'tudo', label: 'Tudo' },
]

export function CustosPage() {
  const { isOwnerOrAdmin, loading: roleLoading } = useMembership()
  const navigate = useNavigate()
  const redirectedRef = useRef(false)
  const [periodo, setPeriodo] = useState<Periodo>('mes')
  const [expandido, setExpandido] = useState<string | null>(null)
  const { data: relatorios, isLoading } = useCustosRelatorios(periodo)

  // Resumos calculados em cima do dataset atual.
  // `porOrg` agrega total + count por org pra visão multi-tenant.
  const resumo = useMemo(() => {
    if (!relatorios) return null
    const validos = relatorios.filter((r) => r.custo_brl != null)
    const total = validos.reduce((s, r) => s + (r.custo_brl ?? 0), 0)
    const totalTokens = validos.reduce((s, r) => s + (r.tokens_total ?? 0), 0)
    const medio = validos.length ? total / validos.length : 0

    const porOrgMap = new Map<
      string,
      { orgNome: string; qtd: number; total: number; tokens: number }
    >()
    for (const r of relatorios) {
      const slot = porOrgMap.get(r.org_id) ?? {
        orgNome: r.org_nome,
        qtd: 0,
        total: 0,
        tokens: 0,
      }
      slot.qtd += 1
      if (r.custo_brl != null) slot.total += r.custo_brl
      if (r.tokens_total != null) slot.tokens += r.tokens_total
      porOrgMap.set(r.org_id, slot)
    }
    const porOrg = Array.from(porOrgMap.entries())
      .map(([orgId, v]) => ({ orgId, ...v }))
      .sort((a, b) => b.total - a.total)

    return {
      qtd: relatorios.length,
      qtdValidos: validos.length,
      total,
      medio,
      totalTokens,
      porOrg,
      multiOrg: porOrg.length >= 2,
    }
  }, [relatorios])

  useEffect(() => {
    if (roleLoading || isOwnerOrAdmin) {
      redirectedRef.current = false
      return
    }
    if (redirectedRef.current) return
    redirectedRef.current = true
    void navigate({ to: '/relatorios', replace: true })
  }, [roleLoading, isOwnerOrAdmin, navigate])

  if (roleLoading) {
    return (
      <div className="py-12 text-center text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 size={16} className="animate-spin" />
        Carregando…
      </div>
    )
  }

  if (!isOwnerOrAdmin) {
    return (
      <div className="py-12 text-center text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 size={16} className="animate-spin" />
        Redirecionando…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BarChart3 size={22} />
            Custos
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Consumo Gemini por relatório. Acesso restrito a owners/admins da org.
          </p>
        </div>
        <div className="flex items-center gap-1">
          {PERIODOS.map((p) => (
            <Button
              key={p.value}
              variant={periodo === p.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPeriodo(p.value)}
            >
              {p.label}
            </Button>
          ))}
        </div>
      </header>

      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Relatórios no período"
          value={
            resumo ? `${resumo.qtdValidos}/${resumo.qtd}` : '—'
          }
          hint={resumo ? 'com custo / total' : undefined}
        />
        <MetricCard
          label="Custo total"
          value={resumo ? FMT_BRL_SHORT.format(resumo.total) : '—'}
        />
        <MetricCard
          label="Custo médio / relatório"
          value={resumo ? FMT_BRL_SHORT.format(resumo.medio) : '—'}
        />
        <MetricCard
          label="Tokens totais"
          value={resumo ? FMT_INT.format(resumo.totalTokens) : '—'}
        />
      </section>

      {resumo?.multiOrg && (
        <section className="rounded-lg border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-tight">
              Consumo por organização
            </h2>
            <span className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              {resumo.porOrg.length} orgs
            </span>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Org</TableHead>
                <TableHead className="text-right">Relatórios</TableHead>
                <TableHead className="text-right">Tokens</TableHead>
                <TableHead className="text-right">Custo (BRL)</TableHead>
                <TableHead className="text-right">% total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {resumo.porOrg.map((row) => {
                const pct = resumo.total
                  ? ((row.total / resumo.total) * 100).toFixed(1)
                  : '0.0'
                return (
                  <TableRow key={row.orgId}>
                    <TableCell className="font-medium">
                      {row.orgNome}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {row.qtd}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {FMT_INT.format(row.tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {FMT_BRL_SHORT.format(row.total)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">
                      {pct}%
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </section>
      )}

      <section className="rounded-lg border border-border">
        {isLoading ? (
          <div className="py-12 text-center text-muted-foreground flex items-center justify-center gap-2">
            <Loader2 size={16} className="animate-spin" />
            Carregando relatórios…
          </div>
        ) : !relatorios?.length ? (
          <div className="py-12 text-center text-muted-foreground text-sm">
            Nenhum relatório no período.
          </div>
        ) : (
          <Table zebra>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Data</TableHead>
                <TableHead>Cidade / Bairro</TableHead>
                {resumo?.multiOrg && <TableHead>Org</TableHead>}
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Tempo</TableHead>
                <TableHead className="text-right">Tokens</TableHead>
                <TableHead className="text-right">Custo (BRL)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {relatorios.map((r) => (
                <RelatorioCustoRowView
                  key={r.id}
                  relatorio={r}
                  showOrg={resumo?.multiOrg ?? false}
                  expandido={expandido === r.id}
                  onToggle={() =>
                    setExpandido((cur) => (cur === r.id ? null : r.id))
                  }
                />
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  )
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
        {label}
      </p>
      <p className="text-2xl font-semibold tracking-tight mt-1">{value}</p>
      {hint && (
        <p className="text-[10px] text-muted-foreground mt-1">{hint}</p>
      )}
    </div>
  )
}

function RelatorioCustoRowView({
  relatorio: r,
  showOrg,
  expandido,
  onToggle,
}: {
  relatorio: RelatorioCustoRow
  showOrg: boolean
  expandido: boolean
  onToggle: () => void
}) {
  const cidadeBairro =
    r.cidade || r.bairro
      ? `${r.cidade ?? '—'} / ${r.bairro ?? '—'}`
      : '—'
  // Quando há coluna Org, colSpan da linha expandida muda
  const cols = showOrg ? 8 : 7
  return (
    <>
      <TableRow className="cursor-pointer" onClick={onToggle}>
        <TableCell className="w-8 text-muted-foreground">
          {expandido ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </TableCell>
        <TableCell className="font-mono text-xs">
          {FMT_DATE.format(new Date(r.created_at))}
        </TableCell>
        <TableCell>{cidadeBairro}</TableCell>
        {showOrg && (
          <TableCell className="text-sm">{r.org_nome}</TableCell>
        )}
        <TableCell>
          <StatusBadge status={r.status} />
        </TableCell>
        <TableCell className="text-right font-mono text-xs">
          {r.tempo_execucao_segundos != null
            ? `${r.tempo_execucao_segundos}s`
            : '—'}
        </TableCell>
        <TableCell className="text-right font-mono text-xs">
          {r.tokens_total != null ? FMT_INT.format(r.tokens_total) : '—'}
        </TableCell>
        <TableCell className="text-right font-mono">
          {r.custo_brl != null ? FMT_BRL.format(r.custo_brl) : '—'}
        </TableCell>
      </TableRow>
      {expandido && (
        <TableRow>
          <TableCell colSpan={cols} className="bg-muted/20 p-0">
            <AgenteBreakdown relatorioId={r.id} />
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

function AgenteBreakdown({ relatorioId }: { relatorioId: string }) {
  const { data, isLoading } = useCustosAgentes(relatorioId)
  if (isLoading) {
    return (
      <div className="py-6 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
        <Loader2 size={14} className="animate-spin" />
        Carregando breakdown…
      </div>
    )
  }
  if (!data?.length) {
    return (
      <div className="py-6 text-center text-muted-foreground text-sm">
        Sem detalhamento por agente. Relatório gerado antes da v1.7 ou
        executado sem telemetria.
      </div>
    )
  }
  const totalAgentes = data.reduce((s, r) => s + (r.custo_brl ?? 0), 0)
  return (
    <div className="p-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Agente</TableHead>
            <TableHead>Modelo</TableHead>
            <TableHead className="text-right">Tokens in</TableHead>
            <TableHead className="text-right">Tokens out</TableHead>
            <TableHead className="text-right">Custo (BRL)</TableHead>
            <TableHead className="text-right">% do total</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row) => {
            const pct = totalAgentes
              ? ((row.custo_brl / totalAgentes) * 100).toFixed(1)
              : '0.0'
            return (
              <TableRow key={row.agente}>
                <TableCell className="font-medium">{row.agente}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {row.modelo}
                </TableCell>
                <TableCell className="text-right font-mono text-xs">
                  {FMT_INT.format(row.tokens_in)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs">
                  {FMT_INT.format(row.tokens_out)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {FMT_BRL.format(row.custo_brl)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs text-muted-foreground">
                  {pct}%
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === 'done'
      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
      : status === 'failed'
        ? 'bg-red-500/15 text-red-700 dark:text-red-300'
        : status === 'running' || status === 'queued'
          ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
          : 'bg-muted text-muted-foreground'
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium font-mono uppercase tracking-wider',
        color,
      )}
    >
      {status}
    </span>
  )
}
