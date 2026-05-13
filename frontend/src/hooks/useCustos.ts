/**
 * hooks/useCustos.ts — dados pro dashboard de custos.
 *
 * Duas queries:
 *   1. useCustosRelatorios — header da tabela (relatorios.custo_brl + tokens_total
 *      + tempo + cidade/bairro). Filtra por período.
 *   2. useCustosAgentes — breakdown por agente de UM relatório (drill-down).
 *
 * Ambas via Supabase JS direto + RLS. Owner/admin enxerga tudo da org.
 */
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'

export type Periodo = 'mes' | '30d' | 'tudo'

export interface RelatorioCustoRow {
  id: string
  status: string
  cidade: string | null
  bairro: string | null
  org_id: string
  org_nome: string
  tempo_execucao_segundos: number | null
  tokens_total: number | null
  custo_brl: number | null
  created_at: string
}

function periodoToSince(p: Periodo): string | null {
  const now = new Date()
  if (p === 'mes') {
    return new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
  }
  if (p === '30d') {
    return new Date(Date.now() - 30 * 86400_000).toISOString()
  }
  return null
}

export function useCustosRelatorios(periodo: Periodo) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['custos-relatorios', user?.id ?? 'anon', periodo],
    enabled: !!user,
    queryFn: async (): Promise<RelatorioCustoRow[]> => {
      // Junta relatorios + relatorio_inputs + organizations num único select.
      // RLS filtra por org_id IN user_org_ids() — quando user é membro de
      // várias orgs, todas vêm e a coluna Org diferencia.
      const since = periodoToSince(periodo)
      let q = supabase
        .from('relatorios')
        .select(
          'id, status, org_id, tempo_execucao_segundos, tokens_total, custo_brl, created_at, organizations(nome), relatorio_inputs(cidade, bairro)',
        )
        .order('created_at', { ascending: false })
        .limit(500)
      if (since) q = q.gte('created_at', since)
      const { data, error } = await q
      if (error) throw new Error(`Supabase: ${error.message}`)

      return ((data ?? []) as Array<{
        id: string
        status: string
        org_id: string
        tempo_execucao_segundos: number | null
        tokens_total: number | null
        custo_brl: number | null
        created_at: string
        organizations:
          | { nome: string }
          | { nome: string }[]
          | null
        relatorio_inputs:
          | { cidade: string | null; bairro: string | null }
          | { cidade: string | null; bairro: string | null }[]
          | null
      }>).map((r) => {
        const inputs = Array.isArray(r.relatorio_inputs)
          ? r.relatorio_inputs[0]
          : r.relatorio_inputs
        const org = Array.isArray(r.organizations)
          ? r.organizations[0]
          : r.organizations
        return {
          id: r.id,
          status: r.status,
          cidade: inputs?.cidade ?? null,
          bairro: inputs?.bairro ?? null,
          org_id: r.org_id,
          org_nome: org?.nome ?? '?',
          tempo_execucao_segundos: r.tempo_execucao_segundos,
          tokens_total: r.tokens_total,
          custo_brl: r.custo_brl,
          created_at: r.created_at,
        }
      })
    },
  })
}

export interface CustoAgenteRow {
  agente: string
  modelo: string
  tokens_in: number
  tokens_out: number
  custo_brl: number
}

export function useCustosAgentes(relatorioId: string | null) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['custos-agentes', user?.id ?? 'anon', relatorioId],
    enabled: !!user && !!relatorioId,
    queryFn: async (): Promise<CustoAgenteRow[]> => {
      const { data, error } = await supabase
        .from('relatorio_custos_agentes')
        .select('agente, modelo, tokens_in, tokens_out, custo_brl')
        .eq('relatorio_id', relatorioId!)
        .order('custo_brl', { ascending: false })
      if (error) throw new Error(`Supabase: ${error.message}`)
      return (data ?? []) as CustoAgenteRow[]
    },
  })
}
