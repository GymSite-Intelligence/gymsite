import { AgentAvatar } from '@/components/chat/AgentAvatar'
import type { Icon } from '@/components/icons/gymsite-icons'
import { ESPECIALISTA_IMG, especialistaPorId, type EspecialistaId } from '@/config/consultor-agentes'

type ConsultorAgentAvatarProps = {
  Icone?: Icon
  /** Se omitido e `especialistaId`/`imgSrc` ausentes, cai no SVG. */
  imgSrc?: string
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
  imgSrc: imgSrcProp,
  especialistaId,
  isActive = false,
  size = 'rail',
  className,
}: ConsultorAgentAvatarProps) {
  const esp = especialistaId ? especialistaPorId(especialistaId) : undefined
  const Icone = IconeProp ?? esp?.Icone
  const imgSrc = imgSrcProp ?? esp?.img ?? (especialistaId ? ESPECIALISTA_IMG[especialistaId] : undefined)

  if (!Icone && !imgSrc) return null

  return (
    <AgentAvatar
      Icone={Icone}
      imgSrc={imgSrc}
      alt={esp?.nome ?? ''}
      size={SIZE_MAP[size]}
      active={isActive}
      className={className}
    />
  )
}
