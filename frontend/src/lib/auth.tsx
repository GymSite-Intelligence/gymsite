/**
 * lib/auth.tsx — AuthContext, AuthProvider e useAuth (módulo único).
 *
 * Context + hook + provider no mesmo arquivo evita instâncias duplicadas do
 * React Context no bundle de produção (chunk split entre auth.tsx e auth-context.ts).
 *
 * Modelo:
 * - Signup é **por convite apenas** (admin cria users no Supabase Dashboard).
 * - O frontend depende do JWT do user pra ler dados via Supabase JS direto (RLS).
 * - Sessão persistida pelo supabase-js (localStorage).
 */
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { USE_MOCKS } from '@/mocks'
import { createMockSession, isSupabaseConfigured } from '@/lib/mock-auth'
import { isPasswordExpired } from '@/lib/password-expiry'

export interface AuthState {
  user: User | null
  session: Session | null
  loading: boolean
  /** true quando auth mock está ativo (dev sem Supabase). */
  mockAuth: boolean
  signOut: () => Promise<void>
  signInDev: () => void
}

export const AuthContext = createContext<AuthState | undefined>(undefined)

/** Fallback quando o bundle duplica o módulo de context (Provider vs useAuth). */
const authStore: { current: AuthState | null } = { current: null }

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  const state = ctx ?? authStore.current
  if (!state) throw new Error('useAuth fora de <AuthProvider>')
  return state
}

const mockAuthEnabled = USE_MOCKS && !isSupabaseConfigured()

async function rejectExpiredPasswordSession(session: Session | null): Promise<Session | null> {
  if (!session?.user || mockAuthEnabled) return session
  if (!isPasswordExpired(session.user)) return session
  await supabase.auth.signOut()
  return null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (mockAuthEnabled) {
      setSession(createMockSession())
      setLoading(false)
      return
    }

    let active = true

    supabase.auth.getSession().then(async ({ data }) => {
      if (!active) return
      const s = await rejectExpiredPasswordSession(data.session)
      setSession(s)
      setLoading(false)
    })

    const { data: sub } = supabase.auth.onAuthStateChange(async (_event, s) => {
      const next = await rejectExpiredPasswordSession(s)
      setSession(next)
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
    mockAuth: mockAuthEnabled,
    signOut: async () => {
      if (mockAuthEnabled) {
        setSession(null)
        authStore.current = null
        return
      }
      await supabase.auth.signOut()
    },
    signInDev: () => {
      if (mockAuthEnabled) setSession(createMockSession())
    },
  }

  authStore.current = value

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
