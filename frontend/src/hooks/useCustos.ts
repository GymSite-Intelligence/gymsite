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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { supabase, API_BASE } from '@/lib/supabase'

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

export interface CustosAPIData {
  llm: {
    total_brl: number
    por_agente: Record<
      string,
      {
        tokens_in: number
        tokens_out: number
        custo_brl: number
        modelo: string
      }
    >
  }
  api: {
    total_brl: number
    por_sku: Record<
      string,
      {
        calls: number
        custo_brl: number
      }
    >
  }
  total_brl: number
}

export function useCustosAPI(relatorioId: string | null) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['custos-api', user?.id ?? 'anon', relatorioId],
    enabled: !!user && !!relatorioId,
    queryFn: async (): Promise<CustosAPIData> => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: HeadersInit = {}
      if (token) {
        headers.Authorization = `Bearer ${token}`
      }
      const res = await fetch(`${API_BASE}/api/relatorios/${encodeURIComponent(relatorioId!)}/custos-api`, { headers })
      if (!res.ok) {
        throw new Error(`Erro ao buscar custos de API: ${res.statusText}`)
      }
      return res.json()
    },
  })
}

export interface SugestaoOtimizacao {
  tipo: string
  agente: string
  modelo_atual: string
  modelo_sugerido?: string
  economia_brl: number
  detalhe: string
  severidade: 'alta' | 'media' | 'baixa'
}

export interface CustosOptimizationsData {
  periodo_dias: number
  total_chamadas: number
  total_custo_brl: number
  por_agente: Record<string, {
    tokens_in: number
    tokens_out: number
    calls: number
    model: string
    custo_brl: number
    finish_reasons: Record<string, number>
  }>
  sugestoes: SugestaoOtimizacao[]
  economia_total_estimada: number
}

export function useCustosOptimizations(dias: number = 30) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['custos-optimizations', user?.id ?? 'anon', dias],
    enabled: !!user,
    queryFn: async (): Promise<CustosOptimizationsData> => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: HeadersInit = {}
      if (token) {
        headers.Authorization = `Bearer ${token}`
      }
      const res = await fetch(`${API_BASE}/api/custos/optimizations?dias=${dias}`, { headers })
      if (!res.ok) {
        throw new Error(`Erro ao buscar otimizações: ${res.statusText}`)
      }
      return res.json()
    },
  })
}

export interface PropostaOtimizacao {
  id: string
  org_id: string
  criado_por: string | null
  criado_em: string
  tipo: string
  agente: string
  modelo_atual: string
  modelo_sugerido: string
  titulo: string
  descricao: string
  economia_brl_estimada: number
  severidade: string
  status: string
  aprovado_por: string | null
  aprovado_em: string | null
  justificativa_aprovacao: string | null
  implementado_por: string | null
  implementado_em: string | null
  resultado_observacao: string | null
  economia_brl_real: number | null
  referencia_dados: Record<string, unknown> | null
}

export function usePropostasOtimizacao(status?: string) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['propostas-otimizacao', user?.id ?? 'anon', status],
    enabled: !!user,
    queryFn: async (): Promise<PropostaOtimizacao[]> => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: HeadersInit = {}
      if (token) {
        headers.Authorization = `Bearer ${token}`
      }
      let url = `${API_BASE}/api/custos/propostas`
      if (status) url += `?status=${encodeURIComponent(status)}`
      const res = await fetch(url, { headers })
      if (!res.ok) {
        throw new Error(`Erro ao buscar propostas: ${res.statusText}`)
      }
      return res.json()
    },
  })
}

export interface PropostaOtimizacaoInput {
  tipo: string
  agente: string
  modelo_atual: string
  modelo_sugerido: string
  titulo: string
  descricao: string
  economia_brl_estimada: number
  severidade: string
  referencia_dados: Record<string, unknown> | null
}

export function useCriarPropostaOtimizacao() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: PropostaOtimizacaoInput) => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (token) {
        headers.Authorization = `Bearer ${token}`
      }
      const res = await fetch(`${API_BASE}/api/custos/propostas`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        throw new Error(`Erro ao criar proposta: ${res.statusText}`)
      }
      return res.json() as Promise<PropostaOtimizacao>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['propostas-otimizacao'] })
    },
  })
}

export function useAtualizarPropostaOtimizacao() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, status, justificativa, resultado_observacao, economia_brl_real }: { id: string; status: string; justificativa?: string; resultado_observacao?: string; economia_brl_real?: number }) => {
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (token) {
        headers.Authorization = `Bearer ${token}`
      }
      const res = await fetch(`${API_BASE}/api/custos/propostas/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ status, justificativa, resultado_observacao, economia_brl_real }),
      })
      if (!res.ok) {
        throw new Error(`Erro ao atualizar proposta: ${res.statusText}`)
      }
      return res.json() as Promise<PropostaOtimizacao>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['propostas-otimizacao'] })
    },
  })
}
