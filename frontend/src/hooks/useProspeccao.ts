/**
 * useProspeccao — hooks TanStack Query para o módulo de prospecção.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE, supabase } from '@/lib/supabase'

export interface Oportunidade {
  id: string
  org_id: string | null
  cnpj: string
  cno: string | null
  cidade: string
  uf: string
  razao_social: string | null
  nome_fantasia: string | null
  nome_obra: string | null
  segmento_operacao: string | null
  situacao_obra: string | null
  area_total_m2: number | null
  score_match: number | null
  motivo_match: string | null
  status: 'novo' | 'qualificado' | 'webhook_enviado' | 'engajado' | 'fechado' | 'descartado'
  prioridade: 'baixa' | 'media' | 'alta' | 'critica'
  webhook_enviado_at: string | null
  webhook_resposta_http: number | null
  webhook_tentativas: number
  contato_cnpj: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ProspeccaoFilters {
  cidade?: string
  uf?: string
  status?: string
  prioridade?: string
  score_min?: number
}

async function authHeaders(json = false): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession()
  const headers: Record<string, string> = json ? { 'Content-Type': 'application/json' } : {}
  const token = data.session?.access_token
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function fetchOportunidades(filters: ProspeccaoFilters & { limit?: number; offset?: number }): Promise<Oportunidade[]> {
  const params = new URLSearchParams()
  if (filters.cidade) params.set('cidade', filters.cidade)
  if (filters.uf) params.set('uf', filters.uf)
  if (filters.status) params.set('status', filters.status)
  if (filters.prioridade) params.set('prioridade', filters.prioridade)
  if (filters.score_min != null) params.set('score_min', String(filters.score_min))
  params.set('limit', String(filters.limit ?? 100))
  params.set('offset', String(filters.offset ?? 0))

  const res = await fetch(`${API_BASE}/api/prospeccao/oportunidades?${params.toString()}`, {
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Falha ao carregar oportunidades')
  return res.json()
}

async function fetchOportunidade(id: string): Promise<Oportunidade> {
  const res = await fetch(`${API_BASE}/api/prospeccao/oportunidades/${id}`, {
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Oportunidade não encontrada')
  return res.json()
}

async function executarProspeccao(payload: { cidade: string; uf?: string; dias?: number; limit?: number }) {
  const res = await fetch(`${API_BASE}/api/prospeccao/executar`, {
    method: 'POST',
    headers: await authHeaders(true),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Falha ao iniciar prospecção')
  return res.json()
}

async function reenviarWebhook(id: string) {
  const res = await fetch(`${API_BASE}/api/prospeccao/oportunidades/${id}/webhook`, {
    method: 'POST',
    headers: await authHeaders(),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Falha ao reenviar webhook')
  }
  return res.json()
}

async function patchStatus(id: string, status: string) {
  const res = await fetch(`${API_BASE}/api/prospeccao/oportunidades/${id}/status`, {
    method: 'PATCH',
    headers: await authHeaders(true),
    body: JSON.stringify({ status }),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Falha ao atualizar status')
  }
  return res.json()
}

export function useOportunidades(filters: ProspeccaoFilters & { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['prospeccao', 'oportunidades', filters],
    queryFn: () => fetchOportunidades(filters),
  })
}

export function useOportunidade(id: string | undefined) {
  return useQuery({
    queryKey: ['prospeccao', 'oportunidade', id],
    queryFn: () => fetchOportunidade(id!),
    enabled: !!id,
  })
}

export function useExecutarProspeccao() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: executarProspeccao,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prospeccao', 'oportunidades'] })
    },
  })
}

export function useReenviarWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reenviarWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prospeccao'] })
    },
  })
}

export function usePatchStatusOportunidade() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => patchStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prospeccao'] })
    },
  })
}

export interface EntranteCaptado {
  cnpj: string
  nome: string
  segmento_operacao: string | null
  bairro: string | null
  data_abertura: string | null
  relatorio_id: string
  ja_em_prospeccao: boolean
  tem_contato: boolean
}

async function enriquecerEntrante(relatorioId: string, cnpj: string) {
  const res = await fetch(
    `${API_BASE}/api/relatorios/${relatorioId}/entrantes-cnpj/enriquecer`,
    {
      method: 'POST',
      headers: await authHeaders(true),
      // usar_apollo: false — só ReceitaWS (telefone do sócio QSA), sem crédito Apollo.
      body: JSON.stringify({ cnpj, usar_apollo: false }),
    },
  )
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || 'Falha ao enriquecer')
  }
  return res.json()
}

/** Enriquece UM entrante (ReceitaWS) e persiste no relatório de origem. */
export function useEnriquecerEntrante() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ relatorioId, cnpj }: { relatorioId: string; cnpj: string }) =>
      enriquecerEntrante(relatorioId, cnpj),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prospeccao', 'entrantes-captados'] })
    },
  })
}

async function fetchEntrantesCaptados(): Promise<{
  entrantes: EntranteCaptado[]
  total: number
  relatorios: number
}> {
  const res = await fetch(`${API_BASE}/api/prospeccao/entrantes-captados`, {
    headers: await authHeaders(),
  })
  if (!res.ok) throw new Error('Falha ao carregar entrantes captados')
  return res.json()
}

async function enviarEntrantesParaProspeccao(relatorioId: string, cnpjs: string[]) {
  const res = await fetch(
    `${API_BASE}/api/relatorios/${relatorioId}/entrantes-cnpj/prospeccao`,
    {
      method: 'POST',
      headers: await authHeaders(true),
      body: JSON.stringify({ cnpjs }),
    },
  )
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || 'Falha ao enviar para prospecção')
  }
  return res.json()
}

/** Entrantes CNPJ captados em todos os relatórios da org (fonte de leads V1). */
export function useEntrantesCaptados() {
  return useQuery({
    queryKey: ['prospeccao', 'entrantes-captados'],
    queryFn: fetchEntrantesCaptados,
  })
}

/** Envia entrantes selecionados de UM relatório para oportunidades_prospeccao. */
export function useEnviarEntrantesProspeccao() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ relatorioId, cnpjs }: { relatorioId: string; cnpjs: string[] }) =>
      enviarEntrantesParaProspeccao(relatorioId, cnpjs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prospeccao'] })
    },
  })
}

export { authHeaders as prospeccaoAuthHeaders }
