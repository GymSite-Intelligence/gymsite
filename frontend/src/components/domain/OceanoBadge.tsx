import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { normalizeVereditoOceano, OCEANO_CONFIG } from '@/lib/oceano'
import type { VereditoOceano } from '@/types/domain'

export function OceanoBadge({
  veredito,
  className,
  compact,
}: {
  veredito: VereditoOceano | string | null | undefined
  className?: string
  compact?: boolean
}) {
  const key = normalizeVereditoOceano(
    typeof veredito === 'string' ? veredito : veredito ?? undefined,
  )
  if (!key) {
    return (
      <Badge variant="outline" className={cn('font-normal text-muted-foreground', className)}>
        {compact ? '—' : 'Sem posicionamento'}
      </Badge>
    )
  }
  const cfg = OCEANO_CONFIG[key]
  return (
    <Badge
      className={cn(
        'gap-1 border-transparent font-semibold',
        cfg.bg,
        cfg.text,
        className,
      )}
    >
      <span aria-hidden>{cfg.emoji}</span>
      {compact ? cfg.emoji : cfg.label}
    </Badge>
  )
}
