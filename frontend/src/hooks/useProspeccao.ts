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

export { authHeaders as prospeccaoAuthHeaders }
