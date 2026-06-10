/**
 * useConversationalChat — hook para o Agente de IA Especialista em Fitness.
 *
 * Substitui o formulário tradicional por slot-filling conversacional.
 * Persiste mensagens no Supabase (tabela messages).
 */
import { useState, useCallback } from 'react'
import { API_BASE } from '@/lib/supabase'
import { supabase } from '@/lib/supabase'
import type { ChatAttachment } from '@/components/chat/ChatInput'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  attachments?: ChatAttachment[]
}

export interface ChatSessionItem {
  id: string
  title: string
  updatedAt: string
  status: string
}

export interface ConversationalState {
  sessionId: string | null
  intencao: string
  slots: Record<string, unknown>
  slotsFaltando: string[]
  status: string
  relatorioId: string | null
}

export interface UseConversationalChatReturn {
  messages: ChatMessage[]
  sessions: ChatSessionItem[]
  state: ConversationalState
  sendMessage: (text: string, attachments?: ChatAttachment[]) => Promise<void>
  isLoading: boolean
  error: string | null
  newSession: () => void
  selectSession: (id: string) => Promise<void>
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useConversationalChat(): UseConversationalChatReturn {
  const [sessions, setSessions] = useState<ChatSessionItem[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: generateId(),
      role: 'assistant',
      content:
        'Olá! Sou seu Agente de IA especialista em expansão de franquias de academia.\n\n' +
        'Posso preparar uma análise completa de viabilidade para qualquer cidade e bairro do Brasil. ' +
        'Para começar, me diga: em qual cidade e bairro você está pensando em abrir?',
      timestamp: new Date(),
    },
  ])
  const [state, setState] = useState<ConversationalState>({
    sessionId: null,
    intencao: '',
    slots: {},
    slotsFaltando: [],
    status: 'coletando_slots',
    relatorioId: null,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const saveMessage = useCallback(async (message: ChatMessage, sessionId: string) => {
    const { error: supaError } = await supabase.from('messages').insert({
      session_id: sessionId,
      role: message.role,
      content: message.content,
      timestamp: message.timestamp.toISOString(),
      attachments: message.attachments || [],
    })
    if (supaError) {
      console.error('Erro ao salvar mensagem:', supaError)
    }
  }, [])

  const fetchMessages = useCallback(async (sessionId: string): Promise<ChatMessage[]> => {
    const { data, error: supaError } = await supabase
      .from('messages')
      .select('*')
      .eq('session_id', sessionId)
      .order('timestamp', { ascending: true })
    if (supaError) {
      console.error('Erro ao buscar mensagens:', supaError)
      return []
    }
    return (data || []).map((m) => ({
      id: m.id,
      role: m.role as 'user' | 'assistant',
      content: m.content,
      timestamp: new Date(m.timestamp),
      attachments: m.attachments || [],
    }))
  }, [])

  const sendMessage = useCallback(
    async (text: string, _attachments?: ChatAttachment[]) => {
      if (!text.trim()) return
      setError(null)

      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date(),
        attachments: _attachments,
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        const { data: sessionData } = await supabase.auth.getSession()
        const token = sessionData.session?.access_token
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        }
        if (token) {
          headers.Authorization = `Bearer ${token}`
        }

        const res = await fetch(`${API_BASE}/api/assistente/conversar`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            mensagem: text.trim(),
            session_id: state.sessionId,
          }),
          signal: AbortSignal.timeout(60_000),
        })

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}))
          throw new Error(errBody.detail || `Erro ${res.status}`)
        }

        const data = (await res.json()) as {
          session_id: string
          intencao: string
          slots: Record<string, unknown>
          slots_faltando: string[]
          resposta: string
          relatorio_id: string | null
          status: string
        }

        setState({
          sessionId: data.session_id,
          intencao: data.intencao,
          slots: data.slots,
          slotsFaltando: data.slots_faltando,
          status: data.status,
          relatorioId: data.relatorio_id,
        })

        // Persiste mensagem do usuário
        if (data.session_id) {
          await saveMessage(userMsg, data.session_id)
        }

        // Atualiza ou cria sessão na lista lateral
        setSessions((prev) => {
          const exists = prev.find((s) => s.id === data.session_id)
          const title = data.slots?.cidade
            ? `Análise — ${data.slots.cidade}`
            : text.trim().slice(0, 30)
          if (exists) {
            return prev.map((s) =>
              s.id === data.session_id
                ? { ...s, title, updatedAt: new Date().toISOString(), status: data.status }
                : s
            )
          }
          return [
            {
              id: data.session_id,
              title,
              updatedAt: new Date().toISOString(),
              status: data.status,
            },
            ...prev,
          ]
        })

        const assistantMsg: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: data.resposta,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])

        // Persiste mensagem do assistente
        if (data.session_id) {
          await saveMessage(assistantMsg, data.session_id)
        }
      } catch (e: any) {
        setError(e?.message || 'Erro ao conversar com o agente.')
      } finally {
        setIsLoading(false)
      }
    },
    [state.sessionId, saveMessage]
  )

  const newSession = useCallback(() => {
    setMessages([
      {
        id: generateId(),
        role: 'assistant',
        content:
          'Olá! Sou seu Agente de IA especialista em expansão de franquias de academia.\n\n' +
          'Posso preparar uma análise completa de viabilidade para qualquer cidade e bairro do Brasil. ' +
          'Para começar, me diga: em qual cidade e bairro você está pensando em abrir?',
        timestamp: new Date(),
      },
    ])
    setState({
      sessionId: null,
      intencao: '',
      slots: {},
      slotsFaltando: [],
      status: 'coletando_slots',
      relatorioId: null,
    })
    setError(null)
  }, [])

  const selectSession = useCallback(
    async (id: string) => {
      setState((prev) => ({ ...prev, sessionId: id }))
      const msgs = await fetchMessages(id)
      if (msgs.length > 0) {
        setMessages(msgs)
      }
    },
    [fetchMessages]
  )

  return { messages, sessions, state, sendMessage, isLoading, error, newSession, selectSession }
}
