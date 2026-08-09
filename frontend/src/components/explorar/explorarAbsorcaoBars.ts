export function explorarBarPercents(values: number[]): number[] {
  const max = Math.max(0, ...values.map((v) => Math.max(0, Number(v) || 0)))
  if (max <= 0) return values.map(() => 0)
  return values.map((v) => Math.round((Math.max(0, Number(v) || 0) / max) * 100))
}

export function explorarIntPt(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return Math.round(Number(n)).toLocaleString('pt-BR')
}
