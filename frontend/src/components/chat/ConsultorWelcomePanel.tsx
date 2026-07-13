import { ArrowRight } from 'lucide-react'
import { ChatMiniCard } from '@/components/chat/ChatMiniCard'
import { ConsultorAgentAvatar } from '@/components/chat/ConsultorAgentAvatar'
import { copyDegustacao, type Especialista } from '@/config/consultor-agentes'
import { CONSULTOR_COPY } from '@/config/gymsite-design-system'

interface ConsultorWelcomePanelProps {
  especialista: Especialista
  onSend: (text: string) => void
}

export function ConsultorWelcomePanel({ especialista, onSend }: ConsultorWelcomePanelProps) {
  const meta = copyDegustacao(especialista.id)
  const contextoPesquisas = 'contextoPesquisas' in meta ? meta.contextoPesquisas : undefined

  return (
    <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center px-2 py-8 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border bg-card shadow-inner">
        <ConsultorAgentAvatar Icone={especialista.Icone} isActive size="tile" />
      </div>

      <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
        {CONSULTOR_COPY.tagline}
      </span>
      <h2 className="mt-1.5 font-display text-xl font-bold text-foreground">
        Especialista em {especialista.nome}
      </h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{especialista.saudacao}</p>

      <div className="mt-5 w-full rounded-2xl border bg-card p-4 text-left">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Sugestão técnica</span>
          <span className="font-mono text-[9px] text-muted-foreground">exemplo por especialidade</span>
        </div>
        <p className="rounded-lg border border-border/80 bg-background p-3 text-xs italic leading-relaxed text-foreground">
          &ldquo;{especialista.exemploPergunta}&rdquo;
        </p>
        <button
          type="button"
          onClick={() => onSend(especialista.exemploPergunta)}
          className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-primary outline-none transition-colors hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          Usar pergunta exemplo
          <ArrowRight className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>

      {contextoPesquisas?.length ? (
        <div className="mt-4 w-full text-left">
          <span className="mb-2 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            O que este consultor cruza
          </span>
          <div className="flex flex-wrap gap-1.5">
            {contextoPesquisas.map((item) => (
              <span
                key={item}
                className="rounded-md border border-border/70 bg-muted/30 px-2 py-0.5 text-[10px] text-muted-foreground"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-3">
        {CONSULTOR_COPY.miniCards.map((card) => (
          <ChatMiniCard key={card.kicker} kicker={card.kicker} detail={card.detail} />
        ))}
      </div>
    </div>
  )
}
