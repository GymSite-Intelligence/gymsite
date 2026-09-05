import { cn } from '@/lib/utils'

interface ChatMiniCardProps {
  kicker: string
  detail: string
  className?: string
}

export function ChatMiniCard({ kicker, detail, className }: ChatMiniCardProps) {
  return (
    <div className={cn('rounded-xl border border-border/60 bg-card p-3 text-left', className)}>
      <span className="mb-0.5 block text-xs font-bold text-lime">{kicker}</span>
      <span className="block text-[10px] leading-snug text-muted-foreground">{detail}</span>
    </div>
  )
}
