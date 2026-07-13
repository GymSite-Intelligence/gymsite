import { useConsultorChat } from '@/hooks/useConsultorChat'
import { DegustacaoChatShell } from '@/components/chat/DegustacaoChatShell'

export function ConsultorPage() {
  const chat = useConsultorChat()
  return <DegustacaoChatShell mode="app" chat={chat} />
}
