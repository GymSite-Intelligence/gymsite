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
import type { CenarioJSON, CompetidorJSON, SensibilidadeStress } from '@/hooks/useRelatorioDetail'
import { formatBRL, formatInt, formatPct, INVIAVEL_PAYBACK_THRESHOLD } from '@/lib/format'

// ── Derivadas da folga de capacidade (12/06) ────────────────────────────
// Todas computadas dos campos já presentes no cenário; premissas iguais às
// do A4 (share de pico 0,25; freq fallback 2,0 = benchmark IHRSA/ACAD).

function _freq(c?: CenarioJSON): number {
  return c?.frequencia_semanal_aluno || 2.0
}

function _cap(c?: CenarioJSON): number | null {
  return c?.capacidade_simultanea_pico ?? c?.capacidade_maxima_alunos ?? null
}

function _share(c?: CenarioJSON): number {
  return c?.pico_share || 0.25
}

/** Teto de matrículas que o espaço atual suporta (pico = capacidade).
 *  Frame correto (12/06): o gargalo é PESSOAS NO PICO — converte capacidade
 *  em matrículas pelo fator de presença no pico derivado do próprio cenário
 *  (pico_calculado ÷ matrículas realista). Frequência média só entra como
 *  fallback quando o A4 não emitiu o pico. */
function tetoMatriculas(c?: CenarioJSON): number | null {
  const cap = _cap(c)
  if (!cap) return null
  const picoBase = c?.alunos_pico_calculado
  const matricBase = c?.matriculas?.realista?.valor ?? c?.alunos_projetados
  if (picoBase && matricBase) {
    return Math.floor(cap / (picoBase / matricBase))
  }
  return Math.floor((cap * 7) / (_freq(c) * _share(c)))
}

function matriculasRealista(c?: CenarioJSON): number | null {
  return c?.matriculas?.realista?.valor ?? c?.alunos_projetados ?? null
}

/** Concentração de pico medida nas curvas dos concorrentes: maior janela de
 *  2h consecutivas ÷ movimento total do dia, média entre concorrentes e dias
 *  úteis. Comparável ao share 0,25 assumido nos cenários (mesma semântica:
 *  fração do fluxo diário presente na janela de pico). */
function sharePicoMedido(competidores?: CompetidorJSON[] | null): {
  share: number
  nConcorrentes: number
} | null {
  const DIAS_UTEIS = ['segunda', 'terca', 'quarta', 'quinta', 'sexta']
  const shares: number[] = []
  let nComCurva = 0
  for (const comp of competidores ?? []) {
    const curvas = comp.horarios_pico as Record<string, Record<string, number>> | null | undefined
    if (!curvas) continue
    let usou = false
    for (const dia of DIAS_UTEIS) {
      const horas = curvas[dia]
      if (!horas) continue
      const valores = Object.keys(horas)
        .sort()
        .map((h) => Number(horas[h]) || 0)
      const total = valores.reduce((s, v) => s + v, 0)
      if (total <= 0) continue
      let melhorJanela = 0
      for (let i = 0; i < valores.length - 1; i++) {
        melhorJanela = Math.max(melhorJanela, valores[i] + valores[i + 1])
      }
      shares.push(melhorJanela / total)
      usou = true
    }
    if (usou) nComCurva++
  }
  if (!shares.length) return null
  return {
    share: shares.reduce((s, v) => s + v, 0) / shares.length,
    nConcorrentes: nComCurva,
  }
}

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
  /** Concorrentes do relatório — alimentam a concentração de pico MEDIDA do bairro. */
  competidores?: CompetidorJSON[] | null
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
function formatPaybackMeses(m: number | null | undefined): string {
  if (m == null || typeof m !== 'number' || !Number.isFinite(m)) return '—'
  if (m >= INVIAVEL_PAYBACK_THRESHOLD) return 'inviável'
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
  // P-004: linha sem dado em NENHUM modelo não renderiza (runs antigos sem
  // breakdown viravam 14 linhas de travessão). '—' em só alguns modelos fica.
  const rowsComDado = rows.filter((row) =>
    MODELOS.some((m) => row.values(cenarios[m]) !== '—'),
  )
  if (rowsComDado.length === 0) return null
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
            {rowsComDado.map((row, i) => (
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
  competidores,
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

  // Área de referência usada pelo A4 — derivada do próprio dado (realista ÷
  // densidade realista), exibida no header pra deixar explícito que as 3
  // colunas compartilham o MESMO espaço (a variável tamanho é o input do
  // relatório, não o modelo).
  const areaRefLabel = (() => {
    for (const m of MODELOS) {
      const r = cenarios[m]?.matriculas?.realista
      if (r?.valor && r?.matr_por_m2) {
        const area = Math.round(r.valor / r.matr_por_m2)
        return `área de referência ~${area.toLocaleString('pt-BR')} m²`
      }
    }
    return areaM2 ? `área-alvo ${areaM2.toLocaleString('pt-BR')} m²` : ''
  })()

  // ── (a) DEMANDA — só v2 ──
  // Matrículas = densidade ACAD/Sebrae 2024 (matr/m² por modelo e cenário)
  // × área de referência. A densidade vem no próprio dado do A4
  // (matriculas.X.matr_por_m2) e é exibida pra trilha de auditoria.
  const fmtMatriculas = (
    item?: { valor?: number | null; matr_por_m2?: number | null } | null,
    cenario?: CenarioJSON,
  ) => {
    if (item?.valor == null) return '—'
    // O banco só persiste matr_por_m2 do REALISTA; densidade dos outros
    // cenários é derivada por proporção exata (mesma área de referência):
    // dens_x = valor_x ÷ (valor_realista ÷ dens_realista).
    const realista = cenario?.matriculas?.realista
    let dens: number | null = null
    if (realista?.valor && realista?.matr_por_m2) {
      const areaRef = realista.valor / realista.matr_por_m2
      dens = Math.round((item.valor / areaRef) * 10) / 10
    }
    return (
      <>
        {formatInt(item.valor)}
        {dens != null && (
          <span className="ml-1 text-[10px] text-muted-foreground">
            ({String(dens).replace('.', ',')}/m²)
          </span>
        )}
      </>
    )
  }
  const rowsDemanda: SubTableRow[] = [
    {
      label: (
        <TooltipLabel help="Piso de captação: densidade conservadora ACAD/Sebrae 2024 (low 1,5 · mid 1,0 · premium 0,4 matrículas por m²) × área de referência. Cenário de praça difícil ou execução mediana — se a conta fecha aqui, o risco é baixo.">
          Matrículas conservador
        </TooltipLabel>
      ),
      values: (c) => fmtMatriculas(c?.matriculas?.conservador, c),
    },
    {
      label: (
        <TooltipLabel help="Base das projeções de receita: densidade realista ACAD/Sebrae 2024 (low 2,2 · mid 1,4 · premium 0,6 matr/m²) × área de referência. Benchmark NACIONAL — a calibração com a demanda local (Censo por setor censitário) entra na próxima versão do motor.">
          Matrículas realista (base)
        </TooltipLabel>
      ),
      values: (c) => fmtMatriculas(c?.matriculas?.realista, c),
      emphasize: true,
    },
    {
      label: (
        <TooltipLabel help="Teto de captação da indústria: densidade agressiva ACAD/Sebrae 2024 (low 3,0 · mid 1,8 · premium 0,9 matr/m²). Âncora de realidade: a Smart Fit (listada, CVM) opera em média ~2,5 mil matrículas por clube — o agressivo low-cost é território de rede com marca consolidada, não de estreante.">
          Matrículas agressivo
        </TooltipLabel>
      ),
      values: (c) => fmtMatriculas(c?.matriculas?.agressivo, c),
    },
    {
      label: (
        <TooltipLabel help="Pessoas treinando AO MESMO TEMPO que o espaço comporta com conforto — densidade de LAYOUT do benchmark ACAD por modelo (low 0,55 · mid 0,40 · premium 0,25 pessoas/m²) × a MESMA área-alvo. Varia entre colunas porque cada modelo ocupa o espaço diferente (low empilha equipamento; premium gasta m² com studio e circulação), não porque o imóvel muda.">
          Capacidade física simultânea
        </TooltipLabel>
      ),
      values: (c) => formatInt(c?.capacidade_simultanea_pico),
    },
    {
      label: (
        <TooltipLabel help="Máximo de matrículas que o MERCADO sustenta nesta área, pelo benchmark ACAD/Sebrae 2024 de matrículas por m² no cenário agressivo de cada modelo (low 3,0 · mid 1,8 · premium 0,9 matr/m²). É o teto de CAPTAÇÃO da indústria — diferente do teto físico do espaço, logo abaixo.">
          Teto de mercado (benchmark ACAD)
        </TooltipLabel>
      ),
      values: (c) => formatInt(c?.matriculas?.agressivo?.valor),
    },
    {
      label: 'Pico calculado (real × freq × 0,25)',
      values: (c) => formatInt(c?.alunos_pico_calculado),
    },
    {
      label: (
        <TooltipLabel help="Quanto da academia SOBRA no horário mais cheio. Fórmula: matrículas × freq./semana ÷ 7 dias × 25% (share do pico, benchmark setor) = pessoas simultâneas no pico; folga = 1 − pico/capacidade física. 40–70% é o sweet spot: abaixo, fila e churn; muito acima, aluguel pago por espaço ocioso. Veja o cruzamento com o pico REAL do bairro no quadro abaixo.">
          Folga capacidade
        </TooltipLabel>
      ),
      values: (c) => formatPct(c?.folga_capacidade_pct),
    },
    {
      label: (
        <TooltipLabel help="Frequência média de treino por aluno/semana. Quando o run não calculou, exibimos o benchmark do setor (IHRSA / ACAD Brasil: 2,0–2,5x) usado nas projeções de pico.">
          Freq. semanal aluno
        </TooltipLabel>
      ),
      values: (c) =>
        c?.frequencia_semanal_aluno
          ? `${c.frequencia_semanal_aluno}x`
          : '2,0–2,5x (benchmark setor)',
    },
    // ── Derivadas da folga (12/06) — crescimento, dinheiro e proteção ──
    {
      label: (
        <TooltipLabel help="GATE de dimensionamento expresso onde o gargalo acontece: PESSOAS SIMULTÂNEAS no pico, não matrículas. Pico do agressivo = matrículas agressivas × fator de presença no pico (pico÷base do próprio cenário A4, ~7% — a frequência é insumo dessa premissa, não a métrica da análise). Verde = capacidade comporta o pico do cenário máximo da indústria; vermelho = o prédio lota antes do mercado esgotar.">
          Pico no agressivo × capacidade
        </TooltipLabel>
      ),
      values: (c) => {
        const cap = _cap(c)
        const mercado = c?.matriculas?.agressivo?.valor
        const picoBase = c?.alunos_pico_calculado
        const matricBase = matriculasRealista(c)
        if (!cap || !mercado || !picoBase || !matricBase) return '—'
        // Fator de presença no pico derivado do próprio cenário (sem premissa nova)
        const presenca = picoBase / matricBase
        const picoAgressivo = Math.round(mercado * presenca)
        const ok = picoAgressivo <= cap
        const razao = cap / picoAgressivo
        return (
          <span className={ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-veredito-reprovado'}>
            {formatInt(picoAgressivo)} pessoas vs {formatInt(cap)} de capacidade{' '}
            {ok ? `(✓ ${razao.toFixed(1).replace('.', ',')}× de folga)` : '(✗ LOTA antes do mercado)'}
          </span>
        )
      },
      emphasize: true,
    },
    {
      label: (
        <TooltipLabel help="Receita mensal extra se a base crescer do realista até o teto de MERCADO (benchmark ACAD agressivo), ao ticket realizado. Upside captável com marketing, sem CAPEX — limitado pelo que a indústria comprovadamente capta, não pela fantasia do espaço vazio.">
          Receita destravável até o teto ACAD
        </TooltipLabel>
      ),
      values: (c) => {
        const tetoMercado = c?.matriculas?.agressivo?.valor
        const base = matriculasRealista(c)
        const ticket = c?.ticket_realizado_estimado ?? c?.ticket_medio
        if (tetoMercado == null || base == null || !ticket) return '—'
        const extra = Math.max(0, tetoMercado - base) * Number(ticket)
        return `+${formatBRL(extra)}/mês`
      },
    },
    {
      label: (
        <TooltipLabel help="Quantas matrículas a mais cabem antes da ocupação no PICO atingir 85% da capacidade — limiar onde nascem as reclamações de lotação (visto nos reviews dos concorrentes deste relatório). Conversão pelo fator de presença no pico do próprio cenário (~7% da base simultânea), mesmo frame do gate acima.">
          Colchão até reclamação (85%)
        </TooltipLabel>
      ),
      values: (c) => {
        const teto = tetoMatriculas(c)
        const base = matriculasRealista(c)
        if (teto == null || base == null) return '—'
        const colchao = Math.floor(teto * 0.85) - base
        return colchao >= 0 ? `+${formatInt(colchao)} matrículas` : (
          <span className="text-veredito-reprovado">acima do limiar</span>
        )
      },
    },
    {
      label: (
        <TooltipLabel help="Fração do teto de MERCADO (benchmark ACAD agressivo) necessária só pra pagar as contas. Quanto menor, mais defensável: sobra distância entre 'não perder dinheiro' e o máximo que a indústria capta. Acima de ~60% o modelo exige execução quase perfeita.">
          Break-even ÷ teto de mercado
        </TooltipLabel>
      ),
      values: (c) => {
        const tetoMercado = c?.matriculas?.agressivo?.valor
        const be = c?.alunos_break_even
        if (tetoMercado == null || be == null) return '—'
        const pct = (be / tetoMercado) * 100
        return (
          <span className={pct > 60 ? 'text-veredito-reprovado' : undefined}>
            {formatPct(pct)}
          </span>
        )
      },
    },
    {
      label: (
        <TooltipLabel help="Concentração de pico MEDIDA nas curvas de movimento dos concorrentes deste relatório (maior janela de 2h ÷ movimento do dia, média dos dias úteis). Compare com os 25% assumidos nos cenários: medição menor = premissa conservadora = folga real ainda maior.">
          Share de pico medido no bairro
        </TooltipLabel>
      ),
      values: () => {
        const medido = sharePicoMedido(competidores)
        if (!medido) return '—'
        return `${Math.round(medido.share * 100)}% (${medido.nConcorrentes} concorrentes) vs 25% assumido`
      },
    },
    {
      label: (
        <TooltipLabel help="Espaço físico por pessoa no horário de pico (70% da área útil destinada a treino ÷ pico simultâneo). Conforto de referência do setor: ≥ 4 m²/pessoa. Abaixo de 2,5 m² o treino vira fila.">
          m² por pessoa no pico
        </TooltipLabel>
      ),
      values: (c) => {
        const pico = c?.alunos_pico_calculado
        if (!areaM2 || !pico) return '—'
        const m2 = (areaM2 * 0.7) / pico
        const ok = m2 >= 4
        return (
          <span className={ok ? 'text-emerald-600 dark:text-emerald-400' : undefined}>
            {m2.toFixed(1).replace('.', ',')} m² {ok ? '(confortável)' : ''}
          </span>
        )
      },
    },
  ]

  // ── (b) RECEITA & CUSTOS ──
  const rowsCustos: SubTableRow[] = [
    {
      label: (
        <TooltipLabel help="Mensalidade de tabela por modelo. Referência ACAD/Sebrae 2024: low R$ 89,90 · mid R$ 149,90 · premium R$ 299,90 — quando o valor difere, o A4 ajustou ao mercado LOCAL. Confira contra os planos públicos dos concorrentes no quadro 'Planos e preços da concorrência' deste relatório.">
          Ticket nominal
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.ticket_medio),
    },
    {
      label: (
        <TooltipLabel help="Ticket que entra de fato no caixa: nominal × (1 − inadimplência). É a base da receita e do break-even.">
          Ticket realizado (pós-inadimpl.)
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.ticket_realizado_estimado),
    },
    {
      label: (
        <TooltipLabel help="% de matrículas que não pagam mensalidade. Referência ACAD por modelo: low 6% · mid 4% · premium 2,5% (débito recorrente). Sem recorrência (boleto/Pix manual) o setor vê 15-25%. Aplicada como redutor sobre o ticket nominal.">
          Inadimplência
        </TooltipLabel>
      ),
      values: (c) =>
        c?.taxa_inadimplencia != null ? `${(c.taxa_inadimplencia * 100).toFixed(1)}%` : '—',
    },
    {
      label: (
        <TooltipLabel help="Matrículas realista × ticket realizado — verificável nas duas linhas acima e no quadro Demanda.">
          Receita mensal
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.receita_mensal),
      emphasize: true,
    },
    {
      label: (
        <TooltipLabel help="Mesmo imóvel nas 3 colunas — por isso o valor é idêntico. Mediana de mercado pra faixa de área; veja a reconciliação com o preço do candidato real anunciado logo acima dos cenários.">
          Aluguel
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.aluguel),
    },
    {
      label: (
        <TooltipLabel help="Premissa: 15% do aluguel — padrão de imóvel comercial de grande porte.">
          Condomínio
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.condominio),
    },
    { label: 'IPTU', values: (c) => formatBRL(c?.custos_detalhados?.iptu) },
    {
      label: (
        <TooltipLabel help="Premium estima +50% de energia (climatização integral, sauna, equipamentos de recovery). Low e mid compartilham a base da faixa de área.">
          Energia
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.energia),
    },
    {
      label: (
        <TooltipLabel help="⚠️ Premissa FIXA nas 3 colunas — leitura conservadora pro premium e otimista pro low-cost (3-4× mais visitas = mais chuveiro). Refinamento previsto: escalar com visitas projetadas.">
          Água
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.agua),
    },
    { label: 'Internet', values: (c) => formatBRL(c?.custos_detalhados?.internet) },
    {
      label: (
        <TooltipLabel help="Escala com o modelo: low opera com equipe enxuta (recepção + instrutores mínimos); premium soma personal trainers, atendimento e operação de serviços (spa/recovery).">
          Folha de pagamento
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.folha),
    },
    {
      label: (
        <TooltipLabel help="0,5% ao mês do CAPEX do modelo — equipamento mais caro = manutenção proporcionalmente maior. Verificável: divida o valor por 0,005 e compare com o CAPEX no quadro Investimento.">
          Manutenção
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.manutencao),
    },
    { label: 'Contabilidade', values: (c) => formatBRL(c?.custos_detalhados?.contabilidade) },
    { label: 'Sistema de gestão', values: (c) => formatBRL(c?.custos_detalhados?.sistema_gestao) },
    {
      label: (
        <TooltipLabel help="0,2% ao mês do CAPEX do modelo — mesmo racional da manutenção, auditável contra o quadro Investimento.">
          Seguro
        </TooltipLabel>
      ),
      values: (c) => formatBRL(c?.custos_detalhados?.seguro),
    },
    { label: 'Outros (2% receita)', values: (c) => formatBRL(c?.custos_detalhados?.outros) },
    {
      label: 'Custos fixos total',
      values: (c) => formatBRL(c?.custos_fixos_total ?? c?.custos_fixos),
    },
    {
      label: (
        <TooltipLabel help="% da receita por modelo (low ~6% · mid ~8% · premium ~12%): premium investe proporcionalmente mais porque vende posicionamento e experiência, não preço — CAC maior por aluno, compensado pelo ticket.">
          Marketing
        </TooltipLabel>
      ),
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
        <TooltipLabel help="Lucro líquido ÷ receita bruta. Critério ACAD: 15-25% saudável (verde); abaixo de 10% modelo sob pressão (vermelho) — sem espaço pra imprevisto, churn acima do esperado já vira prejuízo.">
          Margem
        </TooltipLabel>
      ),
      values: (c) => {
        const m = c?.margem_percentual
        if (m == null) return '—'
        const cor =
          m < 10 ? 'text-veredito-reprovado font-semibold'
          : m >= 15 && m <= 25 ? 'text-emerald-600 dark:text-emerald-400'
          : undefined
        return <span className={cor}>{formatPct(m)}</span>
      },
    },
    {
      label: (
        <TooltipLabel help="Custos totais do cenário ÷ ticket realizado — alunos mínimos pra zerar o mês. Leitura CONSERVADORA: trata marketing e 'outros' (que são % da receita) como fixos; o break-even real é levemente menor. Compare com o teto de mercado no quadro Demanda: BE acima de 60% do teto = modelo exige execução quase perfeita.">
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
          description={
            `Mesma área-alvo nas 3 colunas${areaRefLabel ? ` (${areaRefLabel})` : ''} — ` +
            'Low/Mid/Premium não é só preço: é pacote operacional ACAD completo. ' +
            'Cada modelo usa o MESMO espaço com layout diferente (low 0,55 · mid 0,40 · ' +
            'premium 0,25 pessoas/m² no pico), daí capacidades distintas pra mesma metragem.'
          }
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
