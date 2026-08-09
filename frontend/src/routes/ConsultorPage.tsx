import { useConsultorChat } from '@/hooks/useConsultorChat'
import { ConsultorAppShell } from '@/components/chat/ConsultorAppShell'

export function ConsultorPage() {
  const chat = useConsultorChat()
  return <ConsultorAppShell chat={chat} />
}
