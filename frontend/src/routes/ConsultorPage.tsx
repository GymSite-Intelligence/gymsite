import { useConsultorChat } from '@/hooks/useConsultorChat'
import { EspecialistasChatShell } from '@/components/chat/EspecialistasChatShell'

export function ConsultorPage() {
  const chat = useConsultorChat()
  return <EspecialistasChatShell variant="app" chat={chat} />
}
