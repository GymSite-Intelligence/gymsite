import { useEffect, useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Download, Loader2, PanelLeft, PanelRight, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ConsultorMessage } from '@/components/chat/ConsultorMessage'
import { ConsultorWelcomePanel } from '@/components/chat/ConsultorWelcomePanel'
import { ConsultorProjetoAside } from '@/components/chat/ConsultorProjetoAside'
import { ChatMiniCard } from '@/components/chat/ChatMiniCard'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
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
import { useMediaQuery } from '@/hooks/use-media-query'
import type { ChatMessageData } from '@/components/chat/ChatMessage'
import type { ConsultorProjeto } from '@/hooks/useConsultorChat'
import type { ConsultorSessionItem } from '@/lib/consultor-sessions'

const IconeRelatorio = AGENT_ICONS.marketing_report_writer

interface ConsultorChatProps {
  messages: ChatMessageData[]
  sessions: ConsultorSessionItem[]
  activeProjetoId: string | null
  projeto: ConsultorProjeto | null
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
  projeto,
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
  const [input, setInput] = useState('')
  const [focado, setFocado] = useState<Especialista>(especialistaPadrao)
  const [agentsCollapsed, setAgentsCollapsed] = useState(false)
  const [projetoCollapsed, setProjetoCollapsed] = useState(true)
  const [agentsSheetOpen, setAgentsSheetOpen] = useState(false)
  const [projetoSheetOpen, setProjetoSheetOpen] = useState(false)
  const isLg = useMediaQuery('(min-width: 1024px)')
  const isXl = useMediaQuery('(min-width: 1280px)')

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

  const selectAgente = (e: Especialista) => {
    setFocado(e)
    setAgentsSheetOpen(false)
  }

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
                    ? 'border-primary bg-elevated'
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
                      'h-1.5 w-1.5 shrink-0 rounded-full',
                      ativa ? 'bg-lime' : 'bg-muted-foreground/40',
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
    </>
  )

  return (
    <div className="flex min-w-0 flex-1">
      {!agentsCollapsed && (
        <aside
          id="sidebar-consultor-especialistas"
          className="hidden w-56 shrink-0 flex-col border-r border-border bg-card lg:flex xl:w-60"
        >
          {sidebarContent}
        </aside>
      )}

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
                        ? 'border-primary bg-elevated text-foreground'
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

          <span className="min-w-0 flex-1 truncate text-center text-[11px] text-muted-foreground sm:text-xs">
            {especialistaAtivo.especialidade}
          </span>

          <button
            type="button"
            onClick={() => {
              if (isXl) setProjetoCollapsed((v) => !v)
              else setProjetoSheetOpen(true)
            }}
            className={cn(
              'inline-flex h-9 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition',
              isXl && !projetoCollapsed
                ? 'border-lime/30 bg-lime/10 text-lime'
                : 'border-border bg-background text-foreground hover:bg-accent',
            )}
            aria-expanded={isXl ? !projetoCollapsed : projetoSheetOpen}
            aria-controls={isXl ? 'sidebar-consultor-projeto' : 'sidebar-consultor-projeto-sheet'}
          >
            <span className="hidden sm:inline">Projeto</span>
            <PanelRight className="h-4 w-4 shrink-0 text-lime" aria-hidden />
          </button>
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

        <div
          ref={scrollRef}
          className="flex-1 space-y-3 overflow-y-auto bg-background px-3 py-3 sm:px-5 sm:py-4"
        >
          {isWelcomeState ? (
            <ConsultorWelcomePanel
              especialista={focado}
              onSend={(text) => onSend(text, apiIdFromUi(focado.id))}
            />
          ) : (
            <>
              {messages.map((msg, i) => (
                <ConsultorMessage key={msg.id} msg={msg} especialistaAnterior={especialistaAnterior(i)} />
              ))}
              {isLoading && messages[messages.length - 1]?.role === 'user' && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 rounded-lg bg-secondary px-3 py-2 text-sm text-muted-foreground">
                    <span className="flex gap-1">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-lime" />
                      <span className="h-2 w-2 animate-pulse rounded-full bg-lime [animation-delay:150ms]" />
                      <span className="h-2 w-2 animate-pulse rounded-full bg-lime [animation-delay:300ms]" />
                    </span>
                    Pesquisando bases públicas… (pode levar 1-3 min)
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {!isLoading && sugestoes.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t border-border px-3 py-2 sm:px-5">
            {sugestoes.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSend(s, apiIdFromUi(focado.id))}
                className="rounded-full border border-lime/40 px-3 py-1 text-xs text-foreground hover:bg-lime/10 hover:text-lime disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {podeGerarRelatorio && !temRelatorio && (
          <div className="border-t border-border bg-lime/5 p-3 text-center">
            <p className="mb-2 text-xs text-muted-foreground">
              Dados suficientes para o{' '}
              <span className="font-medium text-foreground">Relatório Formal de Viabilidade</span>.
            </p>
            <button
              type="button"
              disabled={isGeneratingReport}
              onClick={onGerarRelatorio}
              className="inline-flex items-center gap-1.5 rounded-md bg-lime px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-lime-glow disabled:opacity-50"
            >
              {isGeneratingReport ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <IconeRelatorio className="h-4 w-4" />
              )}
              Gerar relatório
            </button>
          </div>
        )}

        {error && (
          <div className="border-t border-destructive/30 bg-destructive/10 px-3 py-2 text-center text-xs text-destructive sm:px-5">
            {error}
          </div>
        )}

        <form
          onSubmit={submit}
          className="flex gap-2 border-t border-border bg-card p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] sm:p-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={focado.placeholder}
            disabled={isLoading}
            className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="shrink-0 rounded-md bg-lime px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-lime-glow disabled:opacity-50 sm:px-4"
          >
            Enviar
          </button>
        </form>
      </div>

      {!projetoCollapsed && (
        <aside
          id="sidebar-consultor-projeto"
          className="hidden w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border bg-muted/20 p-4 xl:flex"
        >
          <ConsultorProjetoAside projeto={projeto} />
        </aside>
      )}

      <Sheet open={agentsSheetOpen} onOpenChange={setAgentsSheetOpen}>
        <SheetContent
          id="sidebar-consultor-especialistas-sheet"
          side="left"
          className="flex w-[min(100%,18rem)] flex-col border-border bg-card p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Especialistas</SheetTitle>
            <SheetDescription>
              Tema sugerido — o especialista certo assume conforme sua pergunta.
            </SheetDescription>
          </SheetHeader>
          <div className="flex min-h-0 flex-1 flex-col pt-2">{sidebarContent}</div>
        </SheetContent>
      </Sheet>

      <Sheet open={projetoSheetOpen} onOpenChange={setProjetoSheetOpen}>
        <SheetContent
          id="sidebar-consultor-projeto-sheet"
          side="right"
          className="flex w-[min(100%,20rem)] flex-col gap-3 overflow-y-auto border-border bg-muted/20 p-4 pt-12"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Projeto</SheetTitle>
            <SheetDescription>Localização, pesquisas e status do relatório.</SheetDescription>
          </SheetHeader>
          <ConsultorProjetoAside projeto={projeto} />
        </SheetContent>
      </Sheet>
    </div>
  )
}
