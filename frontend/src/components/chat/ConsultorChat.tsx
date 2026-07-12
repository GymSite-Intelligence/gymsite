import { useEffect, useRef, useState } from 'react'
import { Loader2, FileText, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChatInput } from '@/components/chat/ChatInput'
import { ConsultorMessage } from '@/components/chat/ConsultorMessage'
import {
  ESPECIALISTAS,
  especialistaDaMensagem,
  especialistaPadrao,
  type Especialista,
} from '@/config/consultor-agentes'
import { cn } from '@/lib/utils'
import type { ChatMessageData } from '@/components/chat/ChatMessage'

interface ConsultorChatProps {
  messages: ChatMessageData[]
  sugestoes: string[]
  isLoading: boolean
  isGeneratingReport: boolean
  podeGerarRelatorio: boolean
  temRelatorio: boolean
  error: string | null
  onSend: (text: string) => void
  onGerarRelatorio: () => void
}

export function ConsultorChat({
  messages,
  sugestoes,
  isLoading,
  isGeneratingReport,
  podeGerarRelatorio,
  temRelatorio,
  error,
  onSend,
  onGerarRelatorio,
}: ConsultorChatProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [focado, setFocado] = useState<Especialista>(especialistaPadrao)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isLoading])

  const ultimoResponder = [...messages].reverse().find((m) => m.role === 'assistant')
  const idDestaque = ultimoResponder ? especialistaDaMensagem(ultimoResponder.acoes).id : focado.id

  const especialistaAnterior = (index: number): Especialista | undefined => {
    for (let j = index - 1; j >= 0; j--) {
      if (messages[j].role === 'assistant') return especialistaDaMensagem(messages[j].acoes)
    }
    return undefined
  }

  return (
    <div className="flex min-w-0 flex-1">
      <div className="flex w-14 shrink-0 flex-col items-center gap-1 border-r bg-muted/20 py-3 sm:w-16">
        {ESPECIALISTAS.map((e) => {
          const destacado = e.id === idDestaque
          const Icone = e.Icone
          return (
            <button
              key={e.id}
              type="button"
              title={`${e.nome} — ${e.especialidade}`}
              aria-label={`${e.nome} — ${e.especialidade}`}
              aria-pressed={destacado}
              onClick={() => setFocado(e)}
              className={cn(
                'flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
                destacado ? 'bg-primary/15 text-primary' : 'text-muted-foreground hover:bg-accent',
              )}
            >
              <span className="flex h-8 w-8 items-center justify-center overflow-hidden">
                <Icone className="h-full w-full object-contain" />
              </span>
              {e.nome}
            </button>
          )
        })}
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4 sm:px-6">
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

        {!isLoading && sugestoes.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t px-4 py-2 sm:px-6">
            {sugestoes.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSend(s)}
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

        <ChatInput onSend={(text) => onSend(text)} isLoading={isLoading} placeholder={focado.placeholder} />
      </div>
    </div>
  )
}
