/**
 * useComparacao — carrega 2 relatórios em paralelo pra comparar lado a lado.
 *
 * Reusa `useRelatorioDetail` (cache hit se um deles já foi visitado).
 * Retorna estado consolidado pra a página renderizar com 1 loading/error.
 */
import { useRelatorioDetail, type RelatorioDetail } from './useRelatorioDetail'

export interface ComparacaoState {
  relatorioA: RelatorioDetail | undefined
  relatorioB: RelatorioDetail | undefined
  isLoading: boolean
  error: Error | null
  /** True quando faltam IDs ou um dos relatórios não existe */
  invalido: boolean
  motivoInvalido?: string
}

export function useComparacao(
  idA: string | undefined,
  idB: string | undefined,
): ComparacaoState {
  const qa = useRelatorioDetail(idA)
  const qb = useRelatorioDetail(idB)

  if (!idA || !idB) {
    return {
      relatorioA: undefined,
      relatorioB: undefined,
      isLoading: false,
      error: null,
      invalido: true,
      motivoInvalido:
        'Selecione 2 relatórios pra comparar (use a listagem em /relatorios).',
    }
  }

  if (idA === idB) {
    return {
      relatorioA: undefined,
      relatorioB: undefined,
      isLoading: false,
      error: null,
      invalido: true,
      motivoInvalido: 'Os 2 IDs são idênticos — escolha relatórios diferentes.',
    }
  }

  return {
    relatorioA: qa.data,
    relatorioB: qb.data,
    isLoading: qa.isLoading || qb.isLoading,
    error: (qa.error as Error | null) ?? (qb.error as Error | null) ?? null,
    invalido: false,
  }
}

// ── Helpers de diff pra UI ─────────────────────────────────────────────

/** Calcula Δ% entre dois números. Retorna null se base é 0. */
export function calcularDelta(
  valorA: number | null | undefined,
  valorB: number | null | undefined,
): { delta: number; pct: number | null; direcao: 'up' | 'down' | 'eq' } | null {
  if (valorA == null || valorB == null) return null
  if (!Number.isFinite(valorA) || !Number.isFinite(valorB)) return null
  const delta = valorB - valorA
  const direcao = delta > 0 ? 'up' : delta < 0 ? 'down' : 'eq'
  const pct = valorA !== 0 ? (delta / Math.abs(valorA)) * 100 : null
  return { delta, pct, direcao }
}

/** Formata BRL pra exibição. */
export function formatBRL(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return v.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

export function formatPct(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return `${v.toFixed(1)}%`
}
