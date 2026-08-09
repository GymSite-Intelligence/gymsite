import { User } from 'lucide-react'
import { renderRich } from '@/components/chat/render-rich'
import { CitationStamp } from '@/components/chat/CitationStamp'
import { CabecalhoHandoff } from '@/components/chat/CabecalhoHandoff'
import { ConsultorAgentAvatar } from '@/components/chat/ConsultorAgentAvatar'
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
        <div className="flex max-w-[85%] items-start gap-2">
          <div className="inline-block rounded-2xl bg-primary px-4 py-2 text-sm font-medium leading-relaxed text-primary-foreground">
            {msg.content}
          </div>
          <span
            className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"
            aria-hidden
          >
            <User className="h-3.5 w-3.5" />
          </span>
        </div>
      </div>
    )
  }

  const especialista = especialistaDaMensagem(msg.acoes, msg.agenteId)
  const handoff = especialistaAnterior && especialistaAnterior.id !== especialista.id

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%]">
        {handoff && (
          <CabecalhoHandoff anterior={especialistaAnterior!} atual={especialista} />
        )}
        <div className="mb-1 flex items-center gap-1.5 text-xs">
          <ConsultorAgentAvatar
            Icone={especialista.Icone}
            imgSrc={especialista.img}
            isActive
            size="inline"
          />
          <span className="font-medium text-foreground">{especialista.nome}</span>
          <span className="text-muted-foreground">· {especialista.especialidade}</span>
        </div>
        <div className="inline-block rounded-2xl bg-secondary px-4 py-2 text-sm leading-relaxed text-foreground">
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
