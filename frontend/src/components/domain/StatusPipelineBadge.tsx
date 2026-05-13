/**
 * StatusPipelineBadge — mostra o status atual do pipeline (queued, running,
 * done, failed, cancelled). `running` recebe animação pulse pra indicar
 * trabalho em andamento.
 */
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { RelatorioStatus } from '@/types/domain'

const CONFIG: Record<
  RelatorioStatus,
  { label: string; bg: string; emoji: string; animate?: boolean }
> = {
  queued: { label: 'na fila', bg: 'bg-muted-foreground/20', emoji: '⏳' },
  running: {
    label: 'rodando',
    bg: 'bg-veredito-investigar',
    emoji: '⚙️',
    animate: true,
  },
  done: { label: 'pronto', bg: 'bg-veredito-aprovado', emoji: '✓' },
  failed: { label: 'falhou', bg: 'bg-veredito-reprovado', emoji: '⚠' },
  cancelled: { label: 'cancelado', bg: 'bg-muted-foreground/30', emoji: '⊘' },
}

export interface StatusPipelineBadgeProps {
  status: RelatorioStatus
  className?: string
}

export function StatusPipelineBadge({ status, className }: StatusPipelineBadgeProps) {
  const cfg = CONFIG[status]
  return (
    <Badge
      className={cn(
        'border-transparent text-white gap-1 text-[10px] px-1.5 py-0',
        cfg.bg,
        cfg.animate && 'animate-pulse',
        className,
      )}
      aria-label={`Status: ${cfg.label}`}
    >
      <span aria-hidden>{cfg.emoji}</span>
      <span>{cfg.label}</span>
    </Badge>
  )
}
