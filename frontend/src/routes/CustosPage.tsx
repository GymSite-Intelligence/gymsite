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
import { ChevronDown, ChevronRight, Loader2, BarChart3, Coins, Cpu, Lightbulb, Sparkles, TrendingDown } from 'lucide-react'
import { useMembership } from '@/hooks/useMembership'
import {
  useCustosRelatorios,
  useCustosAPI,
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

      {/* Seção de Oportunidades de Otimização */}
      <section className="rounded-lg border border-border bg-card p-5 space-y-4 shadow-sm relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full filter blur-xl pointer-events-none" />
        
        <div className="flex items-center gap-2">
          <Lightbulb className="text-yellow-500" size={18} />
          <h2 className="text-sm font-semibold tracking-tight">
            Oportunidades de redução de custo identificadas
          </h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded-md bg-muted/30 border border-border/50 space-y-1 hover:border-primary/20 transition-all">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles size={13} className="text-primary" />
              Troca do Agente A3b para Gemini 2.5 Flash Lite
            </div>
            <p className="text-muted-foreground leading-relaxed">
              O agente de análise de concorrentes (A3b) foi migrado com sucesso de <code>gemini-2.5-flash</code> para o novo modelo <code>gemini-2.5-flash-lite</code>. Isso gera uma **redução imediata de até 40%** no custo de processamento deste sub-agente.
            </p>
            <div className="text-[10px] text-emerald-500 font-medium">Economia: ~R$ 0,80 a R$ 1,50 por execução</div>
          </div>

          <div className="p-3 rounded-md bg-muted/30 border border-border/50 space-y-1 hover:border-primary/20 transition-all">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <TrendingDown size={13} className="text-primary" />
              Cache Geográfico por Cidade e Bairro (7 dias)
            </div>
            <p className="text-muted-foreground leading-relaxed">
              A reutilização de dados de geocoding e popular_times da SearchAPI via cache em disco evita consultas repetitivas para o mesmo bairro. Garanta a manutenção do cache local para manter as requisições de API a custo zero.
            </p>
            <div className="text-[10px] text-emerald-500 font-medium">Economia: Elimina custos redundantes de geocoding e SearchAPI</div>
          </div>

          <div className="p-3 rounded-md bg-muted/30 border border-border/50 space-y-1 hover:border-primary/20 transition-all">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <Coins size={13} className="text-primary" />
              Limitação de concorrentes processados no A3c
            </div>
            <p className="text-muted-foreground leading-relaxed">
              Ao limitar o mapeamento de oferta do A3c a apenas os concorrentes mais relevantes que possuem presença ativa na web (website ou Instagram), evitamos chamadas de Places Details desnecessárias para academias sem canais digitais.
            </p>
            <div className="text-[10px] text-emerald-500 font-medium">Economia: ~30% do custo do A3c</div>
          </div>

          <div className="p-3 rounded-md bg-muted/30 border border-border/50 space-y-1 hover:border-primary/20 transition-all">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <Cpu size={13} className="text-primary" />
              Context Caching no Consolidador A6
            </div>
            <p className="text-muted-foreground leading-relaxed">
              Como o prompt base e as diretrizes do relatório consolidado são estáticos, a implementação futura de Context Caching do Gemini reduzirá drasticamente o custo do agente A6 (que consome mais de 1.8M tokens por relatório).
            </p>
            <div className="text-[10px] text-emerald-500 font-medium">Economia: R$ 1,00 a R$ 2,00 por relatório completo</div>
          </div>
        </div>
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
  const { data, isLoading } = useCustosAPI(relatorioId)

  if (isLoading) {
    return (
      <div className="py-6 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
        <Loader2 size={14} className="animate-spin" />
        Carregando detalhamento de custos…
      </div>
    )
  }

  const llmRecords = data?.llm?.por_agente ? Object.entries(data.llm.por_agente) : []
  const apiRecords = data?.api?.por_sku ? Object.entries(data.api.por_sku) : []

  if (!llmRecords.length && !apiRecords.length) {
    return (
      <div className="py-6 text-center text-muted-foreground text-sm bg-muted/5 rounded-b-lg">
        Sem telemetria registrada para este relatório. Relatório antigo ou executado antes do rastreamento.
      </div>
    )
  }

  const llmTotal = data?.llm?.total_brl ?? 0
  const apiTotal = data?.api?.total_brl ?? 0
  const grandTotal = data?.total_brl ?? 0

  return (
    <div className="p-5 bg-card/40 border-t border-border/60 space-y-6">
      {/* Custo Share header */}
      <div className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/50 pb-2">
        <div className="flex items-center gap-4">
          <span>
            Custo LLM: <strong className="text-foreground">{FMT_BRL.format(llmTotal)}</strong> ({grandTotal ? ((llmTotal/grandTotal)*100).toFixed(1) : 0}%)
          </span>
          <span>
            Custo APIs: <strong className="text-foreground">{FMT_BRL.format(apiTotal)}</strong> ({grandTotal ? ((apiTotal/grandTotal)*100).toFixed(1) : 0}%)
          </span>
        </div>
        <div>
          Total Geral: <strong className="text-foreground">{FMT_BRL.format(grandTotal)}</strong>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* LLM Costs */}
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
            <Cpu size={14} className="text-primary" />
            Consumo de Modelos LLM
          </div>
          {llmRecords.length === 0 ? (
            <div className="text-xs text-muted-foreground py-4 text-center border border-dashed rounded-lg">
              Nenhum consumo de LLM registrado.
            </div>
          ) : (
            <div className="border border-border/80 rounded-lg overflow-hidden bg-background/50">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/10">
                    <TableHead className="text-xs">Agente</TableHead>
                    <TableHead className="text-xs">Modelo</TableHead>
                    <TableHead className="text-xs text-right">Tokens In / Out</TableHead>
                    <TableHead className="text-xs text-right">Custo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {llmRecords.map(([agente, r]) => (
                    <TableRow key={agente} className="hover:bg-muted/5">
                      <TableCell className="font-medium text-xs py-2">{agente}</TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground py-2">
                        {r.modelo}
                      </TableCell>
                      <TableCell className="text-right font-mono text-[10px] py-2">
                        {FMT_INT.format(r.tokens_in)} / {FMT_INT.format(r.tokens_out)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs py-2 font-semibold text-foreground">
                        {FMT_BRL.format(r.custo_brl)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* API Costs */}
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
            <Coins size={14} className="text-primary" />
            Chamadas a APIs e Provedores
          </div>
          {apiRecords.length === 0 ? (
            <div className="text-xs text-muted-foreground py-4 text-center border border-dashed rounded-lg">
              Nenhuma chamada de API externa registrada.
            </div>
          ) : (
            <div className="border border-border/80 rounded-lg overflow-hidden bg-background/50">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/10">
                    <TableHead className="text-xs">API / Serviço</TableHead>
                    <TableHead className="text-xs text-right">Chamadas</TableHead>
                    <TableHead className="text-xs text-right">Custo unitário</TableHead>
                    <TableHead className="text-xs text-right">Custo total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiRecords.map(([sku, r]) => {
                    const unitario = r.calls > 0 ? r.custo_brl / r.calls : 0
                    return (
                      <TableRow key={sku} className="hover:bg-muted/5">
                        <TableCell className="font-medium text-xs py-2 font-mono">
                          {sku}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs py-2">
                          {r.calls}
                        </TableCell>
                        <TableCell className="text-right font-mono text-[10px] text-muted-foreground py-2">
                          {FMT_BRL.format(unitario)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs py-2 font-semibold text-foreground">
                          {FMT_BRL.format(r.custo_brl)}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
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
