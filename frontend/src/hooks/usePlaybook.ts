/**
 * usePlaybook — Plano de Abertura (Playbook Fase 1).
 *
 * Conversa com /api/execucao/* (JWT Supabase). Valores monetários chegam em
 * CENTAVOS do backend — converter para reais apenas no display (formatBRL).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { API_BASE, supabase } from '@/lib/supabase'

export interface ChecklistItem {
  id: string
  tarefa_id: string
  descricao: string
  concluido: boolean
  ordem: number
}

export interface Tarefa {
  id: string
  playbook_id: string
  titulo: string
  descricao: string | null
  categoria: string
  status: 'A_FAZER' | 'EM_ANDAMENTO' | 'CONCLUIDA' | 'BLOQUEADA' | 'CANCELADA'
  prioridade: 'BAIXA' | 'MEDIA' | 'ALTA' | 'CRITICA'
  ordem: number
  custo_planejado: number | null
  custo_real: number | null
  data_inicio: string | null
  data_prevista_conclusao: string | null
  data_conclusao: string | null
  responsavel_nome: string | null
  sugerida_pela_ia: boolean
  origem_relatorio_secao: string | null
  origem_relatorio_insight: string | null
  dias_atraso: number
  esta_atrasada: boolean
  variacao_conclusao_dias: number | null
  checklist: ChecklistItem[]
}

export interface TarefaNota {
  id: string
  tarefa_id: string
  autor_nome: string
  origem: 'DONO' | 'EXTERNO' | 'IA'
  texto: string
  criado_em: string
}

export interface Dependencia {
  tarefa_id: string
  depende_de_tarefa_id: string
  tipo: string
}

export interface PlaybookCompleto {
  id: string
  projeto_id: string
  relatorio_id: string | null
  nome: string
  status: string
  data_inicio: string | null
  data_prevista_conclusao: string | null
  custo_planejado_total: number | null
  custo_real_total: number
  total_tarefas: number
  tarefas_concluidas: number
  percentual_concluido: number
  tarefas_atrasadas: number
  tarefas: Tarefa[]
  dependencias: Dependencia[]
}

async function authHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (session?.access_token) {
    headers.Authorization = `Bearer ${session.access_token}`
  }
  return headers
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await authHeaders()
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body?.detail || `Erro ${res.status}`)
  }
  return body as T
}

export const playbookKeys = {
  all: ['playbooks'] as const,
  detail: (id: string) => ['playbooks', id] as const,
  notas: (tarefaId: string) => ['playbooks', 'notas', tarefaId] as const,
}

export function usePlaybook(playbookId: string | undefined) {
  return useQuery({
    queryKey: playbookKeys.detail(playbookId ?? ''),
    enabled: Boolean(playbookId),
    queryFn: () => api<PlaybookCompleto>(`/api/execucao/playbooks/${playbookId}`),
    staleTime: 30_000,
  })
}

export interface GerarPlanoResult {
  playbook_id: string
  ja_existia: boolean
  tarefas_geradas?: number
}

export function useGerarPlano() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { relatorioId: string; force?: boolean }) =>
      api<GerarPlanoResult>('/api/execucao/playbooks/gerar', {
        method: 'POST',
        body: JSON.stringify({ relatorio_id: vars.relatorioId, force: vars.force ?? false }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: playbookKeys.all })
    },
  })
}

export function useAtualizarTarefa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { tarefaId: string; status: Tarefa['status']; custoReal?: number | null }) =>
      api<{ tarefa: Tarefa; tarefas_liberadas: string[] }>(`/api/execucao/tarefas/${vars.tarefaId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: vars.status,
          custo_real: vars.custoReal ?? undefined,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) })
    },
  })
}

export function useNotasTarefa(tarefaId: string | null) {
  return useQuery({
    queryKey: playbookKeys.notas(tarefaId ?? ''),
    enabled: Boolean(tarefaId),
    queryFn: () => api<{ items: TarefaNota[] }>(`/api/execucao/tarefas/${tarefaId}/notas`),
    select: (r) => r.items,
    staleTime: 15_000,
  })
}

export function useAdicionarNota(tarefaId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (texto: string) =>
      api<TarefaNota>(`/api/execucao/tarefas/${tarefaId}/notas`, {
        method: 'POST',
        body: JSON.stringify({ texto }),
      }),
    onSuccess: () => {
      if (tarefaId) qc.invalidateQueries({ queryKey: playbookKeys.notas(tarefaId) })
    },
  })
}

export function useMarcarChecklist(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { itemId: string; concluido: boolean }) =>
      api<ChecklistItem>(`/api/execucao/checklist/${vars.itemId}`, {
        method: 'PATCH',
        body: JSON.stringify({ concluido: vars.concluido }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) })
    },
  })
}
