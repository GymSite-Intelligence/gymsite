import { useEffect, useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Loader2, FileText, Sparkles, Plus, MessageSquare, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChatInput } from '@/components/chat/ChatInput'
import { ConsultorMessage } from '@/components/chat/ConsultorMessage'
import { ConsultorWelcomePanel } from '@/components/chat/ConsultorWelcomePanel'
import { ConsultorAgentAvatar } from '@/components/chat/ConsultorAgentAvatar'
import {
  ESPECIALISTAS,
  especialistaDaMensagem,
  especialistaPadrao,
  type Especialista,
} from '@/config/consultor-agentes'
import { cn } from '@/lib/utils'
import { apiIdFromUi } from '@/config/site-agent-map'
import type { ChatMessageData } from '@/components/chat/ChatMessage'
import type { ConsultorSessionItem } from '@/lib/consultor-sessions'

interface ConsultorChatProps {
  messages: ChatMessageData[]
  sessions: ConsultorSessionItem[]
  activeProjetoId: string | null
  sugestoes: string[]
  isLoading: boolean
  isLoadingSessions: boolean
  isGeneratingReport: boolean
  podeGerarRelatorio: boolean
  temRelatorio: boolean
  error: string | null
  onSend: (text: string, agente?: string) => void
  onGerarRelatorio: () => void
  onSelectSession: (id: string) => void
  onNewSession: () => void
  onExportJson: () => void
}

export function ConsultorChat({
  messages,
  sessions,
  activeProjetoId,
  sugestoes,
  isLoading,
  isLoadingSessions,
  isGeneratingReport,
  podeGerarRelatorio,
  temRelatorio,
  error,
  onSend,
  onGerarRelatorio,
  onSelectSession,
  onNewSession,
  onExportJson,
}: ConsultorChatProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [focado, setFocado] = useState<Especialista>(especialistaPadrao)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isLoading])

  const ultimoResponder = [...messages].reverse().find((m) => m.role === 'assistant')
  const idDestaque = ultimoResponder
    ? especialistaDaMensagem(ultimoResponder.acoes, ultimoResponder.agenteId).id
    : focado.id

  const especialistaAnterior = (index: number): Especialista | undefined => {
    for (let j = index - 1; j >= 0; j--) {
      if (messages[j].role === 'assistant') {
        return especialistaDaMensagem(messages[j].acoes, messages[j].agenteId)
      }
    }
    return undefined
  }

  const isWelcomeState =
    messages.length === 1 && messages[0].role === 'assistant' && !activeProjetoId && !isLoading

  return (
    <div className="flex min-w-0 flex-1">
      <aside className="flex w-60 shrink-0 flex-col border-r bg-muted/20">
        <div className="px-3 pb-1 pt-3">
          <span className="pl-0.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Consultores
          </span>
        </div>
        <div className="flex flex-col gap-1 px-2 pb-2">
          {ESPECIALISTAS.map((e) => {
            const destacado = e.id === idDestaque
            return (
              <button
                key={e.id}
                type="button"
                title={`${e.nome} — ${e.especialidade}`}
                aria-label={`${e.nome} — ${e.especialidade}`}
                aria-pressed={destacado}
                onClick={() => setFocado(e)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-lg border p-2 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
                  destacado
                    ? 'border-primary/25 bg-primary/5 text-primary'
                    : 'border-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground',
                )}
              >
                <ConsultorAgentAvatar Icone={e.Icone} isActive={destacado} size="tile" />
                <div className="min-w-0 flex-1">
                  <span className={cn('block text-xs font-bold', destacado ? 'text-primary' : 'text-foreground')}>
                    {e.nome}
                  </span>
                  <span className="block truncate text-[10px] leading-tight text-muted-foreground">
                    {e.especialidade}
                  </span>
                </div>
              </button>
            )
          })}
        </div>

        <div className="mx-2 h-px bg-border" />

        <div className="flex items-center justify-between px-3 py-2">
          <span className="text-xs font-semibold">Conversas</span>
          <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-[11px]" onClick={onNewSession}>
            <Plus className="h-3 w-3" />
            Nova
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {isLoadingSessions ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : sessions.length === 0 ? (
            <p className="px-2 py-4 text-center text-[11px] text-muted-foreground">
              Nenhuma conversa ainda.
              <br />
              Inicie uma nova análise.
            </p>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition-colors',
                    activeProjetoId === session.id
                      ? 'bg-primary/10 text-primary'
                      : 'text-foreground/80 hover:bg-muted',
                  )}
                >
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                  <span className="flex-1 truncate">{session.title || 'Nova conversa'}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="mx-2 mb-2 rounded-xl border bg-card p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              Bases oficiais
            </span>
          </div>
          <p className="text-[10px] leading-relaxed text-muted-foreground">
            +27 fontes catalogadas (IBGE, CREF, mapas públicos). Respostas com carimbo de fonte e janela.
          </p>
        </div>

        <div className="space-y-1.5 border-t p-2">
          <Button variant="outline" size="sm" className="h-8 w-full gap-1.5 text-xs" asChild>
            <Link to="/relatorios/new">
              <FileText className="h-3.5 w-3.5" />
              Novo relatório
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-full gap-1.5 text-xs text-muted-foreground"
            onClick={onExportJson}
            disabled={!activeProjetoId && messages.length <= 1}
          >
            <Download className="h-3.5 w-3.5" />
            Exportar JSON
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
          {isWelcomeState ? (
            <ConsultorWelcomePanel
              especialista={focado}
              onSend={(text) => onSend(text, apiIdFromUi(focado.id))}
            />
          ) : (
            <div className="mx-auto max-w-3xl space-y-3">
              {messages.map((msg, i) => (
                <ConsultorMessage key={msg.id} msg={msg} especialistaAnterior={especialistaAnterior(i)} />
              ))}
              {isLoading && messages[messages.length - 1]?.role === 'user' && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="flex gap-1">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                    <span className="h-2 w-2 animate-pulse rounded-full bg-primary [animation-delay:150ms]" />
                    <span className="h-2 w-2 animate-pulse rounded-full bg-primary [animation-delay:300ms]" />
                  </span>
                  Pesquisando bases públicas… (pode levar 1-3 min)
                </div>
              )}
            </div>
          )}
        </div>

        {!isLoading && sugestoes.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t px-4 py-2 sm:px-6">
            {sugestoes.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSend(s, apiIdFromUi(focado.id))}
                className="rounded-full border border-primary/40 px-3 py-1 text-xs text-foreground outline-none transition-colors hover:bg-primary/10 hover:text-primary focus-visible:ring-2 focus-visible:ring-ring"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {podeGerarRelatorio && !temRelatorio && (
          <div className="flex items-center gap-2 border-t bg-primary/10 px-4 py-2 text-xs text-foreground sm:px-6">
            <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
            <span className="flex-1">Dados suficientes para o Relatório Formal de Viabilidade.</span>
            <Button size="sm" className="h-7 gap-1 text-xs" disabled={isGeneratingReport} onClick={onGerarRelatorio}>
              {isGeneratingReport ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FileText className="h-3.5 w-3.5" />
              )}
              Gerar relatório
            </Button>
          </div>
        )}

        {error && (
          <div className="border-t border-destructive/30 bg-destructive/10 px-4 py-2 text-center text-xs text-destructive sm:px-6">
            {error}
          </div>
        )}

        <ChatInput
          onSend={(text) => onSend(text, apiIdFromUi(focado.id))}
          isLoading={isLoading}
          placeholder={focado.placeholder}
        />
      </div>
    </div>
  )
}
