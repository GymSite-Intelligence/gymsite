import { useRef, useEffect, useState, useCallback } from 'react'
import { Send, Loader2, Paperclip, X, FileText, Image as ImageIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

// Flag local até a extração de anexos existir no backend (ADR-005).
const SHOW_ATTACHMENTS_UI = false

export interface ChatAttachment {
  file: File
  id: string
  preview?: string
}

interface ChatInputProps {
  onSend: (text: string, attachments: ChatAttachment[]) => void
  isLoading: boolean
  disabled?: boolean
  placeholder?: string
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function getFileIcon(file: File) {
  if (file.type.startsWith('image/')) return <ImageIcon className="h-4 w-4" />
  return <FileText className="h-4 w-4" />
}

export function ChatInput({
  onSend,
  isLoading,
  disabled,
  placeholder = 'Mensagem GymSite Agent...',
}: ChatInputProps) {
  const [text, setText] = useState('')
  const [attachments, setAttachments] = useState<ChatAttachment[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [text])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (!files) return
      const newAttachments: ChatAttachment[] = []
      Array.from(files).forEach((file) => {
        const att: ChatAttachment = { file, id: generateId() }
        if (file.type.startsWith('image/')) {
          att.preview = URL.createObjectURL(file)
        }
        newAttachments.push(att)
      })
      setAttachments((prev) => [...prev, ...newAttachments])
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    [],
  )

  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => {
      const att = prev.find((a) => a.id === id)
      if (att?.preview) URL.revokeObjectURL(att.preview)
      return prev.filter((a) => a.id !== id)
    })
  }, [])

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if ((!text.trim() && attachments.length === 0) || isLoading || disabled) return
    onSend(text.trim(), attachments)
    setText('')
    attachments.forEach((a) => {
      if (a.preview) URL.revokeObjectURL(a.preview)
    })
    setAttachments([])
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t bg-background px-3 py-3 sm:px-6 lg:px-8"
    >
      {/* Previews dos anexos */}
      {attachments.length > 0 && (
        <div className="mx-auto mb-2 flex max-w-3xl flex-wrap gap-2">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="group relative flex items-center gap-2 rounded-lg border bg-muted/50 px-2.5 py-1.5 text-xs"
            >
              {att.preview ? (
                <img
                  src={att.preview}
                  alt={att.file.name}
                  className="h-8 w-8 rounded object-cover"
                />
              ) : (
                <span className="text-muted-foreground">{getFileIcon(att.file)}</span>
              )}
              <span className="max-w-[120px] truncate">{att.file.name}</span>
              <button
                type="button"
                onClick={() => removeAttachment(att.id)}
                className="ml-1 rounded-full p-0.5 hover:bg-muted"
              >
                <X className="h-3 w-3 text-muted-foreground" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border bg-muted/50 p-2 focus-within:ring-1 focus-within:ring-primary/30">
        {/* Upload oculto até a extração de anexos existir (ADR-005): aceitar
            arquivo que o backend ignora cria expectativa quebrada. Reativar
            junto com Gemini Vision (gates T05.1-T05.5). */}
        {SHOW_ATTACHMENTS_UI && (
          <>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={disabled || isLoading}
              className="h-9 w-9 shrink-0 rounded-xl text-muted-foreground hover:text-foreground"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="h-4 w-4" />
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv"
              className="hidden"
              onChange={handleFileSelect}
            />
          </>
        )}

        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={placeholder}
          className="max-h-[200px] min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2.5 text-sm outline-none placeholder:text-muted-foreground/60 disabled:opacity-50"
        />

        <Button
          type="submit"
          size="icon"
          disabled={(!text.trim() && attachments.length === 0) || isLoading || disabled}
          className="h-9 w-9 shrink-0 rounded-xl"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
      <p className="mt-1.5 text-center text-[10px] text-muted-foreground/60">
        O Agente pode cometer erros. Verifique informações críticas.
      </p>
    </form>
  )
}
