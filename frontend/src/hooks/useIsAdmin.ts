/**
 * useIsAdmin — flag de permissão admin pra esconder UI sensível ao cliente.
 *
 * Esconde informações operacionais que o usuário-final (cliente da Vectra)
 * não precisa ver: estimativa de custo do pipeline, duração interna,
 * telemetria de tokens, IDs de execução, etc.
 *
 * Resolução em cascata:
 * 1. `localStorage.gymsite_admin === 'true'` — override manual em dev.
 *    Setar via DevTools: `localStorage.setItem('gymsite_admin', 'true')`.
 * 2. `VITE_DEV_AS_ADMIN === 'true'` no .env do frontend — default em dev.
 * 3. Futuro: Supabase Auth + claim/JWT (`user_metadata.role === 'admin'`)
 *    quando o auth flow estiver plugado.
 *
 * Em produção sem nenhum desses sinais, retorna false (modo cliente).
 *
 * NOTA: NÃO usar pra controle de acesso real (route guards, mutações
 * destrutivas). É só pra esconder ruído visual. Permissões reais
 * devem ser checadas no backend (RLS Supabase + edge function checks).
 */
export function useIsAdmin(): boolean {
  if (typeof window === 'undefined') return false

  // 1. Override localStorage (dev e debug)
  try {
    if (window.localStorage.getItem('gymsite_admin') === 'true') return true
  } catch {
    // localStorage pode estar bloqueado (modo privado, etc) — ignora
  }

  // 2. Env var explícita (default em dev)
  if (import.meta.env.VITE_DEV_AS_ADMIN === 'true') return true

  // 3. TODO: Supabase Auth user_metadata.role
  // const { data: { user } } = useSupabaseUser()
  // return user?.user_metadata?.role === 'admin'

  return false
}
