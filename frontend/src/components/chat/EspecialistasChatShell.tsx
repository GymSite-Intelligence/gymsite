/**
 * Shell compartilhado Degustação (public/sandbox) e Consultor (app).
 * Mesmo viewport de chat; auth/billing ficam nos hooks/API de cada variante.
 */
import { ConsultorChat } from '@/components/chat/ConsultorChat'
import { ConsultorProjetoAside } from '@/components/chat/ConsultorProjetoAside'
import { DegustacaoRouteShell } from '@/components/site/DegustacaoRouteShell'
import type { UseConsultorChatReturn } from '@/hooks/useConsultorChat'
import type { AgenteApiId } from '@/config/site-agent-map'

export type EspecialistasShellVariant = 'public' | 'sandbox' | 'app'

export type EspecialistasChatShellProps =
  | { variant: 'public' | 'sandbox'; formulario: boolean; devToken?: string }
  | { variant: 'app'; chat: UseConsultorChatReturn }

function AppEspecialistasShell({ chat }: { chat: UseConsultorChatReturn }) {
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
    <div
      data-testid="especialistas-shell"
      className="flex h-full min-h-0 w-full flex-1 overflow-hidden bg-background"
    >
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

export function EspecialistasChatShell(props: EspecialistasChatShellProps) {
  if (props.variant === 'app') {
    return <AppEspecialistasShell chat={props.chat} />
  }

  return (
    <DegustacaoRouteShell
      variant={props.variant}
      formulario={props.formulario}
      devToken={props.devToken}
      data-testid="especialistas-shell"
    />
  )
}
