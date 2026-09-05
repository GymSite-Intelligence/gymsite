/**
 * @deprecated Use EspecialistasChatShell variant="app" directly.
 */
import { EspecialistasChatShell } from '@/components/chat/EspecialistasChatShell'
import type { UseConsultorChatReturn } from '@/hooks/useConsultorChat'

interface ConsultorAppShellProps {
  chat: UseConsultorChatReturn
}

export function ConsultorAppShell({ chat }: ConsultorAppShellProps) {
  return <EspecialistasChatShell variant="app" chat={chat} />
}
