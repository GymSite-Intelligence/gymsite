/**
 * useConsultorChat — hook do Consultor V2 (Jarvis).
 *
 * Espelha useConversationalChat (V1), mas fala com `/api/consultor/*`:
 * - POST /conversar           → resposta + estado do projeto (pesquisas, custo, sugestões)
 * - POST /projetos/{id}/relatorio → dispara o pipeline A0–A9 formal
 *
 * Diferença do V1: o LLM decide POR TURNO quais ferramentas (A0–A4) chamar e
 * responde em segundos; o estado do projeto é acumulativo (persistido em
 * gymsite.user_projects). Auth via JWT do Supabase (header Authorization).
 */
import { useState, useCallback } from 'react'
import { API_BASE, supabase } from '@/lib/supabase'
import type { ChatMessageData } from '@/components/chat/ChatMessage'

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

export interface ConsultorAcao {
  ferramenta: string
  status: string
  resumo: string
}

interface ConversarResponse {
  projeto_id: string
  mensagem: string
  status: string
  acoes_executadas: ConsultorAcao[]
  sugestoes: string[]
  pode_gerar_relatorio: boolean
  dados_faltantes: string[]
  projeto: ConsultorProjeto
}

export interface UseConsultorChatReturn {
  messages: ChatMessageData[]
  projeto: ConsultorProjeto | null
  projetoId: string | null
  sugestoes: string[]
  dadosFaltantes: string[]
  podeGerarRelatorio: boolean
  isLoading: boolean
  isGeneratingReport: boolean
  error: string | null
  sendMessage: (text: string) => Promise<void>
  gerarRelatorio: () => Promise<string | null>
  novaConversa: () => void
}

const SAUDACAO =
  'Olá! Sou seu consultor de expansão de academias e franquias fitness. ' +
  'Me diga a cidade e o bairro que você está avaliando e eu pesquiso o ' +
  'mercado, a concorrência, o público e a viabilidade financeira em tempo real.'

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

export function useConsultorChat(): UseConsultorChatReturn {
  const [messages, setMessages] = useState<ChatMessageData[]>([saudacaoInicial()])
  const [projeto, setProjeto] = useState<ConsultorProjeto | null>(null)
  const [projetoId, setProjetoId] = useState<string | null>(null)
  const [sugestoes, setSugestoes] = useState<string[]>([])
  const [dadosFaltantes, setDadosFaltantes] = useState<string[]>([])
  const [podeGerarRelatorio, setPodeGerarRelatorio] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (text: string) => {
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

      try {
        const res = await fetch(`${API_BASE}/api/consultor/conversar`, {
          method: 'POST',
          headers: await authHeaders(),
          body: JSON.stringify({ mensagem: text.trim(), projeto_id: projetoId }),
          // tools A0–A4 rodam server-side e podem levar dezenas de segundos
          signal: AbortSignal.timeout(180_000),
        })

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}))
          throw new Error(errBody.detail || `Erro ${res.status}`)
        }

        const data = (await res.json()) as ConversarResponse

        setProjetoId(data.projeto_id)
        setProjeto(data.projeto)
        setSugestoes(data.sugestoes || [])
        setDadosFaltantes(data.dados_faltantes || [])
        setPodeGerarRelatorio(Boolean(data.pode_gerar_relatorio))

        const assistantMsg: ChatMessageData = {
          id: generateId(),
          role: 'assistant',
          content: data.mensagem,
          timestamp: new Date(),
          acoes: data.acoes_executadas,
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Erro ao falar com o consultor.'
        setError(msg.includes('timeout') ? 'A pesquisa demorou demais. Tente de novo.' : msg)
      } finally {
        setIsLoading(false)
      }
    },
    [isLoading, projetoId],
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
        setProjeto((p) => (p ? { ...p, relatorio_id: data.relatorio_id, status: 'CONSOLIDANDO' } : p))
        setMessages((prev) => [
          ...prev,
          { id: generateId(), role: 'assistant', content: data.mensagem, timestamp: new Date() },
        ])
      }
      return data.relatorio_id
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao gerar o relatório.')
      return null
    } finally {
      setIsGeneratingReport(false)
    }
  }, [projetoId, isGeneratingReport])

  const novaConversa = useCallback(() => {
    setMessages([saudacaoInicial()])
    setProjeto(null)
    setProjetoId(null)
    setSugestoes([])
    setDadosFaltantes([])
    setPodeGerarRelatorio(false)
    setError(null)
  }, [])

  return {
    messages,
    projeto,
    projetoId,
    sugestoes,
    dadosFaltantes,
    podeGerarRelatorio,
    isLoading,
    isGeneratingReport,
    error,
    sendMessage,
    gerarRelatorio,
    novaConversa,
  }
}
