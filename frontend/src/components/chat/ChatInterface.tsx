/**
 * ChatInterface — componente conversacional do Agente de IA Especialista em Fitness.
 *
 * Usa shadcn/ui (Card, Button, Input, Avatar) + Tailwind.
 * Substitui o formulário tradicional por slot-filling via chat natural.
 */
import { useRef, useEffect, useState } from 'react'
import { Send, Loader2, Trash2, Bot, User, FileText, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useConversationalChat, type ChatMessage } from '@/hooks/useConversationalChat'
import { Link } from '@tanstack/react-router'

function ChatBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className={isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground'
        }`}
      >
        <p>{msg.content}</p>
        <span className="mt-1 block text-[10px] opacity-60">
          {msg.timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}

function PipelineStatusCard({ relatorioId }: { relatorioId: string }) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm">
      <div className="flex items-center gap-2 text-blue-800 font-medium">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Seu relatório está sendo preparado...</span>
      </div>
      <p className="mt-1 text-blue-600 text-xs">
        A análise completa de viabilidade está em andamento. Isso leva cerca de 3–5 minutos.
      </p>
      <div className="mt-2 flex gap-2">
        <Link
          to="/relatorios"
          className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
        >
          <FileText className="h-3 w-3" />
          Ver todos os relatórios
        </Link>
        <Link
          to="/relatorios/$relatorioId"
          params={{ relatorioId }}
          className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          Acompanhar este relatório
        </Link>
      </div>
    </div>
  )
}

export function ChatInterface() {
  const { messages, state, sendMessage, isLoading, error, newSession } = useConversationalChat()
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    const text = input.trim()
    setInput('')
    await sendMessage(text)
  }

  return (
    <Card className="flex h-[calc(100vh-8rem)] flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 border-b pb-4">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">GymSite Agent</CardTitle>
        </div>
        <Button variant="ghost" size="sm" onClick={newSession}>
          <Trash2 className="mr-1 h-4 w-4" />
          Limpar
        </Button>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4 p-4">
        <div className="flex-1 overflow-y-auto pr-2" ref={scrollRef}>
          <div className="flex flex-col gap-4">
            {messages.map((msg) => (
              <ChatBubble key={msg.id} msg={msg} />
            ))}
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-xs">Analisando...</span>
              </div>
            )}
            {state.status === 'pipeline_rodando' && state.relatorioId && (
              <PipelineStatusCard relatorioId={state.relatorioId} />
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            placeholder="Digite sua mensagem..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
