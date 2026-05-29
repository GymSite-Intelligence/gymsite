const IS_DEV = typeof process !== 'undefined' && process.env?.NODE_ENV === 'development';

/**
 * Formata um valor numérico para a moeda BRL (R$).
 * Retorna '—' se for nulo, indefinido ou não-finito (e loga aviso em dev).
 */
export function formatBRL(
  v: number | null | undefined,
  opts?: { compact?: boolean }
): string {
  if (v == null) return '—'
  if (!Number.isFinite(v)) {
    if (IS_DEV) {
      console.warn(`[formatBRL] Valor numérico inválido recebido:`, v)
    }
    return '—'
  }
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
    notation: opts?.compact ? 'compact' : 'standard',
  }).format(v)
}

/**
 * Limiar (sentinela) usado pelo backend para representar payback inviável.
 */
export const INVIAVEL_PAYBACK_THRESHOLD = 999;

/**
 * Formata o tempo de payback em meses/anos.
 */
export function formatPayback(m: number | null | undefined): string {
  if (m == null || typeof m !== 'number' || !Number.isFinite(m)) {
    if (m != null && IS_DEV) {
      console.warn(`[formatPayback] Valor de meses de payback inválido:`, m)
    }
    return '—'
  }
  if (m >= INVIAVEL_PAYBACK_THRESHOLD) return 'inviável'
  if (m >= 24) return `${(m / 12).toFixed(1)} anos`
  return `${m} meses`
}

/**
 * Formata um número inteiro com separador de milhar.
 */
export function formatInt(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return v.toLocaleString('pt-BR')
}

/**
 * Formata um percentual.
 */
export function formatPct(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return `${v.toFixed(1)}%`
}
