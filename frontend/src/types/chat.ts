import type { CarimboCitacao } from '@/components/chat/CitationStamp'

export interface ChatAcao {
  ferramenta: string
  status: string
  resumo: string
}

export interface ChatMessageData {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  attachments?: { id: string; file: File; preview?: string }[]
  /** id em chat_interacoes — presente só em respostas Q&A logadas */
  interacaoId?: string
  /** ferramentas que rodaram no turno (acoes_executadas) — handoff vive na sidebar do consultor */
  acoes?: ChatAcao[]
  /** id público do agente ADK (poll) — prioridade sobre inferência por tool */
  agenteId?: string | null
  citacoes?: CarimboCitacao[]
}
