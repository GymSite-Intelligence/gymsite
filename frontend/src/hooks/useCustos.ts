/**
 * hooks/useCustos.ts — dados pro dashboard de custos.
 *
 * Duas queries:
 *   1. useCustosRelatorios — header da tabela (relatorios.custo_brl + tokens_total
 *      + tempo + cidade/bairro). Filtra por período.
 *   2. useCustosAgentes — breakdown por agente de UM relatório (drill-down).
 *   3. usePropostasOtimizacao — governança de otimização (otimizacoes_custo).
 *
 * Relatórios, agentes e propostas via Supabase JS + RLS. Otimizações/custos-api
 * ainda usam a API FastAPI (sem auth ou service role no servidor).
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
        .is('deleted_at', null)
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

function mapPropostaRow(row: Record<string, unknown>): PropostaOtimizacao {
  return {
    ...(row as unknown as PropostaOtimizacao),
    economia_brl_estimada: Number(row.economia_brl_estimada ?? 0),
    economia_brl_real:
      row.economia_brl_real != null ? Number(row.economia_brl_real) : null,
  }
}

async function resolveUserOrgId(userId: string): Promise<string> {
  const { data, error } = await supabase
    .from('organization_members')
    .select('org_id')
    .eq('user_id', userId)
    .limit(1)
    .maybeSingle()
  if (error) throw new Error(`Supabase: ${error.message}`)
  if (!data?.org_id) throw new Error('Usuário sem organização')
  return data.org_id
}

/** Propostas via Supabase + RLS (mesmo padrão de useCustosRelatorios). */
export function usePropostasOtimizacao(status?: string) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['propostas-otimizacao', user?.id ?? 'anon', status],
    enabled: !!user,
    queryFn: async (): Promise<PropostaOtimizacao[]> => {
      let q = supabase
        .from('otimizacoes_custo')
        .select('*')
        .order('criado_em', { ascending: false })
      if (status) q = q.eq('status', status)
      const { data, error } = await q
      if (error) throw new Error(`Supabase: ${error.message}`)
      return (data ?? []).map((row) =>
        mapPropostaRow(row as Record<string, unknown>),
      )
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
  const { user } = useAuth()
  return useMutation({
    mutationFn: async (payload: PropostaOtimizacaoInput) => {
      if (!user) throw new Error('Não autenticado')
      const orgId = await resolveUserOrgId(user.id)
      const { data, error } = await supabase
        .from('otimizacoes_custo')
        .insert({
          org_id: orgId,
          criado_por: user.id,
          tipo: payload.tipo,
          agente: payload.agente,
          modelo_atual: payload.modelo_atual,
          modelo_sugerido: payload.modelo_sugerido,
          titulo: payload.titulo,
          descricao: payload.descricao,
          economia_brl_estimada: payload.economia_brl_estimada,
          severidade: payload.severidade,
          referencia_dados: payload.referencia_dados,
        })
        .select('*')
        .single()
      if (error) throw new Error(`Supabase: ${error.message}`)
      return mapPropostaRow(data as Record<string, unknown>)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['propostas-otimizacao'] })
    },
  })
}

export function useAtualizarPropostaOtimizacao() {
  const qc = useQueryClient()
  const { user } = useAuth()
  return useMutation({
    mutationFn: async ({
      id,
      status,
      justificativa,
      resultado_observacao,
      economia_brl_real,
    }: {
      id: string
      status: string
      justificativa?: string
      resultado_observacao?: string
      economia_brl_real?: number
    }) => {
      if (!user) throw new Error('Não autenticado')
      const now = new Date().toISOString()
      const update: Record<string, unknown> = { status }
      if (status === 'aprovada') {
        update.aprovado_por = user.id
        update.aprovado_em = now
        update.justificativa_aprovacao = justificativa ?? ''
      } else if (status === 'implementada') {
        update.implementado_por = user.id
        update.implementado_em = now
        update.resultado_observacao = resultado_observacao ?? ''
        if (economia_brl_real != null) update.economia_brl_real = economia_brl_real
      } else if (status === 'rejeitada') {
        update.justificativa_aprovacao = justificativa ?? ''
      }
      const { data, error } = await supabase
        .from('otimizacoes_custo')
        .update(update)
        .eq('id', id)
        .select('*')
        .single()
      if (error) throw new Error(`Supabase: ${error.message}`)
      return mapPropostaRow(data as Record<string, unknown>)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['propostas-otimizacao'] })
    },
  })
}
