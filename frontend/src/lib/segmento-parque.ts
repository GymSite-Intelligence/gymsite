/** Segmentos do parque ativo (CNPJ) — sem "outro". */
export const SEGMENTO_PARQUE_LABELS: Record<string, string> = {
  academia: 'Academia tradicional',
  crossfit_box: 'CrossFit / Box',
  studio_pilates: 'Estúdio Pilates',
  studio_funcional: 'Estúdio funcional',
  studio_bem_estar: 'Estúdio bem-estar',
  lutas: 'Lutas / MMA',
  personal_studio: 'Personal / coaching',
  aqua_fitness: 'Natacao / aquáticos',
  saude_clinica: 'Clínica / reabilitação',
}

export const SEGMENTO_PARQUE_ORDER = [
  'academia',
  'studio_pilates',
  'crossfit_box',
  'studio_funcional',
  'studio_bem_estar',
  'lutas',
  'personal_studio',
  'aqua_fitness',
] as const

export const SEGMENTO_BADGE_CLASS: Record<string, string> = {
  academia: 'bg-blue-500/15 text-blue-700 dark:text-blue-300',
  crossfit_box: 'bg-orange-500/15 text-orange-700 dark:text-orange-300',
  studio_pilates: 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  studio_funcional: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  studio_bem_estar: 'bg-pink-500/15 text-pink-700 dark:text-pink-300',
  lutas: 'bg-red-500/15 text-red-700 dark:text-red-300',
  personal_studio: 'bg-amber-500/15 text-amber-800 dark:text-amber-200',
  aqua_fitness: 'bg-cyan-500/15 text-cyan-800 dark:text-cyan-200',
  saude_clinica: 'bg-muted text-muted-foreground line-through',
}

export interface ComposicaoSegmentoJSON {
  count: number
  pct: number
  label?: string
}

export function formatComposicaoParque(
  comp?: Record<string, ComposicaoSegmentoJSON> | null,
): string | null {
  if (!comp || Object.keys(comp).length === 0) return null
  return SEGMENTO_PARQUE_ORDER.filter((k) => comp[k]?.count)
    .map((k) => {
      const item = comp[k]!
      const label = item.label ?? SEGMENTO_PARQUE_LABELS[k] ?? k
      return `${label} ${item.pct}% (${item.count})`
    })
    .join(' · ')
}

export const CONFIANCA_HINT: Record<string, string> = {
  alta: '',
  media: '~',
  baixa: '?',
}
