import { Separator } from '@/components/ui/separator'
import { HANDOFF_COPY } from '@/config/gymsite-design-system'
import type { Especialista } from '@/config/consultor-agentes'

interface CabecalhoHandoffProps {
  anterior: Especialista
  atual: Especialista
}

export function CabecalhoHandoff({ anterior, atual }: CabecalhoHandoffProps) {
  return (
    <div
      role="status"
      className="mb-3 flex animate-in fade-in slide-in-from-top-2 items-center gap-3 text-xs text-muted-foreground duration-300"
    >
      <Separator className="flex-1" />
      <span className="max-w-[min(100%,300px)] text-center italic leading-snug">
        <span aria-hidden className="not-italic">
          🔄{' '}
        </span>
        {HANDOFF_COPY.prefixo} {HANDOFF_COPY.template(anterior.nome, atual.nome)}
      </span>
      <Separator className="flex-1" />
    </div>
  )
}
