import { useSearch } from '@tanstack/react-router'
import { EspecialistasChatShell } from '@/components/chat/EspecialistasChatShell'

export function DegustacaoPage() {
  const { abrir, dev_token } = useSearch({ from: '/degustacao' })
  return (
    <EspecialistasChatShell
      variant="public"
      formulario={abrir === 'formulario'}
      devToken={dev_token?.trim() || undefined}
    />
  )
}
