import { useRef, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { ChatMessage, type ChatMessageData } from './ChatMessage'
import { ChatInput, type ChatAttachment } from './ChatInput'
import { ChatSidebarDesktop, ChatSidebarMobile, type ChatSessionItem } from './ChatSidebar'
import { AgentAvatar } from '@/components/chat/AgentAvatar'
import { Button } from '@/components/ui/button'
import { ICONE_CONSULTOR } from '@/config/agentes'

interface ChatLayoutProps {
  messages: ChatMessageData[]
  sessions: ChatSessionItem[]
  activeSessionId: string | null
  isLoading: boolean
  error: string | null
  onSendMessage: (text: string, attachments?: ChatAttachment[]) => void
  onNewSession: () => void
  onSelectSession: (id: string) => void
  onRegenerate?: (msgId: string) => void
  onFeedback?: (interacaoId: string, rating: 1 | -1) => Promise<boolean>
}

export function ChatLayout({
  messages,
  sessions,
  activeSessionId,
  isLoading,
  error,
  onSendMessage,
  onNewSession,
  onSelectSession,
  onRegenerate,
  onFeedback,
}: ChatLayoutProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full overflow-hidden">
      {/* Sidebar Desktop */}
      <ChatSidebarDesktop
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={onSelectSession}
        onNewSession={onNewSession}
      />

      {/* Área principal */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex h-14 items-center gap-3 border-b px-4 sm:px-6">
          <ChatSidebarMobile
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={onSelectSession}
            onNewSession={onNewSession}
          />
          <div className="flex items-center gap-2">
          <AgentAvatar Icone={ICONE_CONSULTOR} size="sm" />
            <div>
              <h1 className="text-sm font-semibold leading-tight">GymSite Agent</h1>
              <p className="text-[10px] text-muted-foreground">Especialista em franquias de fitness</p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="hidden h-8 gap-1 text-xs sm:flex"
              onClick={onNewSession}
            >
              Nova conversa
            </Button>
          </div>
        </header>

        {/* Mensagens */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center px-4 text-center">
              <AgentAvatar Icone={ICONE_CONSULTOR} size="lg" className="mb-4" />
              <h2 className="mb-1 text-lg font-semibold">Como posso ajudar?</h2>
              <p className="max-w-sm text-sm text-muted-foreground">
                Sou seu especialista em expansão de franquias de academia. Me diga a cidade e
                bairro que eu preparo uma análise completa de viabilidade.
              </p>
            </div>
          ) : (
            <div className="pb-2">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  msg={msg}
                  onRegenerate={onRegenerate ? () => onRegenerate(msg.id) : undefined}
                  onFeedback={onFeedback}
                />
              ))}
              {isLoading && messages[messages.length - 1]?.role === 'user' && (
                <div className="flex gap-3 px-4 py-5 sm:px-6 lg:px-8">
                <AgentAvatar Icone={ICONE_CONSULTOR} size="md" />
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span className="text-xs">Analisando...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="border-t border-destructive/30 bg-destructive/10 px-4 py-2 text-center text-xs text-destructive sm:px-6">
            {error}
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={onSendMessage}
          isLoading={isLoading}
          placeholder="Mensagem GymSite Agent..."
        />
      </div>
    </div>
  )
}
