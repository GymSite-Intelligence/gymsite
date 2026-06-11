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
  responsavel_pessoa_id: string | null
}

export interface Pessoa {
  id: string
  nome: string
  papel: string | null
  email: string | null
  telefone: string | null
}

export interface Okr {
  id: string
  objetivo: string
  descricao: string | null
  status: 'ATIVO' | 'CONCLUIDO' | 'ARQUIVADO'
  kr1_descricao: string | null
  kr1_target: number | null
  kr1_atual: number | null
  kr2_descricao: string | null
  kr2_target: number | null
  kr2_atual: number | null
  kr3_descricao: string | null
  kr3_target: number | null
  kr3_atual: number | null
}

export interface Anexo {
  id: string
  tarefa_id: string
  nota_id: string | null
  nome_arquivo: string
  content_type: string | null
  tamanho_bytes: number | null
  criado_em: string
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
  responsavel_pessoa_id: string | null
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
  pessoas: Pessoa[]
  okrs: Okr[]
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
  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body?.detail || `Erro ${res.status}`)
  }
  return body as T
}

/** Upload multipart — sem Content-Type manual (o browser define o boundary). */
async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: form })
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
  anexos: (tarefaId: string) => ['playbooks', 'anexos', tarefaId] as const,
}

export interface PlaybookResumo {
  id: string
  projeto_id: string
  relatorio_id: string | null
  nome: string
  projeto_nome: string | null
  status: string
  data_inicio: string | null
  data_prevista_conclusao: string | null
  custo_planejado_total: number | null
  custo_real_total: number | null
  total_tarefas: number
  tarefas_concluidas: number
  percentual_concluido: number | null
  created_at: string
}

export function usePlaybooks() {
  return useQuery({
    queryKey: playbookKeys.all,
    queryFn: () => api<{ items: PlaybookResumo[] }>('/api/execucao/playbooks'),
    select: (r) => r.items,
    staleTime: 30_000,
  })
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

export function useGerarOkrs(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api<{ okrs_criados: number }>(`/api/execucao/playbooks/${playbookId}/okrs/gerar`, {
        method: 'POST',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useAtualizarOkr(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { okrId: string; kr1_atual?: number; kr2_atual?: number; kr3_atual?: number; status?: Okr['status'] } & Partial<NovaOkr>) => {
      const { okrId, ...campos } = vars
      return api<Okr>(`/api/execucao/okrs/${okrId}`, {
        method: 'PATCH',
        body: JSON.stringify(campos),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useCriarPessoa(playbookId: string, projetoId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { nome: string; papel?: string; email?: string; telefone?: string }) =>
      api<Pessoa>(`/api/execucao/projetos/${projetoId}/pessoas`, {
        method: 'POST',
        body: JSON.stringify(vars),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useAtualizarPessoa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { pessoaId: string; nome?: string; papel?: string; email?: string; telefone?: string }) => {
      const { pessoaId, ...campos } = vars
      return api<Pessoa>(`/api/execucao/pessoas/${pessoaId}`, {
        method: 'PATCH',
        body: JSON.stringify(campos),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useRemoverPessoa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pessoaId: string) =>
      api<void>(`/api/execucao/pessoas/${pessoaId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export interface NovaTarefa {
  titulo: string
  descricao?: string
  categoria: string
  custo_planejado?: number | null
  data_inicio?: string
  data_prevista_conclusao?: string
  responsavel_nome?: string
}

export function useCriarTarefa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: NovaTarefa) =>
      api<Tarefa>(`/api/execucao/playbooks/${playbookId}/tarefas`, {
        method: 'POST',
        body: JSON.stringify(vars),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useEditarTarefa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { tarefaId: string } & Partial<NovaTarefa>) => {
      const { tarefaId, ...campos } = vars
      return api<Tarefa>(`/api/execucao/tarefas/${tarefaId}/detalhes`, {
        method: 'PATCH',
        body: JSON.stringify(campos),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useExcluirTarefa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (tarefaId: string) =>
      api<void>(`/api/execucao/tarefas/${tarefaId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useAdicionarChecklistItem(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { tarefaId: string; descricao: string }) =>
      api<ChecklistItem>(`/api/execucao/tarefas/${vars.tarefaId}/checklist`, {
        method: 'POST',
        body: JSON.stringify({ descricao: vars.descricao }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useExcluirChecklistItem(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) =>
      api<void>(`/api/execucao/checklist/${itemId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export interface NovaOkr {
  objetivo: string
  descricao?: string
  kr1_descricao?: string
  kr1_target?: number
  kr2_descricao?: string
  kr2_target?: number
  kr3_descricao?: string
  kr3_target?: number
}

export function useCriarOkr(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: NovaOkr) =>
      api<Okr>(`/api/execucao/playbooks/${playbookId}/okrs`, {
        method: 'POST',
        body: JSON.stringify(vars),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useExcluirOkr(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (okrId: string) =>
      api<void>(`/api/execucao/okrs/${okrId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useRegistrarGasto(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { tarefaId: string; custoRealCentavos: number }) =>
      api<Tarefa>(`/api/execucao/tarefas/${vars.tarefaId}/custo`, {
        method: 'PATCH',
        body: JSON.stringify({ custo_real: vars.custoRealCentavos }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useAtribuirResponsavelTarefa(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { tarefaId: string; pessoaId: string | null }) =>
      api<Tarefa>(`/api/execucao/tarefas/${vars.tarefaId}/responsavel`, {
        method: 'PATCH',
        body: JSON.stringify({ pessoa_id: vars.pessoaId }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useAtribuirResponsavelChecklist(playbookId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { itemId: string; pessoaId: string | null }) =>
      api<ChecklistItem>(`/api/execucao/checklist/${vars.itemId}/responsavel`, {
        method: 'PATCH',
        body: JSON.stringify({ pessoa_id: vars.pessoaId }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: playbookKeys.detail(playbookId) }),
  })
}

export function useAnexosTarefa(tarefaId: string | null) {
  return useQuery({
    queryKey: playbookKeys.anexos(tarefaId ?? ''),
    enabled: Boolean(tarefaId),
    queryFn: () => api<{ items: Anexo[] }>(`/api/execucao/tarefas/${tarefaId}/anexos`),
    select: (r) => r.items,
    staleTime: 15_000,
  })
}

export function useEnviarAnexo(tarefaId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { arquivo: File; notaId?: string }) => {
      const form = new FormData()
      form.append('arquivo', vars.arquivo)
      if (vars.notaId) form.append('nota_id', vars.notaId)
      return apiUpload<Anexo>(`/api/execucao/tarefas/${tarefaId}/anexos`, form)
    },
    onSuccess: () => {
      if (tarefaId) qc.invalidateQueries({ queryKey: playbookKeys.anexos(tarefaId) })
    },
  })
}

export async function abrirAnexo(anexoId: string): Promise<void> {
  const r = await api<{ url: string }>(`/api/execucao/anexos/${anexoId}/download`)
  window.open(r.url, '_blank', 'noopener')
}

export function useExcluirAnexo(tarefaId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (anexoId: string) =>
      api<void>(`/api/execucao/anexos/${anexoId}`, { method: 'DELETE' }),
    onSuccess: () => {
      if (tarefaId) qc.invalidateQueries({ queryKey: playbookKeys.anexos(tarefaId) })
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
