/**
 * RequireAuth — gate de rotas autenticadas.
 *
 * Redireciona via useEffect (não <Navigate> no render) para evitar loop infinito
 * no Transitioner do TanStack Router quando a sessão expira ou a rota recarrega.
 */
import { useEffect, useRef, type ReactNode } from 'react'
import { useNavigate, useRouterState } from '@tanstack/react-router'
import { useAuth } from '@/lib/auth'
import { Loader2 } from 'lucide-react'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const redirectingRef = useRef(false)

  useEffect(() => {
    if (loading || session) {
      redirectingRef.current = false
      return
    }
    if (pathname === '/login' || redirectingRef.current) return
    redirectingRef.current = true
    void navigate({ to: '/login', replace: true })
  }, [loading, session, pathname, navigate])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground gap-2">
        <Loader2 size={16} className="animate-spin" />
        Carregando…
      </div>
    )
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground gap-2">
        <Loader2 size={16} className="animate-spin" />
        Redirecionando…
      </div>
    )
  }

  return <>{children}</>
}
