import { cn } from '@/lib/utils'
import type { Icon } from '@/components/icons/gymsite-icons'
import { especialistaPorId, type EspecialistaId } from '@/config/consultor-agentes'

type ConsultorAgentAvatarProps = {
  Icone?: Icon
  especialistaId?: EspecialistaId
  isActive?: boolean
  size?: 'tile' | 'inline'
  className?: string
}

export function ConsultorAgentAvatar({
  Icone: IconeProp,
  especialistaId,
  isActive = false,
  size = 'tile',
  className,
}: ConsultorAgentAvatarProps) {
  const Icone = IconeProp ?? (especialistaId ? especialistaPorId(especialistaId)?.Icone : undefined)
  if (!Icone) return null

  const isTile = size === 'tile'

  return (
    <span
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden ring-offset-background transition-all',
        isTile ? 'h-14 w-14 rounded-lg bg-card' : 'h-8 w-8 rounded-md bg-muted/20',
        isActive && 'ring-2 ring-primary ring-offset-2',
        className,
      )}
    >
      <Icone className="h-full w-full object-contain" />
    </span>
  )
}
