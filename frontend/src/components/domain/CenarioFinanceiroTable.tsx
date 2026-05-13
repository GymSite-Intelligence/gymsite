/**
 * CenarioFinanceiroTable — schema v2 com 4 sub-tabelas.
 *
 * Antes: 1 tabela única com info insuficiente pro veredito.
 * Agora: Demanda + Receita/Custos detalhados + Investimento + Risco.
 *
 * Backward-compat: se receber JSON v1 (sem campos novos), sub-tabelas v2
 * ficam ocultas — só renderiza o que tem.
 */
import { Check, TrendingDown, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { CenarioJSON, SensibilidadeStress } from '@/hooks/useRelatorioDetail'

/**
 * TooltipLabel — texto com underline tracejado que abre tooltip ao hover.
 * Usado em métricas técnicas (Payback, TIR, VPL, Margem, Break-even) pra
 * glossário inline sem poluir o layout.
 */
function TooltipLabel({
  children,
  help,
}: {
  children: React.ReactNode
  help: string
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="underline decoration-dashed decoration-muted-foreground/40 underline-offset-4 cursor-help">
          {children}
        </span>
      </TooltipTrigger>
      <TooltipContent>{help}</TooltipContent>
    </Tooltip>
  )
}

export interface CenarioFinanceiroTableProps {
  cenarios: Record<'low' | 'mid' | 'premium', CenarioJSON> | undefined
  modeloRecomendado?: string | null
  /** Área alvo (m²) do imóvel — usada pra calcular densidade máxima teórica. */
  areaM2?: number | null
  className?: string
}

const MODELOS: ('low' | 'mid' | 'premium')[] = ['low', 'mid', 'premium']

const MODELO_LABELS: Record<'low' | 'mid' | 'premium', { nome: string; descricao: string }> = {
  low: { nome: 'Low Cost', descricao: 'Smart Fit, Bluefit, Selfit' },
  mid: { nome: 'Mid Market', descricao: 'Bodytech entry, regionais' },
  premium: { nome: 'Premium', descricao: 'Bodytech, Bio Ritmo, boutique' },
}

// Cores de viabilidade — usa tokens semânticos --status-* (UI Lote 1).
const VIABILIDADE_COLOR: Record<string, string> = {
  ALTO: 'bg-status-good text-white',
  MEDIO: 'bg-status-warning text-black',
  BAIXO: 'bg-status-investigate text-white',
  INVIAVEL: 'bg-status-critical text-white',
}

// ── Formatters ───────────────────────────────────────────────────────────
function formatBRL(v: number | null | undefined, opts?: { compact?: boolean }): string {
  if (v == null) return '—'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
    notation: opts?.compact ? 'compact' : 'standard',
  }).format(v)
}
function formatInt(v: number | null | undefined): string {
  if (v == null) return '—'
  return v.toLocaleString('pt-BR')
}
function formatPct(v: number | null | undefined): string {
  if (v == null) return '—'
  return `${v.toFixed(1)}%`
}
function formatPaybackMeses(m: number | null | undefined): string {
  if (m == null) return '—'
  if (m >= 999) return 'inviável'
  if (m >= 24) return `${(m / 12).toFixed(1)} anos (${m}m)`
  return `${m}m`
}

function isModeloRecomendado(m: string, rec?: string | null): boolean {
  if (!rec) return false
  const n = rec.toLowerCase().replace(/\s+/g, '')
  return (
    (m === 'low' && n.includes('low')) ||
    (m === 'mid' && (n.includes('mid') || n.includes('médio'))) ||
    (m === 'premium' && n.includes('premium'))
  )
}

// ── Sub-tabela genérica reutilizável ────────────────────────────────────
interface SubTableRow {
  /** Texto OU ReactNode (pode incluir TooltipLabel pra glossário). */
  label: React.ReactNode
  values: (cenario: CenarioJSON | undefined) => React.ReactNode
  emphasize?: boolean    // negrito + maior peso visual
  variant?: 'good-negative' | 'plain'  // good-negative: vermelho se < 0
}

function SubTable({
  title,
  emoji,
  rows,
  cenarios,
  modeloRecomendado,
  description,
}: {
  title: string
  emoji: string
  rows: SubTableRow[]
  cenarios: CenarioFinanceiroTableProps['cenarios']
  modeloRecomendado?: string | null
  description?: string
}) {
  if (!cenarios) return null
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <header className="px-4 py-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <span aria-hidden>{emoji}</span>
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        {description && (
          <p className="text-[10px] font-mono text-muted-foreground mt-1">{description}</p>
        )}
      </header>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
              <th className="text-left p-2 font-medium">Métrica</th>
              {MODELOS.map((m) => {
                const rec = isModeloRecomendado(m, modeloRecomendado)
                return (
                  <th
                    key={m}
                    className={cn(
                      'text-right p-2 min-w-[120px]',
                      rec && 'bg-primary/10',
                    )}
                  >
                    <div className="flex items-center justify-end gap-1.5">
                      {rec && (
                        <span className="inline-flex items-center gap-0.5 px-1 py-0 rounded text-[9px] bg-primary text-primary-foreground font-bold">
                          <Check size={9} /> REC
                        </span>
                      )}
                      <span className="font-semibold">{MODELO_LABELS[m].nome}</span>
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className={cn(
                  'border-b border-border last:border-b-0 hover:bg-muted/20',
                  row.emphasize && 'bg-muted/10',
                )}
              >
                <td
                  className={cn(
                    'p-2 text-xs text-muted-foreground',
                    row.emphasize && 'font-semibold text-foreground',
                  )}
                >
                  {row.label}
                </td>
                {MODELOS.map((m) => {
                  const rec = isModeloRecomendado(m, modeloRecomendado)
                  const value = row.values(cenarios[m])
                  const isNum = typeof value === 'number'
                  const isNeg = isNum && (value as number) < 0
                  return (
                    <td
                      key={m}
                      className={cn(
                        'p-2 text-right font-mono tabular-nums text-sm',
                        rec && 'bg-primary/5',
                        row.emphasize && 'font-semibold',
                        row.variant === 'good-negative' && isNeg && 'text-veredito-reprovado',
                      )}
                    >
                      {value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Componente principal ────────────────────────────────────────────────
export function CenarioFinanceiroTable({
  cenarios,
  modeloRecomendado,
  areaM2,
  className,
}: CenarioFinanceiroTableProps) {
  if (!cenarios) {
    return (
      <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Cenários financeiros indisponíveis para este relatório.
      </div>
    )
  }

  // Detecta se é schema v2 (tem matriculas em pelo menos 1 cenário)
  const isV2 = MODELOS.some((m) => cenarios[m]?.matriculas != null)

  // ── (a) DEMANDA — só v2 ──
  const rowsDemanda: SubTableRow[] = [
    {
      label: 'Matrículas conservador',
      values: (c) => formatInt(c?.matriculas?.conservador.valor),
    },
    {
      label: 'Matrículas realista (base)',
      values: (c) => formatInt(c?.matriculas?.realista.valor),
      emphasize: true,
    },
    {
      label: 'Matrículas agressivo',
      values: (c) => formatInt(c?.matriculas?.agressivo.valor),
    },
    {
      label: 'Capacidade física simultânea',
      values: (c) => formatInt(c?.capacidade_simultanea_pico),
    },
    {
      label: (
        <TooltipLabel help="Densidade máxima teórica considerando 3 pessoas por m² — referência de ocupação extrema (auditório/show). Academias operam muito abaixo disso por causa de equipamentos e zonas de circulação. Use como teto absoluto.">
          Densidade máxima (3/m²)
        </TooltipLabel>
      ),
      // Independente do cenário — depende só da área. Mesmo valor em todas as colunas.
      values: () => (areaM2 ? formatInt(Math.floor(areaM2 * 3)) : '—'),
    },
    {
      label: 'Pico calculado (real × freq × 0,25)',
      values: (c) => formatInt(c?.alunos_pico_calculado),
    },
    {
      label: (
        <TooltipLabel help="Diferença entre capacidade física máxima e pico calculado. Alta folga = espaço pra crescer matrículas; folga negativa = pico simultâneo já excede conforto, risco de churn.">
          Folga capacidade
        </TooltipLabel>
      ),
      values: (c) => formatPct(c?.folga_capacidade_pct),
    },
    {
      label: 'Freq. semanal aluno',
      values: (c) => (c?.frequencia_semanal_aluno ? `${c.frequencia_semanal_aluno}x` : '—'),
    },
  ]

  // ── (b) RECEITA & CUSTOS ──
  const rowsCustos: SubTableRow[] = [
    { label: 'Ticket nominal', values: (c) => formatBRL(c?.ticket_medio) },
    {
      label: 'Ticket realizado (pós-inadimpl.)',
      values: (c) => formatBRL(c?.ticket_realizado_estimado),
    },
    {
      label: (
        <TooltipLabel help="% de matrículas que não pagam mensalidade. Panorama Setorial Fitness Brasil 2025: com débito recorrente ~4-8% (varia por modelo); sem recorrência (boleto/Pix manual) chega a 15-25%. Aplicada como redutor sobre ticket nominal pra estimar receita realizada.">
          Inadimplência
        </TooltipLabel>
      ),
      values: (c) =>
        c?.taxa_inadimplencia != null ? `${(c.taxa_inadimplencia * 100).toFixed(1)}%` : '—',
    },
    {
      label: 'Receita mensal',
      values: (c) => formatBRL(c?.receita_mensal),
      emphasize: true,
    },
    { label: 'Aluguel', values: (c) => formatBRL(c?.custos_detalhados?.aluguel) },
    { label: 'Condomínio', values: (c) => formatBRL(c?.custos_detalhados?.condominio) },
    { label: 'IPTU', values: (c) => formatBRL(c?.custos_detalhados?.iptu) },
    { label: 'Energia', values: (c) => formatBRL(c?.custos_detalhados?.energia) },
    { label: 'Água', values: (c) => formatBRL(c?.custos_detalhados?.agua) },
    { label: 'Internet', values: (c) => formatBRL(c?.custos_detalhados?.internet) },
    { label: 'Folha de pagamento', values: (c) => formatBRL(c?.custos_detalhados?.folha) },
    { label: 'Manutenção', values: (c) => formatBRL(c?.custos_detalhados?.manutencao) },
    { label: 'Contabilidade', values: (c) => formatBRL(c?.custos_detalhados?.contabilidade) },
    { label: 'Sistema de gestão', values: (c) => formatBRL(c?.custos_detalhados?.sistema_gestao) },
    { label: 'Seguro', values: (c) => formatBRL(c?.custos_detalhados?.seguro) },
    { label: 'Outros (2% receita)', values: (c) => formatBRL(c?.custos_detalhados?.outros) },
    {
      label: 'Custos fixos total',
      values: (c) => formatBRL(c?.custos_fixos_total ?? c?.custos_fixos),
    },
    {
      label: `Marketing`,
      values: (c) => {
        const m = c?.marketing_mensal
        const pct = c?.marketing_pct_faturamento
        if (m == null) return '—'
        return pct != null ? `${formatBRL(m)} (${(pct * 100).toFixed(0)}%)` : formatBRL(m)
      },
    },
    {
      label: 'Custos totais',
      values: (c) => formatBRL(c?.custos_totais),
      emphasize: true,
    },
    {
      label: 'Lucro mensal',
      values: (c) => {
        const v = c?.lucro_mensal_estimado
        if (v == null) return '—'
        return (
          <span className={v < 0 ? 'text-status-critical font-semibold' : 'text-status-good font-semibold'}>
            {formatBRL(v)}
          </span>
        )
      },
      emphasize: true,
    },
    {
      label: (
        <TooltipLabel help="Lucro líquido ÷ receita bruta. Saudável: 15-25%. Abaixo de 10% indica modelo sob pressão.">
          Margem
        </TooltipLabel>
      ),
      values: (c) => formatPct(c?.margem_percentual),
    },
    {
      label: (
        <TooltipLabel help="Quantidade mínima de alunos pagantes pra cobrir todos os custos fixos + variáveis. Acima disso, qualquer matrícula extra é lucro.">
          Break-even (alunos)
        </TooltipLabel>
      ),
      values: (c) => formatInt(c?.alunos_break_even),
    },
  ]

  // ── (c) INVESTIMENTO ──
  const rowsInvestimento: SubTableRow[] = [
    { label: 'Equipamentos', values: (c) => formatBRL(c?.capex_detalhado?.equipamentos) },
    { label: 'Obra de adaptação', values: (c) => formatBRL(c?.capex_detalhado?.obra_adaptacao) },
    { label: 'Projeto arquitetônico', values: (c) => formatBRL(c?.capex_detalhado?.projeto_arquitetonico) },
    { label: 'Alvará e taxas', values: (c) => formatBRL(c?.capex_detalhado?.alvara_e_taxas) },
    {
      label: 'Frete equipamentos (ANTT)',
      values: (c) => formatBRL(c?.capex_detalhado?.frete_equipamentos),
    },
    { label: 'Contingência (10%)', values: (c) => formatBRL(c?.capex_detalhado?.contingencia_valor) },
    {
      label: 'CAPEX total',
      values: (c) => formatBRL(c?.capex_total ?? c?.capex_estimado),
      emphasize: true,
    },
    {
      label: `Capital de giro (${cenarios.low?.capital_giro_meses ?? 3} meses)`,
      values: (c) => formatBRL(c?.capital_giro),
    },
    {
      label: 'Investimento total',
      values: (c) => formatBRL(c?.investimento_total),
      emphasize: true,
    },
    {
      label: (
        <TooltipLabel help="Tempo (meses) pra recuperar o investimento total via lucro mensal. Ideal: 24-36m. Acima de 60m sinaliza modelo arriscado pro setor fitness.">
          Payback
        </TooltipLabel>
      ),
      values: (c) => formatPaybackMeses(c?.payback_meses),
      emphasize: true,
    },
    {
      label: (
        <TooltipLabel help="Taxa Interna de Retorno anualizada. Compare com custo de capital (12% a.a. no modelo). TIR > 25%: muito atrativo. TIR < 12%: pior que aplicar em renda fixa.">
          TIR anual
        </TooltipLabel>
      ),
      values: (c) => (c?.tir_anual_pct != null ? `${c.tir_anual_pct.toFixed(1)}%` : '—'),
    },
    {
      label: (
        <TooltipLabel help="Valor Presente Líquido em 5 anos descontado a 12% a.a. VPL positivo = projeto gera valor acima do custo de capital. VPL negativo = melhor não investir.">
          VPL 5 anos @12% a.a.
        </TooltipLabel>
      ),
      values: (c) => {
        const v = c?.vpl_5_anos
        if (v == null) return '—'
        return (
          <span className={v < 0 ? 'text-status-critical font-semibold' : ''}>
            {formatBRL(v)}
          </span>
        )
      },
    },
  ]

  return (
    <div className={cn('space-y-4', className)}>
      {/* a) Demanda — só renderiza se v2 */}
      {isV2 && (
        <SubTable
          title="Demanda — Matrículas vs. Capacidade Física"
          emoji="📊"
          description="Matrículas em 3 calibrações (ACAD/Smart Fit/Bodytech). Pico simultâneo = capacidade física no horário cheio."
          rows={rowsDemanda}
          cenarios={cenarios}
          modeloRecomendado={modeloRecomendado}
        />
      )}

      {/* b) Receita & Custos */}
      <SubTable
        title="Receita & Custos Mensais"
        emoji="💵"
        description="Custos detalhados em 12 linhas. Receita usa matrículas realista × ticket realizado (após inadimplência)."
        rows={rowsCustos}
        cenarios={cenarios}
        modeloRecomendado={modeloRecomendado}
      />

      {/* c) Investimento */}
      <SubTable
        title="Investimento & Retorno"
        emoji="🏗️"
        description="CAPEX detalhado + capital de giro + payback/TIR/VPL pra decisão de investimento."
        rows={rowsInvestimento}
        cenarios={cenarios}
        modeloRecomendado={modeloRecomendado}
      />

      {/* d) Sensibilidade — só renderiza se algum cenário tem stress tests */}
      {isV2 && cenarios.low?.sensibilidade && (
        <SensibilidadeTable cenarios={cenarios} modeloRecomendado={modeloRecomendado} />
      )}

      {/* Veredito + justificativa final por cenário */}
      <div className="rounded-lg border border-border bg-card p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
        {MODELOS.map((m) => {
          const c = cenarios[m]
          if (!c) return null
          const rec = isModeloRecomendado(m, modeloRecomendado)
          return (
            <div
              key={m}
              className={cn(
                'rounded-md border border-border p-3 space-y-2',
                rec && 'ring-2 ring-primary/40',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold">{MODELO_LABELS[m].nome}</span>
                <span
                  className={cn(
                    'px-2 py-0.5 rounded text-[10px] font-semibold',
                    VIABILIDADE_COLOR[c.viabilidade] ?? 'bg-muted',
                  )}
                >
                  {c.viabilidade}
                </span>
              </div>
              {c.justificativa && (
                <p className="text-xs text-muted-foreground leading-snug">
                  {c.justificativa}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── (d) SENSIBILIDADE — formato diferente: stress × modelo ────────────
function SensibilidadeTable({
  cenarios,
  modeloRecomendado,
}: {
  cenarios: NonNullable<CenarioFinanceiroTableProps['cenarios']>
  modeloRecomendado?: string | null
}) {
  // Coleta stress tests do primeiro cenário que tiver
  const stressIds: SensibilidadeStress['id'][] = [
    'aluguel_mais_20pct',
    'matriculas_menos_30pct',
    'ticket_menos_15pct',
  ]

  function findStress(c: CenarioJSON | undefined, id: SensibilidadeStress['id']) {
    return c?.sensibilidade?.find((s) => s.id === id)
  }

  const stressLabels: Record<SensibilidadeStress['id'], { label: string; Icon: typeof TrendingDown }> = {
    aluguel_mais_20pct: { label: 'Aluguel +20%', Icon: TrendingDown },
    matriculas_menos_30pct: { label: 'Matrículas −30%', Icon: AlertTriangle },
    ticket_menos_15pct: { label: 'Ticket −15%', Icon: TrendingDown },
  }

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <header className="px-4 py-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <span aria-hidden>⚠️</span>
          <h3 className="text-sm font-semibold">Sensibilidade — 3 Stress Tests</h3>
        </div>
        <p className="text-[10px] font-mono text-muted-foreground mt-1">
          E se condições piorarem? Lucro, payback e viabilidade resultantes pra cada modelo.
        </p>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
              <th className="text-left p-2 font-medium">Stress test</th>
              {MODELOS.map((m) => {
                const rec = isModeloRecomendado(m, modeloRecomendado)
                return (
                  <th
                    key={m}
                    className={cn(
                      'text-right p-2 min-w-[150px]',
                      rec &&
                        'bg-status-good/10 border-l-2 border-status-good text-status-good',
                    )}
                  >
                    <span className="font-semibold inline-flex items-center gap-1.5">
                      {MODELO_LABELS[m].nome}
                      {rec && (
                        <span className="px-1 py-0 rounded text-[8px] bg-status-good text-white font-bold">
                          REC
                        </span>
                      )}
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {stressIds.map((sid) => {
              const cfg = stressLabels[sid]
              return (
                <tr key={sid} className="border-b border-border last:border-b-0 hover:bg-muted/20">
                  <td className="p-2 text-xs">
                    <div className="flex items-center gap-1.5">
                      <cfg.Icon size={11} className="text-muted-foreground" />
                      <span className="font-medium">{cfg.label}</span>
                    </div>
                  </td>
                  {MODELOS.map((m) => {
                    const s = findStress(cenarios[m], sid)
                    const rec = isModeloRecomendado(m, modeloRecomendado)
                    return (
                      <td
                        key={m}
                        className={cn(
                          'p-2 text-right text-xs font-mono',
                          rec && 'bg-status-good/5 border-l-2 border-status-good/30',
                        )}
                      >
                        {s ? (
                          <div className="flex flex-col items-end gap-0.5">
                            <span
                              className={cn(
                                'inline-block px-1.5 py-0 rounded text-[9px] font-semibold',
                                VIABILIDADE_COLOR[s.viabilidade],
                              )}
                            >
                              {s.viabilidade}
                            </span>
                            <span
                              className={cn(
                                'tabular-nums',
                                s.lucro_mensal < 0 && 'text-status-critical font-semibold',
                              )}
                            >
                              {formatBRL(s.lucro_mensal)}
                            </span>
                            <span className="text-muted-foreground text-[10px]">
                              payback {formatPaybackMeses(s.payback_meses)}
                            </span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
