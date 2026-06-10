/**
 * useAssistenteChat — hook para conversar com o GymSite Assistant (Tinker Bot).
 */
import { useState, useCallback } from 'react'
import { API_BASE } from '@/lib/supabase'
import { supabase } from '@/lib/supabase'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface UseAssistenteChatReturn {
  messages: ChatMessage[]
  sendMessage: (text: string, relatorioId?: string) => Promise<void>
  isLoading: boolean
  error: string | null
  clearChat: () => void
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useAssistenteChat(): UseAssistenteChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: generateId(),
      role: 'assistant',
      content:
        'Olá! Sou o GymSite Assistant. Posso ajudar com dúvidas sobre seus relatórios de viabilidade, dados de mercado, concorrência e muito mais. O que gostaria de saber?',
      timestamp: new Date(),
    },
  ])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (text: string, relatorioId?: string) => {
      if (!text.trim()) return
      setError(null)

      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date(),
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

        const res = await fetch(`${API_BASE}/api/assistente/chat`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            pergunta: text.trim(),
            relatorio_id: relatorioId ?? null,
          }),
          signal: AbortSignal.timeout(60_000),
        })

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}))
          throw new Error(errBody.detail || `Erro ${res.status}`)
        }

        const data = (await res.json()) as { resposta: string }
        const assistantMsg: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: data.resposta,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch (e: any) {
        setError(e?.message || 'Erro ao conversar com o assistente.')
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  const clearChat = useCallback(() => {
    setMessages([
      {
        id: generateId(),
        role: 'assistant',
        content:
          'Olá! Sou o GymSite Assistant. Posso ajudar com dúvidas sobre seus relatórios de viabilidade, dados de mercado, concorrência e muito mais. O que gostaria de saber?',
        timestamp: new Date(),
      },
    ])
    setError(null)
  }, [])

  return { messages, sendMessage, isLoading, error, clearChat }
}
