import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, User, Copy, Check, RotateCcw, FileText, ThumbsUp, ThumbsDown } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { useIsAdmin } from '@/hooks/useIsAdmin'

export interface ChatMessageData {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  attachments?: { id: string; file: File; preview?: string }[]
  /** id em chat_interacoes — presente só em respostas Q&A logadas */
  interacaoId?: string
}

interface ChatMessageProps {
  msg: ChatMessageData
  onRegenerate?: () => void
  /** Avaliação admin → dataset de fine-tuning. Retorna true se gravou. */
  onFeedback?: (interacaoId: string, rating: 1 | -1) => Promise<boolean>
}

function CodeBlock({ children, className }: { children: React.ReactNode; className?: string }) {
  const isInline = !className
  if (isInline) {
    return (
      <code className="rounded bg-muted px-1 py-0.5 text-sm font-mono text-foreground">
        {children}
      </code>
    )
  }
  return (
    <div className="my-2 overflow-hidden rounded-lg border bg-muted">
      <div className="flex items-center justify-between bg-muted/80 px-3 py-1.5 text-xs text-muted-foreground">
        <span>{className.replace('language-', '')}</span>
      </div>
      <pre className="overflow-x-auto p-3 text-sm">
        <code className="font-mono">{children}</code>
      </pre>
    </div>
  )
}

export function ChatMessage({ msg, onRegenerate, onFeedback }: ChatMessageProps) {
  const isUser = msg.role === 'user'
  const isAdmin = useIsAdmin()
  const [copied, setCopied] = useState(false)
  const [rated, setRated] = useState<1 | -1 | null>(null)
  const [rating, setRating] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleFeedback = async (value: 1 | -1) => {
    if (!onFeedback || !msg.interacaoId || rating || rated !== null) return
    setRating(true)
    const ok = await onFeedback(msg.interacaoId, value)
    if (ok) setRated(value)
    setRating(false)
  }

  return (
    <div
      className={`group flex gap-3 px-4 py-5 sm:px-6 lg:px-8 ${
        isUser ? 'bg-background' : 'bg-muted/30'
      }`}
    >
      <Avatar className="mt-0.5 h-7 w-7 shrink-0 sm:h-8 sm:w-8">
        <AvatarFallback
          className={
            isUser
              ? 'bg-primary text-primary-foreground text-xs'
              : 'bg-emerald-100 text-emerald-700 text-xs'
          }
        >
          {isUser ? <User className="h-3.5 w-3.5 sm:h-4 sm:w-4" /> : <Bot className="h-3.5 w-3.5 sm:h-4 sm:w-4" />}
        </AvatarFallback>
      </Avatar>

      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-sm font-semibold">
            {isUser ? 'Você' : 'GymSite Agent'}
          </span>
          <span className="text-[11px] text-muted-foreground">
            {msg.timestamp.toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>

        <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code: CodeBlock as any,
              p: ({ children }) => <p className="leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
              li: ({ children }) => <li>{children}</li>,
              strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
              h1: ({ children }) => <h1 className="text-lg font-bold mt-3 mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-primary/30 pl-3 italic text-muted-foreground my-2">
                  {children}
                </blockquote>
              ),
            }}
          >
            {msg.content}
          </ReactMarkdown>
        </div>

        {/* Anexos */}
        {msg.attachments && msg.attachments.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {msg.attachments.map((att) => (
              <div
                key={att.id}
                className="flex items-center gap-2 rounded-lg border bg-muted/50 px-2.5 py-1.5 text-xs"
              >
                {att.preview ? (
                  <img
                    src={att.preview}
                    alt={att.file.name}
                    className="h-8 w-8 rounded object-cover"
                  />
                ) : (
                  <FileText className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="max-w-[120px] truncate">{att.file.name}</span>
              </div>
            ))}
          </div>
        )}

        {!isUser && (
          <div className="mt-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleCopy}
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? 'Copiado' : 'Copiar'}
            </Button>
            {onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
                onClick={onRegenerate}
              >
                <RotateCcw className="h-3 w-3" />
                Regenerar
              </Button>
            )}
            {/* Avaliação admin → alimenta dataset de fine-tuning (chat_interacoes) */}
            {isAdmin && onFeedback && msg.interacaoId && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={rating || rated !== null}
                  className={`h-7 gap-1 text-xs ${
                    rated === 1
                      ? 'text-emerald-600'
                      : 'text-muted-foreground hover:text-emerald-600'
                  }`}
                  onClick={() => handleFeedback(1)}
                  title="Resposta boa — entra no dataset de treino"
                >
                  <ThumbsUp className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={rating || rated !== null}
                  className={`h-7 gap-1 text-xs ${
                    rated === -1
                      ? 'text-red-600'
                      : 'text-muted-foreground hover:text-red-600'
                  }`}
                  onClick={() => handleFeedback(-1)}
                  title="Resposta ruim"
                >
                  <ThumbsDown className="h-3 w-3" />
                </Button>
                {rated !== null && (
                  <span className="self-center text-[10px] text-muted-foreground">
                    avaliado
                  </span>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
