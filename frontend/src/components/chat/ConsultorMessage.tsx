import { renderRich } from '@/components/chat/render-rich'
import { CitationStamp } from '@/components/chat/CitationStamp'
import { especialistaDaMensagem, type Especialista } from '@/config/consultor-agentes'
import type { ChatMessageData } from '@/components/chat/ChatMessage'

interface ConsultorMessageProps {
  msg: ChatMessageData
  especialistaAnterior?: Especialista
}

export function ConsultorMessage({ msg, especialistaAnterior }: ConsultorMessageProps) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[92%] sm:max-w-[85%]">
          <div className="inline-block wrap-break-word rounded-2xl bg-lime px-3 py-2 text-sm font-medium leading-relaxed text-primary-foreground sm:px-4">
            {msg.content}
          </div>
        </div>
      </div>
    )
  }

  const especialista = especialistaDaMensagem(msg.acoes, msg.agenteId)
  const handoff = especialistaAnterior && especialistaAnterior.id !== especialista.id

  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] sm:max-w-[85%]">
        {handoff && (
          <div className="mb-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="text-lime">↝</span>
            <span>
              <span className="font-medium text-foreground">{especialistaAnterior.nome}</span> passou o
              bastão pro <span className="font-medium text-foreground">{especialista.nome}</span>
            </span>
          </div>
        )}
        <div className="mb-1 flex items-center gap-1.5 text-xs">
          <img src={especialista.img} alt="" className="h-6 w-6 shrink-0 object-contain" />
          <span className="font-medium text-foreground">{especialista.nome}</span>
          <span className="truncate text-muted-foreground">· {especialista.especialidade}</span>
        </div>
        <div className="inline-block wrap-break-word rounded-2xl bg-secondary px-3 py-2 text-sm leading-relaxed text-foreground sm:px-4">
          {renderRich(msg.content)}
        </div>
        {msg.citacoes?.length ? (
          <div className="space-y-2">
            {msg.citacoes.map((citacao, i) => (
              <CitationStamp key={i} citacao={citacao} />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
