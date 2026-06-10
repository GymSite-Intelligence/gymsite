import { useState } from 'react'
import { Plus, MessageSquare, Trash2, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'

export interface ChatSessionItem {
  id: string
  title: string
  updatedAt: string
  status: string
}

interface ChatSidebarProps {
  sessions: ChatSessionItem[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onNewSession: () => void
  onDeleteSession?: (id: string) => void
}

function SessionList({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
}: ChatSidebarProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-3 py-3">
        <span className="text-sm font-semibold">Conversas</span>
        <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" onClick={onNewSession}>
          <Plus className="h-3.5 w-3.5" />
          Nova
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 ? (
          <div className="px-4 py-8 text-center text-xs text-muted-foreground">
            Nenhuma conversa ainda.
            <br />
            Inicie uma nova análise.
          </div>
        ) : (
          <div className="space-y-0.5 px-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={`group flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                  activeSessionId === session.id
                    ? 'bg-primary/10 text-primary'
                    : 'text-foreground/80 hover:bg-muted'
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                <span className="flex-1 truncate">{session.title || 'Nova conversa'}</span>
                {onDeleteSession && (
                  <span
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteSession(session.id)
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function ChatSidebarDesktop(props: ChatSidebarProps) {
  return (
    <aside className="hidden w-[260px] shrink-0 border-r bg-muted/20 md:block">
      <SessionList {...props} />
    </aside>
  )
}

export function ChatSidebarMobile(props: ChatSidebarProps) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[280px] p-0">
        <SessionList {...props} />
      </SheetContent>
    </Sheet>
  )
}
