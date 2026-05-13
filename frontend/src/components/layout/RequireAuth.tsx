/**
 * RequireAuth — gate de rotas autenticadas.
 *
 * Espera o AuthProvider resolver a sessão inicial. Se logado, renderiza
 * children. Se não, redireciona pra /login. Children tipicamente é o
 * `<AppShell />` que por sua vez renderiza o `<Outlet />` da rota filha.
 */
import type { ReactNode } from 'react'
import { Navigate } from '@tanstack/react-router'
import { useAuth } from '@/lib/auth'
import { Loader2 } from 'lucide-react'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground gap-2">
        <Loader2 size={16} className="animate-spin" />
        Carregando…
      </div>
    )
  }
  if (!session) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
