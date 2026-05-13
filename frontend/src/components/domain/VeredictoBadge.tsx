/**
 * VeredictoBadge — exibe o veredito de um relatório com cor semântica.
 *
 * Os 4 valores possíveis vêm do A6 ReportConsolidator e refletem a
 * classificação baseada no score_top1_candidato (schema v1.1):
 *   8.0-10.0 → APROVADO
 *   6.0-7.9  → APROVADO COM RESSALVAS
 *   4.0-5.9  → INVESTIGAR MAIS
 *   < 4.0    → REPROVADO
 */
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Veredito } from '@/types/domain'

const VEREDITO_CONFIG: Record<
  Veredito,
  { label: string; emoji: string; bg: string; text: string }
> = {
  APROVADO: {
    label: 'APROVADO',
    emoji: '✅',
    bg: 'bg-veredito-aprovado',
    text: 'text-white',
  },
  'APROVADO COM RESSALVAS': {
    label: 'COM RESSALVAS',
    emoji: '⚠️',
    bg: 'bg-veredito-ressalvas',
    text: 'text-black',
  },
  'INVESTIGAR MAIS': {
    label: 'INVESTIGAR',
    emoji: '🔍',
    bg: 'bg-veredito-investigar',
    text: 'text-white',
  },
  REPROVADO: {
    label: 'REPROVADO',
    emoji: '❌',
    bg: 'bg-veredito-reprovado',
    text: 'text-white',
  },
}

export interface VeredictoBadgeProps {
  veredito: Veredito
  showEmoji?: boolean
  size?: 'sm' | 'md'
  className?: string
}

export function VeredictoBadge({
  veredito,
  showEmoji = true,
  size = 'md',
  className,
}: VeredictoBadgeProps) {
  const cfg = VEREDITO_CONFIG[veredito]
  if (!cfg) return null

  return (
    <Badge
      className={cn(
        'border-transparent gap-1.5 font-semibold tracking-wide',
        cfg.bg,
        cfg.text,
        size === 'sm' && 'text-[10px] px-1.5 py-0',
        size === 'md' && 'text-xs px-2 py-0.5',
        className,
      )}
      role="status"
      aria-label={`Veredito: ${cfg.label}`}
    >
      {showEmoji && <span aria-hidden>{cfg.emoji}</span>}
      <span>{cfg.label}</span>
    </Badge>
  )
}
