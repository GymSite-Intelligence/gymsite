/**
 * AssistentePage — página do Agente de IA Especialista em Fitness.
 *
 * Interface conversacional completa com sidebar, markdown, anexos
 * e slot-filling para substituir o formulário tradicional.
 */
import { ChatLayout } from '@/components/chat/ChatLayout'
import { useConversationalChat } from '@/hooks/useConversationalChat'

export function AssistentePage() {
  const {
    messages,
    sessions,
    state,
    sendMessage,
    sendFeedback,
    isLoading,
    error,
    newSession,
    selectSession,
  } = useConversationalChat()

  return (
    <ChatLayout
      messages={messages}
      sessions={sessions}
      activeSessionId={state.sessionId}
      isLoading={isLoading}
      error={error}
      onSendMessage={sendMessage}
      onNewSession={newSession}
      onSelectSession={selectSession}
      onFeedback={sendFeedback}
    />
  )
}
