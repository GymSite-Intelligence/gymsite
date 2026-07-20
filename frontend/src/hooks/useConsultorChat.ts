/**
 * useConsultorChat — hook do Consultor V2 (ADK async + poll).
 */
import { useState, useCallback, useEffect, useRef } from 'react'
import type { ChatMessageData } from '@/components/chat/ChatMessage'
import type { CarimboCitacao } from '@/components/chat/CitationStamp'
import type { AgenteApiId } from '@/config/site-agent-map'
import { conversarConsultor, pollConsultorMensagens } from '@/lib/consultor-agent-client'
import {
  cacheSession,
  downloadSessionJson,
  loadCachedSession,
  mergeServerSessions,
  setActiveProjetoId,
  type ConsultorSessionItem,
} from '@/lib/consultor-sessions'
import { API_BASE, supabase } from '@/lib/supabase'

export interface ConsultorPesquisas {
  mercado: boolean
  concorrentes: boolean
  reviews: boolean
  oferta_concorrentes: boolean
  demografia: boolean
  pontos_comerciais: boolean
  investimento: boolean
}

export interface ConsultorProjeto {
  id: string
  status: string
  localizacao: { cidade?: string; bairro?: string; uf?: string }
  modelo_negocio: Record<string, unknown>
  pesquisas_realizadas: ConsultorPesquisas
  total_concorrentes: number | null
  custo_brl_ate_agora: number
  pode_gerar_relatorio: boolean
  relatorio_id: string | null
}

interface ProjetoListItem {
  id: string
  status: string
  cidade?: string
  bairro?: string
  uf?: string
  updated_at: string
}

interface ProjetoDetailResponse {
  projeto: {
    id: string
    status: string
    localizacao: ConsultorProjeto['localizacao']
    modelo_negocio: Record<string, unknown>
    pesquisas_realizadas: ConsultorPesquisas
    custo_brl_ate_agora: number
    relatorio_id: string | null
    updated_at: string
  }
  mensagens: {
    id: string
    role: 'user' | 'assistant'
    content: string
    tool_calls?: { ferramenta: string; status: string; resumo: string }[]
    citacoes?: CarimboCitacao[]
    agente?: string | null
    created_at: string
  }[]
}

export interface UseConsultorChatReturn {
  messages: ChatMessageData[]
  projeto: ConsultorProjeto | null
  projetoId: string | null
  sessions: ConsultorSessionItem[]
  sugestoes: string[]
  dadosFaltantes: string[]
  podeGerarRelatorio: boolean
  isLoading: boolean
  isGeneratingReport: boolean
  isLoadingSessions: boolean
  error: string | null
  sendMessage: (text: string, agente?: AgenteApiId) => Promise<void>
  gerarRelatorio: () => Promise<string | null>
  novaConversa: () => void
  selectSession: (id: string) => Promise<void>
  exportJson: () => void
}

const SAUDACAO =
  'Olá! Sou seu consultor de expansão de academias e franquias fitness. ' +
  'Me diga a cidade e o bairro que você está avaliando e eu pesquiso o ' +
  'mercado, a concorrência, o público e a viabilidade financeira em tempo real.'

const POLL_MS = 240_000
const POLL_INTERVAL = 2500

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function saudacaoInicial(): ChatMessageData {
  return { id: generateId(), role: 'assistant', content: SAUDACAO, timestamp: new Date() }
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

function pesquisasDefault(): ConsultorPesquisas {
  return {
    mercado: false,
    concorrentes: false,
    reviews: false,
    oferta_concorrentes: false,
    demografia: false,
    pontos_comerciais: false,
    investimento: false,
  }
}

function projetoFromPoll(
  id: string,
  p: {
    status: string
    localizacao: ConsultorProjeto['localizacao']
    modelo_negocio: Record<string, unknown>
    pesquisas_realizadas: ConsultorPesquisas
    custo_brl_ate_agora: number
    relatorio_id: string | null
    pode_gerar_relatorio: boolean
  },
): ConsultorProjeto {
  return {
    id,
    status: p.status,
    localizacao: p.localizacao ?? {},
    modelo_negocio: p.modelo_negocio ?? {},
    pesquisas_realizadas: p.pesquisas_realizadas ?? pesquisasDefault(),
    total_concorrentes: null,
    custo_brl_ate_agora: p.custo_brl_ate_agora ?? 0,
    pode_gerar_relatorio: Boolean(p.pode_gerar_relatorio),
    relatorio_id: p.relatorio_id,
  }
}

function projetoFromDetail(d: ProjetoDetailResponse['projeto']): ConsultorProjeto {
  return {
    id: d.id,
    status: d.status,
    localizacao: d.localizacao ?? {},
    modelo_negocio: d.modelo_negocio ?? {},
    pesquisas_realizadas: d.pesquisas_realizadas ?? pesquisasDefault(),
    total_concorrentes: null,
    custo_brl_ate_agora: d.custo_brl_ate_agora ?? 0,
    pode_gerar_relatorio: false,
    relatorio_id: d.relatorio_id,
  }
}

function messagesFromApi(mensagens: ProjetoDetailResponse['mensagens']): ChatMessageData[] {
  if (!mensagens.length) return [saudacaoInicial()]
  return mensagens.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: new Date(m.created_at),
    agenteId: m.agente ?? null,
    acoes: m.tool_calls?.map((t) => ({
      ferramenta: t.ferramenta,
      status: t.status,
      resumo: t.resumo,
    })),
    citacoes: m.citacoes,
  }))
}

function sessionFromListItem(p: ProjetoListItem): ConsultorSessionItem {
  const parts = [p.bairro, p.cidade, p.uf].filter(Boolean)
  return {
    id: p.id,
    title: parts.length ? parts.join(', ') : 'Nova conversa',
    updatedAt: p.updated_at,
    status: p.status,
  }
}

function sugestoesFromProjeto(projeto: ConsultorProjeto | null): string[] {
  if (!projeto) return []
  const pesq = projeto.pesquisas_realizadas
  const out: string[] = []
  if (!pesq.concorrentes) out.push('Pesquisar concorrentes na região')
  if (pesq.concorrentes && !pesq.reviews) out.push('Analisar reviews e dores dos alunos')
  if (!pesq.investimento && projeto.localizacao?.cidade) out.push('Estimar investimento inicial')
  if (!pesq.demografia) out.push('Analisar o perfil demográfico do bairro')
  if (pesq.concorrentes && pesq.reviews && pesq.investimento) {
    out.push('Gerar Relatório Formal de Viabilidade')
  }
  return out.slice(0, 3)
}

export function useConsultorChat(): UseConsultorChatReturn {
  const [messages, setMessages] = useState<ChatMessageData[]>([saudacaoInicial()])
  const [projeto, setProjeto] = useState<ConsultorProjeto | null>(null)
  const [projetoId, setProjetoId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ConsultorSessionItem[]>([])
  const [sugestoes, setSugestoes] = useState<string[]>([])
  const [dadosFaltantes, setDadosFaltantes] = useState<string[]>([])
  const [podeGerarRelatorio, setPodeGerarRelatorio] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [isLoadingSessions, setIsLoadingSessions] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollAbort = useRef<AbortController | null>(null)

  const refreshSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/consultor/projetos`, {
        headers: await authHeaders(),
      })
      if (!res.ok) return
      const data = (await res.json()) as { projetos: ProjetoListItem[] }
      setSessions(mergeServerSessions((data.projetos ?? []).map(sessionFromListItem)))
    } catch {
      setSessions(mergeServerSessions([]))
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setIsLoadingSessions(true)
      await refreshSessions()
      if (!cancelled) setIsLoadingSessions(false)
    })()
    return () => {
      cancelled = true
    }
  }, [refreshSessions])

  const hydrateFromProjeto = useCallback(async (id: string, preferCache = false) => {
    setError(null)
    setSugestoes([])
    setActiveProjetoId(id)

    if (preferCache) {
      const cached = loadCachedSession(id)
      if (cached) {
        setProjetoId(id)
        setProjeto(cached.projetoSnapshot)
        setMessages(cached.messagesSnapshot)
        setPodeGerarRelatorio(Boolean(cached.projetoSnapshot?.pode_gerar_relatorio))
        return
      }
    }

    const res = await fetch(`${API_BASE}/api/consultor/projetos/${id}`, {
      headers: await authHeaders(),
    })
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}))
      throw new Error(errBody.detail || `Erro ${res.status}`)
    }
    const data = (await res.json()) as ProjetoDetailResponse
    const p = projetoFromDetail(data.projeto)
    const msgs = messagesFromApi(data.mensagens)
    setProjetoId(id)
    setProjeto(p)
    setMessages(msgs)
    setPodeGerarRelatorio(false)
    setSugestoes(sugestoesFromProjeto(p))
    cacheSession(id, msgs, p)
  }, [])

  const selectSession = useCallback(
    async (id: string) => {
      if (id === projetoId || isLoading) return
      setIsLoading(true)
      try {
        await hydrateFromProjeto(id, true)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Erro ao carregar conversa.')
      } finally {
        setIsLoading(false)
      }
    },
    [hydrateFromProjeto, isLoading, projetoId],
  )

  const sendMessage = useCallback(
    async (text: string, agente: AgenteApiId = 'degustacao') => {
      if (!text.trim() || isLoading) return
      setError(null)
      setSugestoes([])

      const userMsg: ChatMessageData = {
        id: generateId(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      const desde = new Date().toISOString()
      pollAbort.current?.abort()
      pollAbort.current = new AbortController()

      try {
        const { projeto_id } = await conversarConsultor(text.trim(), projetoId, agente)
        setProjetoId(projeto_id)

        const t0 = Date.now()
        while (Date.now() - t0 < POLL_MS) {
          if (pollAbort.current.signal.aborted) return
          await new Promise((r) => setTimeout(r, POLL_INTERVAL))
          const p = await pollConsultorMensagens(projeto_id, desde)
          const ans = p.mensagens.filter((x) => x.role === 'assistant')
          if (ans.length) {
            const ultima = ans[ans.length - 1]
            const snap = projetoFromPoll(projeto_id, p)
            setProjeto(snap)
            setPodeGerarRelatorio(Boolean(p.pode_gerar_relatorio))
            setSugestoes(sugestoesFromProjeto(snap))

            const faltantes: string[] = []
            if (!p.localizacao?.cidade) faltantes.push('cidade')
            if (!p.localizacao?.bairro) faltantes.push('bairro')
            setDadosFaltantes(faltantes)

            const assistantMsg: ChatMessageData = {
              id: generateId(),
              role: 'assistant',
              content: ultima.content,
              timestamp: new Date(ultima.created_at),
              agenteId: ultima.agente ?? null,
              acoes: ultima.tool_calls?.map((t) => ({
                ferramenta: t.ferramenta,
                status: t.status,
                resumo: t.resumo,
              })),
              citacoes: ultima.citacoes,
            }
            setMessages((prev) => {
              const next = [...prev, assistantMsg]
              cacheSession(projeto_id, next, snap)
              return next
            })
            await refreshSessions()
            return
          }
        }
        setError('A pesquisa demorou mais que o esperado. Tente de novo.')
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Erro ao falar com o consultor.')
      } finally {
        setIsLoading(false)
      }
    },
    [isLoading, projetoId, refreshSessions],
  )

  const gerarRelatorio = useCallback(async (): Promise<string | null> => {
    if (!projetoId || isGeneratingReport) return null
    setError(null)
    setIsGeneratingReport(true)
    try {
      const res = await fetch(`${API_BASE}/api/consultor/projetos/${projetoId}/relatorio`, {
        method: 'POST',
        headers: await authHeaders(),
        body: JSON.stringify({ incluir_secoes: [] }),
        signal: AbortSignal.timeout(60_000),
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail || `Erro ${res.status}`)
      }
      const data = (await res.json()) as { relatorio_id: string | null; mensagem: string }
      if (data.relatorio_id) {
        const nextProjeto = projeto
          ? { ...projeto, relatorio_id: data.relatorio_id, status: 'CONSOLIDANDO' }
          : projeto
        setProjeto(nextProjeto)
        setMessages((prev) => {
          const updated = [
            ...prev,
            { id: generateId(), role: 'assistant' as const, content: data.mensagem, timestamp: new Date() },
          ]
          if (projetoId && nextProjeto) cacheSession(projetoId, updated, nextProjeto)
          return updated
        })
      }
      await refreshSessions()
      return data.relatorio_id
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao gerar o relatório.')
      return null
    } finally {
      setIsGeneratingReport(false)
    }
  }, [projetoId, isGeneratingReport, refreshSessions, projeto])

  const novaConversa = useCallback(() => {
    pollAbort.current?.abort()
    setMessages([saudacaoInicial()])
    setProjeto(null)
    setProjetoId(null)
    setSugestoes([])
    setDadosFaltantes([])
    setPodeGerarRelatorio(false)
    setError(null)
    setActiveProjetoId(null)
  }, [])

  const exportJson = useCallback(() => {
    downloadSessionJson({ projeto, projetoId, messages })
  }, [projeto, projetoId, messages])

  return {
    messages,
    projeto,
    projetoId,
    sessions,
    sugestoes,
    dadosFaltantes,
    podeGerarRelatorio,
    isLoading,
    isGeneratingReport,
    isLoadingSessions,
    error,
    sendMessage,
    gerarRelatorio,
    novaConversa,
    selectSession,
    exportJson,
  }
}
