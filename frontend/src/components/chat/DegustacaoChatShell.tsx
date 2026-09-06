import type { ReactNode } from 'react'
import { ConsultorChat } from '@/components/chat/ConsultorChat'
import { ConsultorProjetoAside } from '@/components/chat/ConsultorProjetoAside'
import { ConsultorAgentAvatar } from '@/components/chat/ConsultorAgentAvatar'
import { DegustacaoJornadaAside } from '@/components/landing/DegustacaoJornadaAside'
import { Button } from '@/components/ui/button'
import { especialistaPadrao } from '@/config/consultor-agentes'
import { DEGUSTACAO_COPY } from '@/config/gymsite-design-system'
import type { UseConsultorChatReturn } from '@/hooks/useConsultorChat'
import type { AgenteApiId } from '@/config/site-agent-map'

type ShellMode = 'app' | 'landing'

interface DegustacaoChatShellProps {
  mode?: ShellMode
  chat: UseConsultorChatReturn
  headerExtra?: ReactNode
  temAnalise?: boolean
}

export function DegustacaoChatShell({
  mode = 'app',
  chat,
  headerExtra,
  temAnalise = false,
}: DegustacaoChatShellProps) {
  const {
    messages,
    projeto,
    projetoId,
    sessions,
    sugestoes,
    podeGerarRelatorio,
    isLoading,
    isLoadingSessions,
    isGeneratingReport,
    error,
    sendMessage,
    gerarRelatorio,
    novaConversa,
    selectSession,
    exportJson,
  } = chat

  const loc = projeto?.localizacao
  const locLabel = loc?.cidade ? [loc.bairro, loc.cidade, loc.uf].filter(Boolean).join(', ') : null
  const IconeConsultor = especialistaPadrao.Icone

  const onSend = (text: string, agente?: string) => {
    void sendMessage(text, (agente as AgenteApiId) || 'degustacao')
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b px-4 sm:px-6">
          <ConsultorAgentAvatar Icone={IconeConsultor} isActive size="inline" />
          <div className="min-w-0">
            <h1 className="text-sm font-semibold leading-tight">
              {mode === 'landing' ? 'Degustação GymSite' : 'Consultor GymSite'}
            </h1>
            <p className="truncate text-[10px] text-muted-foreground">
              {locLabel || (mode === 'landing' ? DEGUSTACAO_COPY.subtitle : 'Análise em tempo real')}
            </p>
          </div>
          {headerExtra}
          <div className="ml-auto">
            <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" onClick={novaConversa}>
              Nova conversa
            </Button>
          </div>
        </header>

        <ConsultorChat
          messages={messages}
          sessions={sessions}
          activeProjetoId={projetoId}
          sugestoes={sugestoes}
          isLoading={isLoading}
          isLoadingSessions={isLoadingSessions}
          isGeneratingReport={isGeneratingReport}
          podeGerarRelatorio={podeGerarRelatorio}
          temRelatorio={Boolean(projeto?.relatorio_id)}
          error={error}
          onSend={onSend}
          onGerarRelatorio={gerarRelatorio}
          onSelectSession={selectSession}
          onNewSession={novaConversa}
          onExportJson={exportJson}
        />
      </div>

      {mode === 'app' ? <ConsultorProjetoAside projeto={projeto} /> : <DegustacaoJornadaAside temAnalise={temAnalise} />}
    </div>
  )
}
