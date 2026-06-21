/**
 * ConsultorPage — UI do Consultor V2 (Jarvis).
 *
 * Espelha a AssistentePage (V1) mas consome `/api/consultor/*` via useConsultorChat.
 * Layout: chat (centro, reusa ChatMessage + ChatInput) + painel de projeto (direita):
 * checklist das 7 pesquisas, custo acumulado, status e atalho pro Relatório Formal.
 */
import { useEffect, useRef } from 'react'
import { Link } from '@tanstack/react-router'
import { Bot, Loader2, CheckCircle2, Circle, FileText, MapPin, Sparkles } from 'lucide-react'
import { ChatMessage } from '@/components/chat/ChatMessage'
import { ChatInput } from '@/components/chat/ChatInput'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useConsultorChat, type ConsultorPesquisas } from '@/hooks/useConsultorChat'

const PESQUISA_LABELS: { key: keyof ConsultorPesquisas; label: string }[] = [
  { key: 'mercado', label: 'Contexto de mercado' },
  { key: 'demografia', label: 'Demografia (IBGE)' },
  { key: 'concorrentes', label: 'Concorrentes' },
  { key: 'reviews', label: 'Reviews e dores' },
  { key: 'oferta_concorrentes', label: 'Oferta e serviços' },
  { key: 'pontos_comerciais', label: 'Pontos comerciais' },
  { key: 'investimento', label: 'Viabilidade financeira' },
]

const STATUS_LABEL: Record<string, string> = {
  EM_CONVERSA: 'Em conversa',
  PESQUISANDO: 'Pesquisando',
  CONSOLIDANDO: 'Gerando relatório',
  RELATORIO_GERADO: 'Relatório pronto',
  ARQUIVADO: 'Arquivado',
}

export function ConsultorPage() {
  const {
    messages,
    projeto,
    sugestoes,
    podeGerarRelatorio,
    isLoading,
    isGeneratingReport,
    error,
    sendMessage,
    gerarRelatorio,
    novaConversa,
  } = useConsultorChat()

  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, isLoading])

  const loc = projeto?.localizacao
  const locLabel = loc?.cidade
    ? [loc.bairro, loc.cidade, loc.uf].filter(Boolean).join(', ')
    : null

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full overflow-hidden">
      {/* ── Coluna do chat ──────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b px-4 sm:px-6">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
            <Bot className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold leading-tight">Consultor GymSite</h1>
            <p className="truncate text-[10px] text-muted-foreground">
              {locLabel || 'Análise de viabilidade em tempo real'}
            </p>
          </div>
          <div className="ml-auto">
            <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" onClick={novaConversa}>
              Nova conversa
            </Button>
          </div>
        </header>

        {/* Mensagens */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="pb-2">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} msg={msg} />
            ))}
            {isLoading && messages[messages.length - 1]?.role === 'user' && (
              <div className="flex gap-3 px-4 py-5 sm:px-6 lg:px-8">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 sm:h-8 sm:w-8">
                  <Bot className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span className="text-xs">Pesquisando...</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sugestões de próximo passo */}
        {!isLoading && sugestoes.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t px-4 py-2 sm:px-6">
            {sugestoes.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => sendMessage(s)}
                className="rounded-full border bg-muted/40 px-3 py-1 text-xs text-foreground transition-colors hover:bg-muted"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Banner: gerar relatório formal */}
        {podeGerarRelatorio && !projeto?.relatorio_id && (
          <div className="flex items-center gap-2 border-t bg-emerald-50 px-4 py-2 text-xs text-emerald-800 sm:px-6">
            <Sparkles className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">Dados suficientes para o Relatório Formal de Viabilidade.</span>
            <Button
              size="sm"
              className="h-7 gap-1 text-xs"
              disabled={isGeneratingReport}
              onClick={() => gerarRelatorio()}
            >
              {isGeneratingReport ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
              Gerar relatório
            </Button>
          </div>
        )}

        {error && (
          <div className="border-t bg-red-50 px-4 py-2 text-center text-xs text-red-700 sm:px-6">
            {error}
          </div>
        )}

        <ChatInput onSend={(text) => sendMessage(text)} isLoading={isLoading} placeholder="Mensagem ao Consultor..." />
      </div>

      {/* ── Painel do projeto (desktop) ─────────────────────────────────── */}
      <aside className="hidden w-72 shrink-0 flex-col gap-4 border-l bg-muted/20 p-4 lg:flex">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Projeto</h2>
          {locLabel ? (
            <div className="mt-1 flex items-center gap-1.5 text-sm font-medium">
              <MapPin className="h-3.5 w-3.5 text-emerald-600" />
              <span className="truncate">{locLabel}</span>
            </div>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">Informe cidade e bairro para começar.</p>
          )}
          {projeto?.status && (
            <Badge variant="secondary" className="mt-2 text-[10px]">
              {STATUS_LABEL[projeto.status] || projeto.status}
            </Badge>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pesquisas</h3>
          <ul className="space-y-1.5">
            {PESQUISA_LABELS.map(({ key, label }) => {
              const done = Boolean(projeto?.pesquisas_realizadas?.[key])
              return (
                <li key={key} className="flex items-center gap-2 text-xs">
                  {done ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600" />
                  ) : (
                    <Circle className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40" />
                  )}
                  <span className={cn(done ? 'text-foreground' : 'text-muted-foreground')}>{label}</span>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="mt-auto space-y-2">
          {typeof projeto?.custo_brl_ate_agora === 'number' && projeto.custo_brl_ate_agora > 0 && (
            <p className="text-[11px] text-muted-foreground">
              Custo de pesquisa: <span className="font-medium text-foreground">R$ {projeto.custo_brl_ate_agora.toFixed(2)}</span>
            </p>
          )}
          {projeto?.relatorio_id && (
            <Button variant="outline" size="sm" className="w-full gap-1 text-xs" asChild>
              <Link to="/relatorios/$relatorioId/aguardando" params={{ relatorioId: projeto.relatorio_id }}>
                <FileText className="h-3.5 w-3.5" />
                Acompanhar relatório
              </Link>
            </Button>
          )}
        </div>
      </aside>
    </div>
  )
}
