/**
 * AuthCallbackPage — recebe o redirect do Magic Link.
 *
 * Supabase-js (PKCE flow) processa o hash automaticamente em
 * onAuthStateChange. Aqui só esperamos a sessão materializar e
 * empurramos pra /relatorios. Se passar 8s sem session, volta pra /login.
 */
import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/lib/auth'
import { Loader2 } from 'lucide-react'

export function AuthCallbackPage() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (loading) return
    if (session) {
      navigate({ to: '/relatorios', replace: true })
      return
    }
    const timer = setTimeout(
      () => navigate({ to: '/login', replace: true }),
      4000,
    )
    return () => clearTimeout(timer)
  }, [session, loading, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center text-muted-foreground gap-2">
      <Loader2 size={16} className="animate-spin" />
      Autenticando…
    </div>
  )
}
