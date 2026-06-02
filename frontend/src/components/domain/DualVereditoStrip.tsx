import { VeredictoBadge } from '@/components/domain/VeredictoBadge'
import { OceanoBadge } from '@/components/domain/OceanoBadge'
import { Badge } from '@/components/ui/badge'
import type { Veredito, VereditoOceano } from '@/types/domain'

/**
 * Duas lentes lado a lado: A6 viabilidade do ponto + A9 estratégia de mercado.
 */
export function DualVereditoStrip({
  vereditoViabilidade,
  vereditoOceano,
  className,
}: {
  vereditoViabilidade: Veredito | null | undefined
  vereditoOceano: VereditoOceano | string | null | undefined
  className?: string
}) {
  return (
    <div
      className={className}
      role="group"
      aria-label="Vereditos de viabilidade e posicionamento"
    >
      <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-muted/30 px-4 py-3">
        <div className="flex flex-col gap-1 min-w-[140px]">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Viabilidade (A6)
          </span>
          {vereditoViabilidade ? (
            <VeredictoBadge veredito={vereditoViabilidade} />
          ) : (
            <Badge variant="outline">Sem veredito</Badge>
          )}
        </div>
        <div className="hidden sm:block w-px h-10 bg-border" aria-hidden />
        <div className="flex flex-col gap-1 min-w-[140px]">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Mercado (A9)
          </span>
          <OceanoBadge veredito={vereditoOceano} />
        </div>
      </div>
    </div>
  )
}
