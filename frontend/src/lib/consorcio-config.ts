/**
 * Regras UI-only para bloco "Consórcio recomendado" (GYM-23).
 * Valores de referência — não substituem simulação A4 nem probabilidade de sorteio.
 */

/**
 * OBS: (deprecado) o card de consórcio não é mais “gated” por CAPEX.
 * Mantemos a lógica de estimativa e benchmark; a decisão é estratégica (preservar caixa).
 */

/**
 * Prazo e taxas médias (referências de UI).
 * OBS: não são "dados de mercado" — são defaults para estimativa no dashboard.
 */
export const CONSORCIO_PRAZO_MESES = 120
export const CONSORCIO_TAXA_ADMIN_PCT = 0.18
export const CONSORCIO_TAXA_FUNDO_RESERVA_PCT = 0.02

/** Referência financiamento bancário (60×, ~1,2% a.m.) para comparar economia. */
export const FINANCIAMENTO_PRAZO_MESES = 60
export const FINANCIAMENTO_TAXA_MENSAL = 0.012

export const VECTRA_CONTATO_URL =
  'https://wa.me/5547999999999?text=Olá! Vi a análise GymSite e quero falar sobre consórcio para academia.'

export function getCapexMid(
  cenarios: Record<'low' | 'mid' | 'premium', { capex_total?: number; capex_detalhado?: { total?: number } }> | undefined,
): number | null {
  const mid = cenarios?.mid
  if (!mid) return null
  const v = mid.capex_total ?? mid.capex_detalhado?.total
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** Arredonda CAPEX para carta comercial (múltiplos de R$ 50 mil). */
export function sugerirValorCarta(capexMid: number): number {
  const base = Math.max(0, capexMid)
  // Se vier 0/negativo por algum bug de upstream, garantimos uma carta mínima.
  return Math.max(50_000, Math.ceil(base / 50_000) * 50_000)
}

function parcelaPrice(valor: number, taxa: number, prazo: number): number {
  if (taxa <= 0) return valor / prazo
  const f = Math.pow(1 + taxa, prazo)
  return (valor * taxa * f) / (f - 1)
}

export function estimarParcelaConsorcio(params: {
  valorCarta: number
  prazoMeses: number
  taxaAdminPct?: number
  taxaFundoReservaPct?: number
}): number {
  const taxaAdminPct = params.taxaAdminPct ?? CONSORCIO_TAXA_ADMIN_PCT
  const taxaFundoReservaPct =
    params.taxaFundoReservaPct ?? CONSORCIO_TAXA_FUNDO_RESERVA_PCT
  const totalEstimado =
    params.valorCarta * (1 + taxaAdminPct + taxaFundoReservaPct)
  return totalEstimado / params.prazoMeses
}

export interface LanceBenchmark {
  /** Percentual do lance sobre a carta, ex.: 0.25 → 25%. */
  pct: number
  label: 'baixo' | 'médio' | 'alto'
}

export interface LanceBenchmarkPack {
  bracketLabel: string
  prazoMeses: number
  low: LanceBenchmark
  avg: LanceBenchmark
  high: LanceBenchmark
  defaultPreset: LanceBenchmark['label']
}

/**
 * Benchmarks de lance (assunções configuráveis).
 * A ideia aqui é orientar o investidor sobre "ordem de grandeza" por cota.
 *
 * IMPORTANTE:
 * - Não afirmamos como "média factual" — é um benchmark paramétrico.
 * - Ajuste esses números conforme sua administradora/grupo/segmento.
 */
const LANCE_BENCHMARKS: Array<{
  maxCarta: number | null
  bracketLabel: string
  prazos: Record<
    number,
    {
      lowPct: number
      avgPct: number
      highPct: number
      defaultPreset: LanceBenchmark['label']
    }
  >
}> = [
  {
    maxCarta: 300_000,
    bracketLabel: 'até R$ 300k',
    prazos: {
      84: { lowPct: 0.2, avgPct: 0.27, highPct: 0.35, defaultPreset: 'médio' },
      120: { lowPct: 0.18, avgPct: 0.25, highPct: 0.33, defaultPreset: 'médio' },
      180: { lowPct: 0.16, avgPct: 0.22, highPct: 0.3, defaultPreset: 'baixo' },
    },
  },
  {
    maxCarta: 600_000,
    bracketLabel: 'R$ 300k–600k',
    prazos: {
      84: { lowPct: 0.22, avgPct: 0.3, highPct: 0.38, defaultPreset: 'médio' },
      120: { lowPct: 0.2, avgPct: 0.28, highPct: 0.36, defaultPreset: 'médio' },
      180: { lowPct: 0.18, avgPct: 0.25, highPct: 0.33, defaultPreset: 'baixo' },
    },
  },
  {
    maxCarta: null,
    bracketLabel: 'acima de R$ 600k',
    prazos: {
      84: { lowPct: 0.25, avgPct: 0.33, highPct: 0.42, defaultPreset: 'médio' },
      120: { lowPct: 0.22, avgPct: 0.3, highPct: 0.4, defaultPreset: 'médio' },
      180: { lowPct: 0.2, avgPct: 0.28, highPct: 0.38, defaultPreset: 'baixo' },
    },
  },
] as const

export function getLanceBenchmarkPack(params: {
  valorCarta: number
  prazoMeses: number
}): LanceBenchmarkPack {
  const prazosDisponiveis = [84, 120, 180] as const
  const prazo =
    (prazosDisponiveis.includes(params.prazoMeses as (typeof prazosDisponiveis)[number])
      ? params.prazoMeses
      : 120) ?? 120

  const bracket =
    LANCE_BENCHMARKS.find((b) => b.maxCarta == null || params.valorCarta <= b.maxCarta) ??
    LANCE_BENCHMARKS[LANCE_BENCHMARKS.length - 1]

  const p =
    bracket.prazos[prazo] ??
    bracket.prazos[120] ?? { lowPct: 0.2, avgPct: 0.28, highPct: 0.36, defaultPreset: 'médio' }

  return {
    bracketLabel: bracket.bracketLabel,
    prazoMeses: prazo,
    low: { pct: p.lowPct, label: 'baixo' },
    avg: { pct: p.avgPct, label: 'médio' },
    high: { pct: p.highPct, label: 'alto' },
    defaultPreset: p.defaultPreset,
  }
}

export function estimarPosLance(params: {
  valorCarta: number
  prazoMeses: number
  lancePct: number
  taxaAdminPct?: number
  taxaFundoReservaPct?: number
}): {
  lanceValor: number
  amortizacaoPrincipal: number
  saldoPrincipalRestante: number
  totalEstimadoPosLance: number
  parcelaPosLance: number
} {
  const taxaAdminPct = params.taxaAdminPct ?? CONSORCIO_TAXA_ADMIN_PCT
  const taxaFundoReservaPct =
    params.taxaFundoReservaPct ?? CONSORCIO_TAXA_FUNDO_RESERVA_PCT

  const lancePct = Math.min(0.95, Math.max(0, params.lancePct))
  const lanceValor = params.valorCarta * lancePct

  // Assunção: o lance é um aporte próprio que amortiza o principal (carta).
  // Taxas (admin/fundo) permanecem proporcionais à carta cheia (referência conservadora).
  const amortizacaoPrincipal = lanceValor
  const saldoPrincipalRestante = Math.max(0, params.valorCarta - amortizacaoPrincipal)
  const totalEstimadoPosLance =
    saldoPrincipalRestante + params.valorCarta * (taxaAdminPct + taxaFundoReservaPct)
  const parcelaPosLance = totalEstimadoPosLance / params.prazoMeses

  return {
    lanceValor,
    amortizacaoPrincipal,
    saldoPrincipalRestante,
    totalEstimadoPosLance,
    parcelaPosLance,
  }
}

export interface ConsorcioEstimativa {
  valorCarta: number
  prazoMeses: number
  parcelaConsorcio: number
  parcelaFinanciamentoRef: number
  economiaTotal: number
  economiaPct: number
}

export function estimarConsorcio(capexMid: number): ConsorcioEstimativa {
  const valorCarta = sugerirValorCarta(capexMid)
  const parcelaConsorcio = estimarParcelaConsorcio({
    valorCarta,
    prazoMeses: CONSORCIO_PRAZO_MESES,
  })
  const parcelaFinanciamentoRef = parcelaPrice(
    valorCarta,
    FINANCIAMENTO_TAXA_MENSAL,
    FINANCIAMENTO_PRAZO_MESES,
  )
  const totalConsorcio = parcelaConsorcio * CONSORCIO_PRAZO_MESES
  const totalFin = parcelaFinanciamentoRef * FINANCIAMENTO_PRAZO_MESES
  const economiaTotal = Math.max(0, totalFin - totalConsorcio)
  const economiaPct = totalFin > 0 ? (economiaTotal / totalFin) * 100 : 0

  return {
    valorCarta,
    prazoMeses: CONSORCIO_PRAZO_MESES,
    parcelaConsorcio,
    parcelaFinanciamentoRef,
    economiaTotal,
    economiaPct,
  }
}
