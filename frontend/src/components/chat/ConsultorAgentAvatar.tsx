import { AgentAvatar } from '@/components/chat/AgentAvatar'
import type { Icon } from '@/components/icons/gymsite-icons'
import { especialistaPorId, type EspecialistaId } from '@/config/consultor-agentes'

type ConsultorAgentAvatarProps = {
  Icone?: Icon
  especialistaId?: EspecialistaId
  isActive?: boolean
  size?: 'rail' | 'inline' | 'hero'
  className?: string
}

const SIZE_MAP = {
  rail: 'md',
  inline: 'sm',
  hero: 'xl',
} as const

export function ConsultorAgentAvatar({
  Icone: IconeProp,
  especialistaId,
  isActive = false,
  size = 'rail',
  className,
}: ConsultorAgentAvatarProps) {
  const Icone = IconeProp ?? (especialistaId ? especialistaPorId(especialistaId)?.Icone : undefined)
  if (!Icone) return null

  return (
    <AgentAvatar
      Icone={Icone}
      size={SIZE_MAP[size]}
      active={isActive}
      className={className}
    />
  )
}
