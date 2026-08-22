import { useEffect, useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Loader2, Plus, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChatInput } from '@/components/chat/ChatInput'
import { ConsultorMessage } from '@/components/chat/ConsultorMessage'
import { ConsultorWelcomePanel } from '@/components/chat/ConsultorWelcomePanel'
import { ConsultorAgentAvatar } from '@/components/chat/ConsultorAgentAvatar'
import { ChatMiniCard } from '@/components/chat/ChatMiniCard'
import { AGENT_ICONS } from '@/components/icons/gymsite-icons'
import {
  ESPECIALISTAS,
  especialistaDaMensagem,
  especialistaPadrao,
  type Especialista,
} from '@/config/consultor-agentes'
import { CONSULTOR_COPY } from '@/config/gymsite-design-system'
import { cn } from '@/lib/utils'
import { apiIdFromUi } from '@/config/site-agent-map'
import type { ChatMessageData } from '@/components/chat/ChatMessage'
import type { ConsultorSessionItem } from '@/lib/consultor-sessions'

const IconeRelatorio = AGENT_ICONS.marketing_report_writer

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

  const especialistaAtivo = ESPECIALISTAS.find((e) => e.id === idDestaque) ?? focado

  return (
    <div className="flex min-w-0 flex-1">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
            {CONSULTOR_COPY.tagline}
          </span>
          <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
            {CONSULTOR_COPY.subtitle}
          </p>
        </div>

        <div className="px-3 pb-2 pt-3">
          <span className="pl-0.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Consultores
          </span>
        </div>
        <div className="flex flex-col gap-1 px-2 pb-3">
          {ESPECIALISTAS.map((e) => {
            const destacado = e.id === idDestaque
            const selecionado = e.id === focado.id
            return (
              <button
                key={e.id}
                type="button"
                title={`${e.nome} — ${e.especialidade}`}
                aria-label={`${e.nome} — ${e.especialidade}`}
                aria-pressed={selecionado}
                onClick={() => setFocado(e)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-xl border p-2 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
                  destacado
                    ? 'border-primary/30 bg-primary/5'
                    : 'border-border/50 bg-background/40 hover:border-border hover:bg-card',
                )}
              >
                <ConsultorAgentAvatar
                  Icone={e.Icone}
                  imgSrc={e.img}
                  isActive={destacado}
                  size="rail"
                />
                <div className="min-w-0 flex-1">
                  <span
                    className={cn(
                      'block text-xs font-bold',
                      destacado ? 'text-primary' : 'text-foreground',
                    )}
                  >
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

        <div className="mx-3 h-px bg-border" />

        <div className="flex items-center justify-between px-3 py-2.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Conversas
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 px-2 text-[11px] text-primary hover:text-primary"
            onClick={onNewSession}
          >
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
            <p className="px-2 py-4 text-center text-[11px] leading-relaxed text-muted-foreground">
              Nenhuma conversa ainda.
              <br />
              Inicie uma nova análise.
            </p>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((session) => {
                const ativa = activeProjetoId === session.id
                return (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => onSelectSession(session.id)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-xs transition-colors',
                      ativa
                        ? 'border-primary/30 bg-primary/5 text-primary'
                        : 'border-transparent text-foreground/80 hover:border-border/60 hover:bg-background/60',
                    )}
                  >
                    <span
                      className={cn(
                        'h-1.5 w-1.5 shrink-0 rounded-full',
                        ativa ? 'bg-primary' : 'bg-muted-foreground/40',
                      )}
                      aria-hidden
                    />
                    <span className="flex-1 truncate">{session.title || 'Nova conversa'}</span>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="mx-2 mb-2">
          <ChatMiniCard
            kicker={CONSULTOR_COPY.basesOficiais.kicker}
            detail={CONSULTOR_COPY.basesOficiais.detail}
          />
        </div>

        <div className="space-y-1.5 border-t border-border p-2">
          <Button variant="outline" size="sm" className="h-8 w-full gap-2 text-xs" asChild>
            <Link to="/explorar" search={{ novo: true }}>
              <IconeRelatorio className="h-4 w-4 shrink-0" />
              Novo relatório
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-full gap-2 text-xs text-muted-foreground"
            onClick={onExportJson}
            disabled={!activeProjetoId && messages.length <= 1}
          >
            <Download className="h-3.5 w-3.5 shrink-0" />
            Exportar JSON
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col bg-background">
        {!isWelcomeState && (
          <div className="flex items-center gap-2.5 border-b border-border bg-card px-4 py-2.5 sm:px-6">
            <ConsultorAgentAvatar
              Icone={especialistaAtivo.Icone}
              imgSrc={especialistaAtivo.img}
              isActive
              size="inline"
            />
            <div className="min-w-0">
              <p className="text-xs font-semibold text-foreground">{especialistaAtivo.nome}</p>
              <p className="truncate text-[10px] text-muted-foreground">{especialistaAtivo.especialidade}</p>
            </div>
          </div>
        )}

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
                <div className="flex items-center gap-2.5 text-xs text-muted-foreground">
                  <ConsultorAgentAvatar
                    Icone={focado.Icone}
                    imgSrc={focado.img}
                    isActive
                    size="inline"
                  />
                  <span className="flex items-center gap-2">
                    <span className="flex gap-1">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:150ms]" />
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:300ms]" />
                    </span>
                    Pesquisando bases públicas… (pode levar 1-3 min)
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {!isLoading && sugestoes.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t border-border px-4 py-2 sm:px-6">
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
          <div className="flex items-center gap-2 border-t border-primary/20 bg-primary/10 px-4 py-2.5 text-xs text-foreground sm:px-6">
            <IconeRelatorio className="h-4 w-4 shrink-0 text-primary" aria-hidden />
            <span className="flex-1">Dados suficientes para o Relatório Formal de Viabilidade.</span>
            <Button
              size="sm"
              className="h-7 gap-1.5 text-xs"
              disabled={isGeneratingReport}
              onClick={onGerarRelatorio}
            >
              {isGeneratingReport ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <IconeRelatorio className="h-3.5 w-3.5" />
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
