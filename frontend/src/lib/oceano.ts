import type { VereditoOceano } from '@/types/domain'

export const OCEANO_CONFIG: Record<
  VereditoOceano,
  { label: string; emoji: string; bg: string; text: string; ring: string }
> = {
  OCEANO_AZUL: {
    label: 'Oceano Azul',
    emoji: '🟢',
    bg: 'bg-emerald-600',
    text: 'text-white',
    ring: 'ring-emerald-500/40',
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
