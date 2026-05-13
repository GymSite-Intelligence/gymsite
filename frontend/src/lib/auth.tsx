/**
 * lib/auth.tsx — AuthProvider + useAuth.
 *
 * Modelo:
 * - Signup é **por convite apenas** (admin cria users no Supabase Dashboard).
 *   Não há tela de signup. A LoginPage só faz Magic Link via email já existente.
 * - O frontend depende do JWT do user pra ler dados via Supabase JS direto
 *   (RLS faz o filtro por org_id usando `user_org_ids()`).
 * - Sessão é persistida pelo próprio supabase-js (localStorage). AuthProvider
 *   reage a onAuthStateChange e expõe `{ user, session, loading }`.
 */
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

interface AuthState {
  user: User | null
  session: Session | null
  loading: boolean
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      setLoading(false)
    })

    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s)
      setLoading(false)
    })

    return () => {
      active = false
      sub.subscription.unsubscribe()
    }
  }, [])

  const value: AuthState = {
    user: session?.user ?? null,
    session,
    loading,
    signOut: async () => {
      await supabase.auth.signOut()
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth fora de <AuthProvider>')
  return ctx
}
