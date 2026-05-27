/**
 * Sessão fake para dev quando VITE_USE_MOCKS=true e Supabase não está configurado.
 * Permite acessar /dashboard e rotas autenticadas sem credenciais reais.
 */
import type { Session, User } from '@supabase/supabase-js'

export function isSupabaseConfigured(): boolean {
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined
  return Boolean(url?.trim() && key?.trim())
}

export function createMockSession(): Session {
  const now = Math.floor(Date.now() / 1000)
  const user = {
    id: '00000000-0000-4000-8000-000000000001',
    aud: 'authenticated',
    role: 'authenticated',
    email: 'dev@gymsite.local',
    email_confirmed_at: new Date().toISOString(),
    app_metadata: { provider: 'mock', org_role: 'admin' },
    user_metadata: { full_name: 'Dev GymSite' },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  } as User

  return {
    access_token: 'mock-access-token',
    token_type: 'bearer',
    expires_in: 60 * 60 * 24 * 30,
    expires_at: now + 60 * 60 * 24 * 30,
    refresh_token: 'mock-refresh-token',
    user,
  }
}
