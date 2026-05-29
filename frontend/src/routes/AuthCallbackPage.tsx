/**
 * AuthCallbackPage — recebe o redirect do Magic Link.
 *
 * Supabase-js (PKCE flow) processa o hash automaticamente em
 * onAuthStateChange. Aqui só esperamos a sessão materializar e
 * empurramos pra /relatorios. Se passar 8s sem session, volta pra /login.
 */
import { useEffect, useRef } from 'react'
import { useNavigate, useRouterState } from '@tanstack/react-router'
import { useAuth } from '@/lib/auth'
import { Loader2 } from 'lucide-react'

export function AuthCallbackPage() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const redirectedRef = useRef(false)

  useEffect(() => {
    if (loading) return
    if (session) {
      if (pathname !== '/auth/callback' || redirectedRef.current) return
      redirectedRef.current = true
      void navigate({ to: '/relatorios', replace: true })
      return
    }
    const timer = setTimeout(() => {
      if (redirectedRef.current) return
      redirectedRef.current = true
      void navigate({ to: '/login', replace: true })
    }, 4000)
    return () => clearTimeout(timer)
  }, [session, loading, pathname, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center text-muted-foreground gap-2">
      <Loader2 size={16} className="animate-spin" />
      Autenticando…
    </div>
  )
}
