/**
 * ResumoViabilidadeComparativa — narrativa técnica explicando por que A ou B
 * é financeiramente mais vantajoso, com destaque nos drivers de diferença.
 */
import { TrendingUp, TrendingDown, Equal, AlertTriangle, CheckCircle } from 'lucide-react'
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

interface Driver {
  label: string
  valorA: string
  valorB: string
  diffPct: number | null
  favoravel: 'A' | 'B' | 'neutro'
  peso: number // para ordenar importância
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
          Dados financeiros insuficientes para gerar o resumo comparativo.
        </CardContent>
      </Card>
    )
  }

  // ── Computa drivers ──
  const drivers: Driver[] = []

  // Receita
  const diffReceita = deltaPct(cenarioA.receita_mensal, cenarioB.receita_mensal)
  if (diffReceita != null) {
    drivers.push({
      label: 'Receita mensal',
      valorA: fmtBRL(cenarioA.receita_mensal),
      valorB: fmtBRL(cenarioB.receita_mensal),
      diffPct: diffReceita,
      favoravel: diffReceita > 5 ? 'B' : diffReceita < -5 ? 'A' : 'neutro',
      peso: Math.abs(diffReceita),
    })
  }

  // Aluguel (do relatório ou do cenário)
  const aluguelAeff = aluguelA ?? cenarioA.custos_detalhados?.aluguel ?? cenarioA.custos_fixos_total
  const aluguelBeff = aluguelB ?? cenarioB.custos_detalhados?.aluguel ?? cenarioB.custos_fixos_total
  const diffAluguel = deltaPct(aluguelAeff, aluguelBeff)
  if (diffAluguel != null) {
    drivers.push({
      label: 'Aluguel / Custos fixos',
      valorA: fmtBRL(aluguelAeff),
      valorB: fmtBRL(aluguelBeff),
      diffPct: diffAluguel,
      // Aluguel MENOR é melhor, então se B é menor (diff negativo), B é favorável
      favoravel: diffAluguel < -10 ? 'B' : diffAluguel > 10 ? 'A' : 'neutro',
      peso: Math.abs(diffAluguel) * 0.8, // peso ligeiramente menor que receita
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
      peso: Math.abs(diffLucro) * 1.2, // peso maior
    })
  }

  // Margem
  const diffMargem = deltaPct(cenarioA.margem_percentual, cenarioB.margem_percentual)
  if (diffMargem != null) {
    drivers.push({
      label: 'Margem líquida',
      valorA: fmtPct(cenarioA.margem_percentual),
      valorB: fmtPct(cenarioB.margem_percentual),
      diffPct: diffMargem,
      favoravel: diffMargem > 5 ? 'B' : diffMargem < -5 ? 'A' : 'neutro',
      peso: Math.abs(diffMargem),
    })
  }

  // Payback
  const paybackA = cenarioA.payback_meses
  const paybackB = cenarioB.payback_meses
  let diffPaybackPct: number | null = null
  let favoravelPayback: 'A' | 'B' | 'neutro' = 'neutro'
  if (paybackA != null && paybackB != null && paybackA > 0 && paybackB > 0) {
    diffPaybackPct = ((paybackB - paybackA) / paybackA) * 100
    // Payback MENOR é melhor
    favoravelPayback = diffPaybackPct < -15 ? 'B' : diffPaybackPct > 15 ? 'A' : 'neutro'
  }
  const diffPaybackAbs = paybackA != null && paybackB != null ? paybackB - paybackA : null
  if (diffPaybackAbs != null) {
    drivers.push({
      label: 'Payback',
      valorA: `${paybackA} meses`,
      valorB: `${paybackB} meses`,
      diffPct: diffPaybackPct,
      favoravel: favoravelPayback,
      peso: Math.min(Math.abs(diffPaybackPct ?? 0), 50),
    })
  }

  // TIR
  const tirA = cenarioA.tir_anual_pct
  const tirB = cenarioB.tir_anual_pct
  const diffTir = deltaPct(tirA, tirB)
  if (diffTir != null) {
    drivers.push({
      label: 'TIR anual',
      valorA: fmtPct(tirA),
      valorB: fmtPct(tirB),
      diffPct: diffTir,
      favoravel: diffTir > 10 ? 'B' : diffTir < -10 ? 'A' : 'neutro',
      peso: Math.abs(diffTir) * 0.9,
    })
  }

  // VPL
  const diffVpl = deltaPct(cenarioA.vpl_5_anos, cenarioB.vpl_5_anos)
  if (diffVpl != null) {
    drivers.push({
      label: 'VPL 5 anos',
      valorA: fmtBRL(cenarioA.vpl_5_anos),
      valorB: fmtBRL(cenarioB.vpl_5_anos),
      diffPct: diffVpl,
      favoravel: diffVpl > 10 ? 'B' : diffVpl < -10 ? 'A' : 'neutro',
      peso: Math.abs(diffVpl) * 1.1,
    })
  }

  // CAPEX
  const capexA = cenarioA.investimento_total ?? cenarioA.capex_total ?? cenarioA.capex_estimado
  const capexB = cenarioB.investimento_total ?? cenarioB.capex_total ?? cenarioB.capex_estimado
  const diffCapex = deltaPct(capexA, capexB)
  if (diffCapex != null) {
    drivers.push({
      label: 'Investimento total (CAPEX+giro)',
      valorA: fmtBRL(capexA),
      valorB: fmtBRL(capexB),
      diffPct: diffCapex,
      // CAPEX MENOR é melhor
      favoravel: diffCapex < -10 ? 'B' : diffCapex > 10 ? 'A' : 'neutro',
      peso: Math.abs(diffCapex) * 0.7,
    })
  }

  // Ordena por impacto
  const driversSorted = drivers.sort((a, b) => b.peso - a.peso)
  const topDrivers = driversSorted.slice(0, 5)

  // ── Decide vencedor ──
  const pontosA = drivers.filter((d) => d.favoravel === 'A').reduce((s, d) => s + d.peso, 0)
  const pontosB = drivers.filter((d) => d.favoravel === 'B').reduce((s, d) => s + d.peso, 0)
  const vencedor: 'A' | 'B' | 'empate' =
    pontosB > pontosA * 1.15 ? 'B' : pontosA > pontosB * 1.15 ? 'A' : 'empate'

  // ── Gera narrativa ──
  const mesmosModelos = cenarioA.modelo === cenarioB.modelo
  const modeloStr = cenarioA.modelo ?? 'N/A'

  return (
    <section className="rounded-lg border border-border overflow-hidden">
      <header className="px-4 py-3 bg-muted/30 border-b border-border">
        <h3 className="text-sm font-semibold">Resumo Técnico de Viabilidade</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Análise dos drivers financeiros que diferenciam os dois pontos
        </p>
      </header>

      <div className="p-4 space-y-5">
        {/* Veredito do comparativo */}
        <div className="flex items-center gap-3">
          {vencedor === 'B' ? (
            <>
              <CheckCircle size={18} className="text-emerald-600" />
              <div>
                <p className="text-sm font-semibold">
                  {bairroB} apresenta melhor viabilidade financeira
                </p>
                <p className="text-xs text-muted-foreground">
                  {mesmosModelos
                    ? `Ambos seguem o modelo ${modeloStr}, mas ${bairroB} tem vantagens operacionais.`
                    : `Modelos diferentes — ${bairroB} (${cenarioB.modelo}) vs ${bairroA} (${cenarioA.modelo}).`}
                </p>
              </div>
            </>
          ) : vencedor === 'A' ? (
            <>
              <CheckCircle size={18} className="text-emerald-600" />
              <div>
                <p className="text-sm font-semibold">
                  {bairroA} apresenta melhor viabilidade financeira
                </p>
                <p className="text-xs text-muted-foreground">
                  {mesmosModelos
                    ? `Ambos seguem o modelo ${modeloStr}, mas ${bairroA} tem vantagens operacionais.`
                    : `Modelos diferentes — ${bairroA} (${cenarioA.modelo}) vs ${bairroB} (${cenarioB.modelo}).`}
                </p>
              </div>
            </>
          ) : (
            <>
              <Equal size={18} className="text-sky-600" />
              <div>
                <p className="text-sm font-semibold">
                  Viabilidade financeira equilibrada entre os dois pontos
                </p>
                <p className="text-xs text-muted-foreground">
                  {mesmosModelos
                    ? `Ambos no modelo ${modeloStr}. As diferenças são marginais — a decisão pode pender para fatores qualitativos (visibilidade, concorrência, dores dominantes).`
                    : `Modelos distintos compensam-se financeiramente. Analise outros critérios.`}
                </p>
              </div>
            </>
          )}
        </div>

        {/* Drivers principais */}
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            Principais drivers de diferença
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {topDrivers.map((d) => (
              <DriverCard key={d.label} driver={d} />
            ))}
          </div>
        </div>

        {/* Narrativa explicativa */}
        <div className="rounded-lg bg-muted/30 border border-border p-3 space-y-2">
          <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            Análise narrativa
          </p>
          <Narrativa
            drivers={driversSorted}
            bairroA={bairroA}
            bairroB={bairroB}
            vencedor={vencedor}
            mesmosModelos={mesmosModelos}
            modelo={modeloStr}
          />
        </div>

        {/* Alerta de modelo diferente */}
        {!mesmosModelos && (
          <div className="flex items-start gap-2 text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-md px-3 py-2">
            <AlertTriangle size={14} className="shrink-0 mt-0.5" />
            <p className="text-xs">
              <strong>Atenção:</strong> os modelos recomendados são diferentes (
              {cenarioA.modelo} vs {cenarioB.modelo}). Isso significa que a
              comparação direta de receita e CAPEX pode não ser justa — o modelo
              {cenarioB.modelo ?? ''} naturalmente exige{' '}
              {(cenarioB.modelo ?? '').toLowerCase().includes('premium')
                ? 'maior investimento e promete maior retorno'
                : (cenarioB.modelo ?? '').toLowerCase().includes('low')
                  ? 'menor investimento com retorno mais conservador'
                  : 'perfil de risco diferente'}
              . Considere o payback e a TIR como métricas normalizadas.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

function DriverCard({
  driver,
}: {
  driver: Driver
}) {
  const isB = driver.favoravel === 'B'
  const isA = driver.favoravel === 'A'
  const diffStr =
    driver.diffPct != null
      ? `${driver.diffPct > 0 ? '+' : ''}${driver.diffPct.toFixed(1)}%`
      : '—'

  return (
    <div className="rounded-md border border-border bg-card p-2.5 flex items-center justify-between gap-2">
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
          {driver.label}
        </p>
        <div className="flex items-center gap-2 mt-1 text-xs">
          <span className={cn('font-mono tabular-nums', isA && 'font-semibold text-emerald-600')}>
            {driver.valorA}
          </span>
          <span className="text-muted-foreground">→</span>
          <span className={cn('font-mono tabular-nums', isB && 'font-semibold text-emerald-600')}>
            {driver.valorB}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {isB ? (
          <TrendingUp size={14} className="text-emerald-600" />
        ) : isA ? (
          <TrendingDown size={14} className="text-red-500" />
        ) : (
          <Equal size={14} className="text-muted-foreground" />
        )}
        <Badge
          variant="outline"
          className={cn(
            'text-[10px] font-mono',
            isB && 'border-emerald-200 text-emerald-700 bg-emerald-50 dark:bg-emerald-950/20',
            isA && 'border-red-200 text-red-700 bg-red-50 dark:bg-red-950/20',
          )}
        >
          {diffStr}
        </Badge>
      </div>
    </div>
  )
}

function Narrativa({
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
  vencedor: 'A' | 'B' | 'empate'
  mesmosModelos: boolean
  modelo: string
}) {
  // Encontra os 2 drivers mais impactantes
  const top2 = drivers.slice(0, 2)
  const [d1, d2] = top2

  if (!d1) {
    return (
      <p className="text-xs text-muted-foreground">
        Dados financeiros insuficientes para análise narrativa.
      </p>
    )
  }

  const ganhador = vencedor === 'B' ? bairroB : vencedor === 'A' ? bairroA : null
  const perdedor = vencedor === 'B' ? bairroA : vencedor === 'A' ? bairroB : null

  // Monta frases sobre os drivers
  const frases: string[] = []

  // Driver 1
  if (d1.favoravel === 'neutro') {
    frases.push(
      `Em ${d1.label.toLowerCase()}, ambos os pontos estão muito próximos (${d1.valorA} vs ${d1.valorB}), não sendo um fator decisivo.`
    )
  } else {
    const fav = d1.favoravel === 'B' ? bairroB : bairroA
    const outro = d1.favoravel === 'B' ? bairroA : bairroB
    const diffAbs = d1.diffPct != null ? Math.abs(d1.diffPct).toFixed(1) : null
    frases.push(
      `O principal diferencial é ${d1.label.toLowerCase()}: ${fav} ${d1.label.includes('Aluguel') || d1.label.includes('CAPEX') || d1.label.includes('Payback') ? 'tem vantagem com' : 'se destaca com'} ${d1.valorA === d1.favoravel ? d1.valorA : d1.valorB}${diffAbs ? ` (${diffAbs}% vs ${outro})` : ''}.`
    )
  }

  // Driver 2
  if (d2) {
    if (d2.favoravel === 'neutro') {
      frases.push(`${d2.label} também é equivalente entre os dois pontos.`)
    } else {
      const fav2 = d2.favoravel === 'B' ? bairroB : bairroA
      const outro2 = d2.favoravel === 'B' ? bairroA : bairroB
      frases.push(
        `Em ${d2.label.toLowerCase()}, ${fav2} leva vantagem sobre ${outro2}${d2.diffPct != null ? ` com uma diferença de ${Math.abs(d2.diffPct).toFixed(1)}%` : ''}.`
      )
    }
  }

  // Conclusão
  if (ganhador && perdedor) {
    const paybackDriver = drivers.find((d) => d.label === 'Payback')
    const lucroDriver = drivers.find((d) => d.label === 'Lucro mensal estimado')

    if (mesmosModelos) {
      frases.push(
        `Como ambos operam no modelo ${modelo}, a escolha de ${ganhador} é justificada ${lucroDriver && lucroDriver.favoravel === (vencedor === 'B' ? 'B' : 'A') ? 'principalmente pelo lucro mensal superior' : paybackDriver && paybackDriver.favoravel === (vencedor === 'B' ? 'B' : 'A') ? 'principalmente pelo payback mais curto' : 'pela combinação de métricas financeiras mais favoráveis'}. ${perdedor} só seria preferível se houver fatores qualitativos decisivos (ex: visibilidade, concorrência menor) não capturados na planilha.`
      )
    } else {
      frases.push(
        `Com modelos distintos, ${ganhador} apresenta melhor relação risco/retorno. ${perdedor} pode fazer sentido se o objetivo for ${modelo.toLowerCase().includes('low') ? 'entrada conservadora no mercado' : modelo.toLowerCase().includes('premium') ? 'premiumização da marca' : 'estratégia de nicho diferente'}.`
      )
    }
  } else {
    frases.push(
      `As métricas financeiras são equilibradas. A decisão final deve considerar fatores qualitativos: dores dominantes dos concorrentes, visibilidade do ponto, densidade populacional e projeção de crescimento do bairro.`
    )
  }

  return (
    <div className="space-y-1.5">
      {frases.map((f, i) => (
        <p key={i} className="text-xs text-foreground leading-relaxed">
          {f}
        </p>
      ))}
    </div>
  )
}
