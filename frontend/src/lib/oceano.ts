import type { VereditoOceano } from '@/types/domain'

/** HSL fills for charts, map pins, legends (Tailwind blue-600 ≈ hsl(221 83% 53%)). */
export const OCEANO_FILL: Record<VereditoOceano, string> = {
  OCEANO_AZUL: 'hsl(221 83% 53%)',
  TRANSICAO: 'hsl(45 95% 55%)',
  VERMELHO: 'hsl(0 70% 50%)',
}

/** Pin / map legend when A9 is missing. */
export const OCEANO_FILL_SEM_A9 = 'hsl(220 10% 55%)'

/** Pie chart slice when A9 is missing (slightly lighter). */
export const OCEANO_FILL_SEM_A9_CHART = 'hsl(220 10% 70%)'

export const OCEANO_CHART_COLORS: Record<string, string> = {
  OCEANO_AZUL: OCEANO_FILL.OCEANO_AZUL,
  TRANSICAO: OCEANO_FILL.TRANSICAO,
  VERMELHO: OCEANO_FILL.VERMELHO,
  SEM_A9: OCEANO_FILL_SEM_A9_CHART,
}

export const OCEANO_LEGEND_ITEMS: { color: string; label: string }[] = [
  { color: OCEANO_FILL.OCEANO_AZUL, label: 'Oceano azul' },
  { color: OCEANO_FILL.TRANSICAO, label: 'Transição' },
  { color: OCEANO_FILL.VERMELHO, label: 'Oceano vermelho' },
  { color: OCEANO_FILL_SEM_A9, label: 'Sem A9' },
]

export const OCEANO_CONFIG: Record<
  VereditoOceano,
  { label: string; emoji: string; bg: string; text: string; ring: string }
> = {
  OCEANO_AZUL: {
    label: 'Oceano Azul',
    emoji: '🔵',
    bg: 'bg-blue-600',
    text: 'text-white',
    ring: 'ring-blue-500/40',
  },
  TRANSICAO: {
    label: 'Transição',
    emoji: '🟡',
    bg: 'bg-amber-500',
    text: 'text-black',
    ring: 'ring-amber-500/40',
  },
  VERMELHO: {
    label: 'Oceano Vermelho',
    emoji: '🔴',
    bg: 'bg-red-600',
    text: 'text-white',
    ring: 'ring-red-500/40',
  },
}

const OCEANO_KEYS = new Set<string>(['OCEANO_AZUL', 'TRANSICAO', 'VERMELHO'])

export function normalizeVereditoOceano(
  raw: string | null | undefined,
): VereditoOceano | null {
  if (!raw) return null
  const key = raw.trim().toUpperCase().replace(/\s+/g, '_')
  if (OCEANO_KEYS.has(key)) return key as VereditoOceano
  if (key === 'OCEANO_VERMELHO') return 'VERMELHO'
  return null
}

export function oceanoLabel(raw: string | null | undefined): string {
  const v = normalizeVereditoOceano(raw)
  return v ? OCEANO_CONFIG[v].label : 'Sem A9'
}
