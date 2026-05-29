/**
 * ResumoViabilidadeComparativa — narrativa executiva de viabilidade comparativa.
 *
 * Tom: direto, decisório, C-level. Sem jargão técnico de engenharia.
 * Fontes: sempre genéricas ("dados públicos", "benchmark do setor", "pesquisa de mercado").
 */
import {
  TrendingUp,
  TrendingDown,
  Equal,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Wallet,
  Target,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'

interface ResumoViabilidadeComparativaProps {
  bairroA: string
  bairroB: string
  cenarioA?: CenarioJSON
  cenarioB?: CenarioJSON
  aluguelA?: number | null
  aluguelB?: number | null
}

function fmtBRL(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(v)
}

function fmtPct(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return `${v.toFixed(1)}%`
}

function deltaPct(a: number | null | undefined, b: number | null | undefined): number | null {
  if (a == null || b == null || !Number.isFinite(a) || !Number.isFinite(b) || a === 0) return null
  return ((b - a) / Math.abs(a)) * 100
}

type Favor = 'A' | 'B' | 'neutro'

interface Driver {
  label: string
  valorA: string
  valorB: string
  diffPct: number | null
  favoravel: Favor
  peso: number
  categoria: 'receita' | 'custo' | 'retorno' | 'operacional'
  metodologia: string
}

export function ResumoViabilidadeComparativa({
  bairroA,
  bairroB,
  cenarioA,
  cenarioB,
  aluguelA,
  aluguelB,
}: ResumoViabilidadeComparativaProps) {
  if (!cenarioA || !cenarioB) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Dados financeiros insuficientes para gerar o resumo executivo de viabilidade.
        </CardContent>
      </Card>
    )
  }

  // ── Computa todos os drivers ──
  const drivers: Driver[] = []

  // Receita
  const diffReceita = deltaPct(cenarioA.receita_mensal, cenarioB.receita_mensal)
  if (diffReceita != null) {
    drivers.push({
      label: 'Receita mensal projetada',
      valorA: fmtBRL(cenarioA.receita_mensal),
      valorB: fmtBRL(cenarioB.receita_mensal),
      diffPct: diffReceita,
      favoravel: diffReceita > 5 ? 'B' : diffReceita < -5 ? 'A' : 'neutro',
      peso: Math.abs(diffReceita),
      categoria: 'receita',
      metodologia:
        'Baseada em ticket médio estimado, matrículas projetadas e frequência de visita — calibrada com benchmark do setor fitness para o perfil demográfico do bairro.',
    })
  }

  // Ticket médio
  const diffTicket = deltaPct(cenarioA.ticket_medio, cenarioB.ticket_medio)
  if (diffTicket != null) {
    drivers.push({
      label: 'Ticket médio mensal',
      valorA: fmtBRL(cenarioA.ticket_medio),
      valorB: fmtBRL(cenarioB.ticket_medio),
      diffPct: diffTicket,
      favoravel: diffTicket > 5 ? 'B' : diffTicket < -5 ? 'A' : 'neutro',
      peso: Math.abs(diffTicket) * 0.7,
      categoria: 'receita',
      metodologia:
        'Estimativa a partir da renda média do bairro, concorrência local e posicionamento de mercado — referência em pesquisa de preços praticados na região.',
    })
  }

  // Matrículas
  const matrA = cenarioA.matriculas?.realista?.valor ?? cenarioA.alunos_projetados ?? 0
  const matrB = cenarioB.matriculas?.realista?.valor ?? cenarioB.alunos_projetados ?? 0
  const diffMatr = deltaPct(matrA, matrB)
  if (diffMatr != null) {
    drivers.push({
      label: 'Matrículas projetadas (cenário realista)',
      valorA: String(Math.round(matrA)),
      valorB: String(Math.round(matrB)),
      diffPct: diffMatr,
      favoravel: diffMatr > 10 ? 'B' : diffMatr < -10 ? 'A' : 'neutro',
      peso: Math.abs(diffMatr) * 0.8,
      categoria: 'operacional',
      metodologia:
        'Projeção de demanda baseada em densidade populacional, renda e comportamento de consumo do público-alvo — validada com benchmark de ocupação de academias comparáveis.',
    })
  }

  // Aluguel / Custos fixos
  const aluguelAeff = aluguelA ?? cenarioA.custos_detalhados?.aluguel ?? cenarioA.custos_fixos_total
  const aluguelBeff = aluguelB ?? cenarioB.custos_detalhados?.aluguel ?? cenarioB.custos_fixos_total
  const diffAluguel = deltaPct(aluguelAeff, aluguelBeff)
  if (diffAluguel != null) {
    drivers.push({
      label: 'Aluguel e custos fixos mensais',
      valorA: fmtBRL(aluguelAeff),
      valorB: fmtBRL(aluguelBeff),
      diffPct: diffAluguel,
      favoravel: diffAluguel < -10 ? 'B' : diffAluguel > 10 ? 'A' : 'neutro',
      peso: Math.abs(diffAluguel) * 0.9,
      categoria: 'custo',
      metodologia:
        'Estimativa de custo operacional fixo a partir de dados de mercado imobiliário local e benchmark de condomínio/IPTU para o porte da unidade.',
    })
  }

  // Lucro
  const diffLucro = deltaPct(cenarioA.lucro_mensal_estimado, cenarioB.lucro_mensal_estimado)
  if (diffLucro != null) {
    drivers.push({
      label: 'Lucro mensal estimado',
      valorA: fmtBRL(cenarioA.lucro_mensal_estimado),
      valorB: fmtBRL(cenarioB.lucro_mensal_estimado),
      diffPct: diffLucro,
      favoravel: diffLucro > 10 ? 'B' : diffLucro < -10 ? 'A' : 'neutro',
      peso: Math.abs(diffLucro) * 1.3,
      categoria: 'retorno',
      metodologia:
        'Receita mensal projetada menos custos totais (fixos + variáveis + marketing) — cenário realista de ocupação.',
    })
  }

  // Margem
  const diffMargem = deltaPct(cenarioA.margem_percentual, cenarioB.margem_percentual)
  if (diffMargem != null) {
    drivers.push({
      label: 'Margem líquida operacional',
      valorA: fmtPct(cenarioA.margem_percentual),
      valorB: fmtPct(cenarioB.margem_percentual),
      diffPct: diffMargem,
      favoravel: diffMargem > 5 ? 'B' : diffMargem < -5 ? 'A' : 'neutro',
      peso: Math.abs(diffMargem),
      categoria: 'retorno',
      metodologia:
        'Lucro mensal dividido pela receita bruta — indicador de eficiência operacional e saúde do modelo de negócio.',
    })
  }

  // Payback
  const paybackA = cenarioA.payback_meses
  const paybackB = cenarioB.payback_meses
  let diffPaybackPct: number | null = null
  let favoravelPayback: Favor = 'neutro'
  if (paybackA != null && paybackB != null && paybackA > 0 && paybackB > 0) {
    diffPaybackPct = ((paybackB - paybackA) / paybackA) * 100
    favoravelPayback = diffPaybackPct < -15 ? 'B' : diffPaybackPct > 15 ? 'A' : 'neutro'
  }
  if (diffPaybackPct != null) {
    drivers.push({
      label: 'Payback do investimento',
      valorA: `${paybackA} meses`,
      valorB: `${paybackB} meses`,
      diffPct: diffPaybackPct,
      favoravel: favoravelPayback,
      peso: Math.min(Math.abs(diffPaybackPct), 60),
      categoria: 'retorno',
      metodologia:
        'Tempo estimado para recuperação do capital investido (CAPEX + giro) a partir do fluxo de caixa mensal projetado.',
    })
  }

  // TIR
  const diffTir = deltaPct(cenarioA.tir_anual_pct, cenarioB.tir_anual_pct)
  if (diffTir != null) {
    drivers.push({
      label: 'TIR anual estimada',
      valorA: fmtPct(cenarioA.tir_anual_pct),
      valorB: fmtPct(cenarioB.tir_anual_pct),
      diffPct: diffTir,
      favoravel: diffTir > 10 ? 'B' : diffTir < -10 ? 'A' : 'neutro',
      peso: Math.abs(diffTir) * 1.1,
      categoria: 'retorno',
      metodologia:
        'Taxa interna de retorno do projeto em 5 anos — considerando crescimento conservador de matrículas e inflação de custos.',
    })
  }

  // VPL
  const diffVpl = deltaPct(cenarioA.vpl_5_anos, cenarioB.vpl_5_anos)
  if (diffVpl != null) {
    drivers.push({
      label: 'VPL acumulado (5 anos)',
      valorA: fmtBRL(cenarioA.vpl_5_anos),
      valorB: fmtBRL(cenarioB.vpl_5_anos),
      diffPct: diffVpl,
      favoravel: diffVpl > 10 ? 'B' : diffVpl < -10 ? 'A' : 'neutro',
      peso: Math.abs(diffVpl) * 1.2,
      categoria: 'retorno',
      metodologia:
        'Valor presente líquido dos fluxos de caixa futuros — descontado pela taxa mínima de atratividade do setor.',
    })
  }

  // CAPEX
  const capexA = cenarioA.investimento_total ?? cenarioA.capex_total ?? cenarioA.capex_estimado
  const capexB = cenarioB.investimento_total ?? cenarioB.capex_total ?? cenarioB.capex_estimado
  const diffCapex = deltaPct(capexA, capexB)
  if (diffCapex != null) {
    drivers.push({
      label: 'Investimento inicial total',
      valorA: fmtBRL(capexA),
      valorB: fmtBRL(capexB),
      diffPct: diffCapex,
      favoravel: diffCapex < -10 ? 'B' : diffCapex > 10 ? 'A' : 'neutro',
      peso: Math.abs(diffCapex) * 0.8,
      categoria: 'custo',
      metodologia:
        'Soma de equipamentos, obra de adaptação, projeto, alvarás, frete e capital de giro — orçamento referenciado em fornecedores do setor.',
    })
  }

  // Ordena por impacto
  const driversSorted = drivers.sort((a, b) => b.peso - a.peso)
  const topDrivers = driversSorted.slice(0, 6)

  // ── Decide vencedor ──
  const pontosA = drivers.filter((d) => d.favoravel === 'A').reduce((s, d) => s + d.peso, 0)
  const pontosB = drivers.filter((d) => d.favoravel === 'B').reduce((s, d) => s + d.peso, 0)
  const vencedor: Favor =
    pontosB > pontosA * 1.2 ? 'B' : pontosA > pontosB * 1.2 ? 'A' : 'neutro'

  const mesmosModelos = cenarioA.modelo === cenarioB.modelo
  const modeloStr = cenarioA.modelo ?? 'N/A'

  return (
    <section className="rounded-lg border border-border overflow-hidden">
      <header className="px-5 py-3 bg-muted/30 border-b border-border">
        <h3 className="text-sm font-semibold">Parecer executivo de viabilidade</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Análise comparativa dos drivers financeiros e operacionais · baseada em dados de mercado
        </p>
      </header>

      <div className="p-5 space-y-6">
        {/* Recomendação */}
        <RecomendacaoCard
          vencedor={vencedor}
          bairroA={bairroA}
          bairroB={bairroB}
          mesmosModelos={mesmosModelos}
          modelo={modeloStr}
          cenarioA={cenarioA}
          cenarioB={cenarioB}
        />

        {/* Drivers principais */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <BarChart3 size={14} className="text-muted-foreground" />
            <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              Drivers que mais impactam a decisão
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {topDrivers.map((d) => (
              <DriverCard key={d.label} driver={d} />
            ))}
          </div>
        </div>

        {/* Narrativa executiva */}
        <div className="rounded-lg bg-muted/30 border border-border p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Target size={14} className="text-muted-foreground" />
            <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              Narrativa decisória
            </p>
          </div>
          <NarrativaExecutiva
            drivers={driversSorted}
            bairroA={bairroA}
            bairroB={bairroB}
            vencedor={vencedor}
            mesmosModelos={mesmosModelos}
            modelo={modeloStr}
          />
        </div>

        {/* Metodologia resumida */}
        <div className="rounded-lg border border-border p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Wallet size={14} className="text-muted-foreground" />
            <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
              Base de análise
            </p>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Todos os indicadores financeiros são projetados a partir de dados públicos de
            demografia, pesquisa de mercado local e benchmark operacional do setor fitness.
            Os cenários consideram ocupação realista, sazonalidade de matrículas e inflação
            de custos. Não constituem garantia de performance, mas sim referência para
            tomada de decisão estratégica.
          </p>
        </div>

        {/* Alerta de modelo diferente */}
        {!mesmosModelos && (
          <div className="flex items-start gap-2.5 text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-md px-4 py-3">
            <AlertTriangle size={14} className="shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-xs font-semibold">Modelos de negócio distintos</p>
              <p className="text-xs leading-relaxed">
                {bairroA} foi dimensionado no modelo <strong>{cenarioA.modelo}</strong>,
                enquanto {bairroB} aponta para <strong>{cenarioB.modelo}</strong>.
                Isso afeta diretamente o ticket médio, o CAPEX e a capacidade da unidade.
                Recomendamos priorizar o <strong>payback</strong> e a{' '}
                <strong>TIR</strong> como métricas normalizadas, já que comparam retorno
                independentemente do porte do investimento.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

// ── Subcomponentes ──

function RecomendacaoCard({
  vencedor,
  bairroA,
  bairroB,
  mesmosModelos,
  modelo,
  cenarioA,
  cenarioB,
}: {
  vencedor: Favor
  bairroA: string
  bairroB: string
  mesmosModelos: boolean
  modelo: string
  cenarioA: CenarioJSON
  cenarioB: CenarioJSON
}) {
  const lucroA = cenarioA.lucro_mensal_estimado
  const lucroB = cenarioB.lucro_mensal_estimado
  const payA = cenarioA.payback_meses
  const payB = cenarioB.payback_meses

  if (vencedor === 'B') {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-900 p-4">
        <CheckCircle size={18} className="text-emerald-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-300">
            Recomendamos {bairroB}
          </p>
          <p className="text-xs text-emerald-800 dark:text-emerald-400 leading-relaxed">
            {mesmosModelos
              ? `Ambos os pontos operam no mesmo modelo (${modelo}), mas ${bairroB} entrega melhor relação risco/retorno.`
              : `${bairroB} foi dimensionado no modelo ${cenarioB.modelo}, que se ajusta melhor ao perfil de demanda local.`}{' '}
            {lucroB != null && lucroA != null && lucroB > lucroA
              ? `O lucro mensal projetado é ${fmtBRL(lucroB)} vs ${fmtBRL(lucroA)} em ${bairroA}.`
              : ''}{' '}
            {payB != null && payA != null && payB < payA
              ? `O payback é ${payB} meses, ${payA - payB} meses mais rápido que ${bairroA}.`
              : ''}
          </p>
        </div>
      </div>
    )
  }

  if (vencedor === 'A') {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-900 p-4">
        <CheckCircle size={18} className="text-emerald-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-300">
            Recomendamos {bairroA}
          </p>
          <p className="text-xs text-emerald-800 dark:text-emerald-400 leading-relaxed">
            {mesmosModelos
              ? `Ambos os pontos operam no mesmo modelo (${modelo}), mas ${bairroA} entrega melhor relação risco/retorno.`
              : `${bairroA} foi dimensionado no modelo ${cenarioA.modelo}, que se ajusta melhor ao perfil de demanda local.`}{' '}
            {lucroA != null && lucroB != null && lucroA > lucroB
              ? `O lucro mensal projetado é ${fmtBRL(lucroA)} vs ${fmtBRL(lucroB)} em ${bairroB}.`
              : ''}{' '}
            {payA != null && payB != null && payA < payB
              ? `O payback é ${payA} meses, ${payB - payA} meses mais rápido que ${bairroB}.`
              : ''}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 rounded-lg border border-sky-200 bg-sky-50 dark:bg-sky-950/20 dark:border-sky-900 p-4">
      <Equal size={18} className="text-sky-600 shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-sky-900 dark:text-sky-300">
          Viabilidade financeira equilibrada
        </p>
        <p className="text-xs text-sky-800 dark:text-sky-400 leading-relaxed">
          {mesmosModelos
            ? `Os dois pontos apresentam retorno financeiro próximo no modelo ${modelo}.`
            : `Modelos distintos compensam-se financeiramente.`}{' '}
          A decisão deve considerar fatores qualitativos: visibilidade da fachada,
          densidade de concorrência, acesso de transporte público e perfil do público-alvo.
        </p>
      </div>
    </div>
  )
}

function DriverCard({ driver }: { driver: Driver }) {
  const isB = driver.favoravel === 'B'
  const isA = driver.favoravel === 'A'
  const diffStr =
    driver.diffPct != null
      ? `${driver.diffPct > 0 ? '+' : ''}${driver.diffPct.toFixed(1)}%`
      : '≈ 0%'

  const iconColor =
    driver.categoria === 'receita'
      ? 'text-emerald-600'
      : driver.categoria === 'custo'
        ? 'text-amber-600'
        : driver.categoria === 'retorno'
          ? 'text-violet-600'
          : 'text-sky-600'

  return (
    <Card className="border hover:border-foreground/20 transition-colors">
      <CardContent className="p-3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground truncate">
            {driver.label}
          </p>
          <div className="flex items-center gap-1 shrink-0">
            {isB ? (
              <TrendingUp size={13} className="text-emerald-600" />
            ) : isA ? (
              <TrendingDown size={13} className="text-red-500" />
            ) : (
              <Equal size={13} className="text-muted-foreground" />
            )}
            <Badge
              variant="outline"
              className={cn(
                'text-[10px] font-mono h-5 px-1',
                isB && 'border-emerald-200 text-emerald-700 bg-emerald-50 dark:bg-emerald-950/20',
                isA && 'border-red-200 text-red-700 bg-red-50 dark:bg-red-950/20',
              )}
            >
              {diffStr}
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className={cn('font-mono tabular-nums', isA && 'font-semibold text-emerald-700')}>
            {driver.valorA}
          </span>
          <span className="text-muted-foreground">→</span>
          <span className={cn('font-mono tabular-nums', isB && 'font-semibold text-emerald-700')}>
            {driver.valorB}
          </span>
        </div>

        <p className="text-[10px] text-muted-foreground leading-snug border-t border-border pt-1.5">
          <span className={cn('font-medium', iconColor)}>Base: </span>
          {driver.metodologia}
        </p>
      </CardContent>
    </Card>
  )
}

function NarrativaExecutiva({
  drivers,
  bairroA,
  bairroB,
  vencedor,
  mesmosModelos,
  modelo,
}: {
  drivers: Driver[]
  bairroA: string
  bairroB: string
  vencedor: Favor
  mesmosModelos: boolean
  modelo: string
}) {
  const top3 = drivers.slice(0, 3)
  const ganhador = vencedor === 'B' ? bairroB : vencedor === 'A' ? bairroA : null
  const perdedor = vencedor === 'B' ? bairroA : vencedor === 'A' ? bairroB : null

  const frases: string[] = []

  // Abertura
  if (ganhador && perdedor) {
    const lucroD = drivers.find((d) => d.label === 'Lucro mensal estimado')
    const payD = drivers.find((d) => d.label === 'Payback do investimento')

    if (lucroD && lucroD.favoravel === vencedor) {
      frases.push(
        `O ponto em ${ganhador} se destaca pelo lucro mensal projetado superior, que é o principal atrativo para o investidor.`
      )
    } else if (payD && payD.favoravel === vencedor) {
      frases.push(
        `A principal vantagem de ${ganhador} é o payback mais curto, reduzindo o risco de exposição do capital investido.`
      )
    } else {
      frases.push(
        `${ganhador} apresenta melhor conjunto de métricas financeiras quando comparado a ${perdedor}.`
      )
    }

    // Driver 2 e 3
    const outrosDrivers = top3.filter(
      (d) => d.label !== 'Lucro mensal estimado' && d.label !== 'Payback do investimento' && d.favoravel !== 'neutro'
    )
    if (outrosDrivers.length > 0) {
      const nomes = outrosDrivers.map((d) => d.label.toLowerCase())
      const ultimo = nomes.pop()
      const lista = nomes.length > 0 ? `${nomes.join(', ')} e ${ultimo}` : ultimo
      frases.push(
        `Isso é sustentado por vantagens em ${lista}, que juntos compõem um cenário de menor risco operacional.`
      )
    }

    // Ressalva
    const neutros = top3.filter((d) => d.favoravel === 'neutro')
    if (neutros.length > 0) {
      frases.push(
        `Em ${neutros[0].label.toLowerCase()}, ambos os pontos estão alinhados, o que não pesa na decisão.`
      )
    }

    // Conclusão
    if (mesmosModelos) {
      frases.push(
        `Como o modelo de negócio é o mesmo (${modelo}), a decisão deve privilegiar ${ganhador}, a menos que ${perdedor} ofereça vantagens estratégicas não quantificáveis — como melhor visibilidade de rua, menor concorrência imediata ou acesso superior ao transporte público.`
      )
    } else {
      frases.push(
        `Com modelos distintos, a escolha depende do apetite a risco da operação: ${modelo} em ${vencedor === 'A' ? bairroA : bairroB} representa ${modelo.toLowerCase().includes('premium') ? 'maior investimento com retorno potencial mais alto' : modelo.toLowerCase().includes('low') ? 'entrada de baixo risco e capital reduzido' : 'perfil de retorno moderado'}.`
      )
    }
  } else {
    frases.push(
      `Os dois pontos apresentam retorno financeiro equivalente dentro da margem de erro da projeção. Recomendamos aprofundar a análise qualitativa: compare a intensidade de concorrência, o horário de pico dos vizinhos e a projeção de crescimento demográfico do bairro antes de tomar a decisão final.`
    )
  }

  return (
    <div className="space-y-2">
      {frases.map((f, i) => (
        <p key={i} className="text-xs text-foreground leading-relaxed">
          {f}
        </p>
      ))}
    </div>
  )
}
