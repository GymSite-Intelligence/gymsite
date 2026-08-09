import { useSearch } from '@tanstack/react-router'
import { DegustacaoRouteShell } from '@/components/site/DegustacaoRouteShell'

export function DegustacaoPage() {
  const { abrir, dev_token } = useSearch({ from: '/degustacao' })
  return (
    <DegustacaoRouteShell
      variant="public"
      formulario={abrir === 'formulario'}
      devToken={dev_token?.trim() || undefined}
    />
  )
}
