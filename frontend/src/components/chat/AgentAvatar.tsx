import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import type { Icon } from '@/components/icons/gymsite-icons'

type AgentAvatarProps = {
  Icone: Icon
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

export function AgentAvatar({ Icone, size = 'md', active = false, className }: AgentAvatarProps) {
  return (
    <Avatar
      className={cn(
        SIZE_CLASS[size],
        'shrink-0',
        active && 'ring-2 ring-primary shadow-sm',
        className,
      )}
    >
      <AvatarFallback className="overflow-hidden bg-primary/10 p-0.5">
        <Icone className="h-full w-full object-contain" />
      </AvatarFallback>
    </Avatar>
  )
}
