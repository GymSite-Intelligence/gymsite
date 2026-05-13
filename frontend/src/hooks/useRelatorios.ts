/**
 * hooks/useRelatorios.ts — Lista relatórios da org ativa do user logado.
 *
 * Modo real (USE_MOCKS=false): consulta `v_relatorios_resumo` via Supabase JS
 * com o JWT do user. RLS (`security_invoker=true`) faz o filtro automático
 * por `user_org_ids()`. Frontend não precisa filtrar por org_id manualmente.
 *
 * Modo mock: fixtures locais (dev sem internet).
 */
import { useQuery } from '@tanstack/react-query'
import { getMockRelatoriosResumo, USE_MOCKS } from '@/mocks'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import type { RelatorioResumo } from '@/types/domain'

export interface RelatoriosFilters {
  cidade?: string
  veredito?: string
  since?: string // ISO date "2026-05-01"
}

/** Filtros client-side adicionais (busca por bairro junto). */
function applyClientFilters(
  rows: RelatorioResumo[],
  filters: RelatoriosFilters,
): RelatorioResumo[] {
  return rows.filter((r) => {
    if (filters.cidade) {
      const q = filters.cidade.toLowerCase()
      const match =
        r.cidade.toLowerCase().includes(q) || r.bairro.toLowerCase().includes(q)
      if (!match) return false
    }
    return true
  })
}

export function useRelatorios(filters: RelatoriosFilters = {}) {
  const { user } = useAuth()
  // Sem user logado, o JWT do supabase é anon e a RLS bloqueia tudo —
  // não vale a pena chamar.
  const enabled = USE_MOCKS || !!user

  return useQuery({
    queryKey: ['relatorios', user?.id ?? 'anon', filters],
    enabled,
    queryFn: async (): Promise<RelatorioResumo[]> => {
      if (USE_MOCKS) {
        await new Promise((r) => setTimeout(r, 50))
        return applyClientFilters(getMockRelatoriosResumo(), filters)
      }

      let q = supabase
        .from('v_relatorios_resumo')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(200)

      if (filters.veredito) q = q.eq('veredito', filters.veredito)
      if (filters.since) q = q.gte('created_at', filters.since)

      const { data, error } = await q
      if (error) {
        throw new Error(`Supabase: ${error.message}`)
      }
      const rows = (data ?? []) as unknown as RelatorioResumo[]
      return applyClientFilters(rows, filters)
    },
  })
}
