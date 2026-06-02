/** Placeholder do A0/A6 quando a tool não retornou o dado. */
const PLACEHOLDERS = new Set([
  'dados_nao_disponiveis',
  'dados não disponíveis',
  'n/a',
  'na',
  '—',
  '-',
])

export function isDadoIndisponivel(
  value: string | number | null | undefined,
): boolean {
  if (value == null) return true
  if (typeof value === 'number') return false
  const s = String(value).trim()
  if (!s) return true
  return PLACEHOLDERS.has(s.toLowerCase())
}

export function valorDisponivel(
  value: string | number | null | undefined,
): string | number | null {
  return isDadoIndisponivel(value) ? null : (value as string | number)
}
