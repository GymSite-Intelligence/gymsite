/**
 * Shell do consultor no APP logado.
 * Separado de DegustacaoChatShell (site) — não compartilhar layout de degustação.
 */
import { ConsultorChat } from '@/components/chat/ConsultorChat'
import { ConsultorProjetoAside } from '@/components/chat/ConsultorProjetoAside'
import type { UseConsultorChatReturn } from '@/hooks/useConsultorChat'
import type { AgenteApiId } from '@/config/site-agent-map'

interface ConsultorAppShellProps {
  chat: UseConsultorChatReturn
}

export function ConsultorAppShell({ chat }: ConsultorAppShellProps) {
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

  const onSend = (text: string, agente?: string) => {
    void sendMessage(text, (agente as AgenteApiId) || 'degustacao')
  }

  return (
    <div className="flex h-[calc(100dvh-var(--header-height,3rem))] min-h-0 w-full overflow-hidden border border-border bg-background">
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
      <ConsultorProjetoAside projeto={projeto} />
    </div>
  )
}
