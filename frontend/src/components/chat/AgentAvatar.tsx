import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import type { Icon } from '@/components/icons/gymsite-icons'

type AgentAvatarProps = {
  Icone: Icon
  size?: 'sm' | 'md' | 'lg'
  active?: boolean
  className?: string
}

const SIZE_CLASS = {
  sm: 'h-8 w-8',
  md: 'h-7 w-7 sm:h-8 sm:w-8',
  lg: 'h-10 w-10',
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
