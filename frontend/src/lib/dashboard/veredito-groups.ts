import type { Veredito } from '@/types/domain'

/** Vereditos considerados aprovação no dashboard. */
export const VEREDITOS_APROVADOS: Veredito[] = ['APROVADO', 'APROVADO COM RESSALVAS']

export const VEREDITOS_REPROVADOS: Veredito[] = ['REPROVADO']

export function isVereditoAprovado(veredito: Veredito | null | undefined): boolean {
  return veredito != null && VEREDITOS_APROVADOS.includes(veredito)
}
