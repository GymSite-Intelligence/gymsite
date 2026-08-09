import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import type { Icon } from '@/components/icons/gymsite-icons'

type AgentAvatarProps = {
  /** Fallback line-art (pipeline). Prefer `imgSrc` para os 5 especialistas (marca). */
  Icone?: Icon
  /** Mascote PNG canônico — `/agentes/{id}.png` (mesmo do site). */
  imgSrc?: string
  alt?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  active?: boolean
  className?: string
}

const SIZE_CLASS = {
  sm: 'h-8 w-8',
  md: 'h-9 w-9',
  lg: 'h-11 w-11',
  xl: 'h-16 w-16',
} as const

export function AgentAvatar({
  Icone,
  imgSrc,
  alt = '',
  size = 'md',
  active = false,
  className,
}: AgentAvatarProps) {
  return (
    <Avatar
      className={cn(
        SIZE_CLASS[size],
        'shrink-0 border border-primary/35',
        active && 'border-primary ring-2 ring-primary/80 shadow-sm',
        className,
      )}
    >
      {imgSrc ? (
        <AvatarImage src={imgSrc} alt={alt} className="object-cover" />
      ) : null}
      <AvatarFallback className="overflow-hidden bg-primary/10 p-0.5">
        {Icone ? <Icone className="h-full w-full object-contain" /> : null}
      </AvatarFallback>
    </Avatar>
  )
}
