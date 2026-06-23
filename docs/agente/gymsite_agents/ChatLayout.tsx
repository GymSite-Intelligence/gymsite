// ============================================================
// ChatLayout.tsx — ATUALIZADO com Handoff Badge (Swarm-style)
// GymSite Intelligence v2.1 — 5 Setores
//
// FIXES aplicados:
//  - useState importado (estava faltando)
//  - motion + AnimatePresence importados do framer-motion
//  - cn importado de @/lib/utils
//  - pipelineEvent (singular) em vez de array — evita re-dispatch de eventos antigos
// ============================================================

import { useRef, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, Loader2, PanelRight } from 'lucide-react'
import { cn } from '@/lib/utils'

import { ChatMessage, type ChatMessageData } from './ChatMessage'
import { ChatInput, type ChatAttachment } from './ChatInput'
import { ChatSidebarDesktop, ChatSidebarMobile, type ChatSessionItem } from './ChatSidebar'
import { Button } from '@/components/ui/button'

import { HandoffBadge } from '@/components/handoff/HandoffBadge'
import { HandoffTimeline } from '@/components/handoff/HandoffTimeline'
import { useHandoff } from '@/hooks/useHandoff'
import { SETORES, AGENTES_PIPELINE } from '@/config/handoff'
import type { HandoffEvent } from '@/types/handoff'

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

  // FIX: era pipelineEvents (array) — causava re-dispatch de TODOS os eventos a cada render.
  //      Agora é pipelineEvent (singular, o evento mais recente) — cada evento é processado
  //      uma única vez quando chega via WebSocket/SSE.
  pipelineEvent?: HandoffEvent | null
  pipelineRunning?: boolean
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
  pipelineEvent = null,
  pipelineRunning = false,
}: ChatLayoutProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showTimeline, setShowTimeline] = useState(false)

  const { state: handoffState, dispatchHandoff, reset: resetHandoff } = useHandoff({
    duracaoEntrada: 600,
    duracaoSaida: 300,
    tempoMinimoVisivel: 1200,
  })

  // FIX: processa apenas o evento mais recente (não o array inteiro).
  // O componente pai (ex: usePipeline hook) mantém sempre o último evento
  // recebido via WebSocket e passa como pipelineEvent.
  // A referência garante que o mesmo evento não seja processado duas vezes.
  const lastEventRef = useRef<HandoffEvent | null>(null)

  useEffect(() => {
    if (!pipelineRunning) {
      resetHandoff()
      lastEventRef.current = null
      return
    }

    if (!pipelineEvent) return

    // Evita re-processar o mesmo evento se o componente re-renderizar
    const isMesmoEvento =
      lastEventRef.current?.toAgenteId === pipelineEvent.toAgenteId &&
      lastEventRef.current?.tipo === pipelineEvent.tipo

    if (isMesmoEvento) return

    lastEventRef.current = pipelineEvent
    dispatchHandoff(pipelineEvent)
  }, [pipelineEvent, pipelineRunning, dispatchHandoff, resetHandoff])

  // Scroll automático
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

      <div className="flex flex-1 flex-col">
        {/* ========== HEADER ========== */}
        <header className="flex h-14 items-center gap-3 border-b px-4 sm:px-6">
          <ChatSidebarMobile
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={onSelectSession}
            onNewSession={onNewSession}
          />

          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-semibold leading-tight">GymSite Agent</h1>
              <p className="text-[10px] text-muted-foreground">Especialista em franquias de fitness</p>
            </div>
          </div>

          {/* Handoff Badge — centro do header */}
          <div className="flex flex-1 items-center justify-center">
            <AnimatePresence mode="wait">
              {pipelineRunning ? (
                <motion.div
                  key="badge-ativo"
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                >
                  <HandoffBadge
                    state={handoffState}
                    agentes={AGENTES_PIPELINE}
                    setores={SETORES}
                    onAgenteClick={() => setShowTimeline(true)}
                  />
                </motion.div>
              ) : (
                <motion.span
                  key="badge-idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-[11px] text-muted-foreground/40"
                >
                  Pronto para análise
                </motion.span>
              )}
            </AnimatePresence>
          </div>

          {/* Botões direita */}
          <div className="ml-auto flex items-center gap-2">
            {pipelineRunning && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setShowTimeline((v) => !v)}
                title="Ver pipeline completo"
              >
                <PanelRight className="h-4 w-4" />
              </Button>
            )}
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

        {/* ========== ÁREA DE MENSAGENS + TIMELINE ========== */}
        <div className="flex flex-1 overflow-hidden">
          {/* Mensagens */}
          <div
            ref={scrollRef}
            className={cn(
              'flex-1 overflow-y-auto transition-all duration-300',
              showTimeline && pipelineRunning && 'max-w-[calc(100%-280px)]'
            )}
          >
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center px-4 text-center">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  <Bot className="h-6 w-6" />
                </div>
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
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 sm:h-8 sm:w-8">
                      <Bot className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span className="text-xs">Analisando...</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Timeline lateral */}
          <AnimatePresence>
            {showTimeline && pipelineRunning && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 280, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className="overflow-hidden border-l bg-muted/20"
              >
                <div className="h-full overflow-y-auto p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Pipeline
                    </h3>
                    <span className="text-[10px] text-muted-foreground">
                      {AGENTES_PIPELINE.find((a) => a.id === handoffState.agenteAtivoId)?.nome || '...'}
                    </span>
                  </div>
                  <HandoffTimeline
                    agentes={AGENTES_PIPELINE}
                    setores={SETORES}
                    state={handoffState}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Error */}
        {error && (
          <div className="border-t bg-red-50 px-4 py-2 text-center text-xs text-red-700 sm:px-6">
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
