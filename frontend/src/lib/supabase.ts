/**
 * lib/supabase.ts — Singleton Supabase client.
 *
 * Inicializado lazy a partir de VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY.
 * Quando VITE_USE_MOCKS=true, hooks bypassam o client (não chamam).
 *
 * Schema GymSite vive no mesmo Postgres do CFN (cargo-flow-navigator).
 * Tabelas: organizations, relatorios, relatorio_inputs, relatorio_outputs,
 * candidatos, competidores, cenarios_financeiros, sensibilidade_cenarios,
 * bairros_alternativos. Views: v_relatorios_resumo, v_bairros_aggregate.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js'

let _client: SupabaseClient | null = null

function _getClient(): SupabaseClient {
  if (_client) return _client
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined
  if (!url || !key) {
    throw new Error(
      'Supabase não configurado — defina VITE_SUPABASE_URL e VITE_SUPABASE_ANON_KEY no .env do frontend.',
    )
  }
  _client = createClient(url, key, {
    auth: { persistSession: true, autoRefreshToken: true },
  })
  return _client
}

export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    return _getClient()[prop as keyof SupabaseClient]
  },
})

/** URL base da API HTTP do backend (FastAPI). Default localhost:8000 em dev. */
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.trim() ||
  'http://localhost:8000'
