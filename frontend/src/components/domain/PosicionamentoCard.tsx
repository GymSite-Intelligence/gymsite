/**
 * PosicionamentoCard — output A9 (Framework ERRC / oceano azul).
 */
import { OceanoBadge } from '@/components/domain/OceanoBadge'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PosicionamentoEstrategicoJSON } from '@/hooks/useRelatorioDetail'

const ERRC_LABELS: { key: keyof NonNullable<PosicionamentoEstrategicoJSON['framework_errc']>; title: string; accent: string }[] = [
  { key: 'eliminar', title: 'Eliminar', accent: 'border-red-300 bg-red-50/50' },
  { key: 'reduzir', title: 'Reduzir', accent: 'border-amber-300 bg-amber-50/50' },
  { key: 'aumentar', title: 'Aumentar', accent: 'border-blue-300 bg-blue-50/50' },
  { key: 'criar', title: 'Criar', accent: 'border-emerald-300 bg-emerald-50/50' },
]

export interface PosicionamentoCardProps {
  data: PosicionamentoEstrategicoJSON
  className?: string
}

export function PosicionamentoCard({ data, className }: PosicionamentoCardProps) {
  if (data.erro) {
    return (
      <div className={cn('rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm', className)}>
        <p className="font-medium text-destructive">Posicionamento estratégico indisponível</p>
        <p className="mt-1 text-muted-foreground">{data.erro}</p>
      </div>
    )
  }

  const ticket = data.recomendacao_ticket
  const errc = data.framework_errc

  return (
    <div className={cn('space-y-6', className)}>
      <div className="flex flex-wrap items-center gap-3">
        <OceanoBadge veredito={data.veredito_posicionamento} />
        {ticket?.ticket_recomendado != null && (
          <span className="text-sm text-muted-foreground">
            Ticket recomendado:{' '}
            <strong className="text-foreground">R$ {ticket.ticket_recomendado}/mês</strong>
            {ticket.ticket_minimo != null && ticket.ticket_maximo != null && (
              <> (faixa R$ {ticket.ticket_minimo}–{ticket.ticket_maximo})</>
            )}
          </span>
        )}
      </div>

      {data.justificativa_veredito && (
        <p className="text-sm leading-relaxed text-muted-foreground">{data.justificativa_veredito}</p>
      )}

      {errc && (
        <div className="grid gap-3 sm:grid-cols-2">
          {ERRC_LABELS.map(({ key, title, accent }) => {
            const items = errc[key]
            if (!items?.length) return null
            return (
              <div key={key} className={cn('rounded-lg border p-4', accent)}>
                <h4 className="mb-2 text-sm font-semibold">{title}</h4>
                <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                  {items.slice(0, 5).map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      )}

      {data.gaps_identificados && data.gaps_identificados.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-semibold">GAPs de mercado</h4>
          <div className="space-y-2">
            {data.gaps_identificados.slice(0, 5).map((g, i) => (
              <div key={i} className="rounded-md border bg-card p-3 text-sm">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-medium">{g.gap}</span>
                  {g.potencial_ticket && (
                    <span className="text-xs text-muted-foreground">{g.potencial_ticket}</span>
                  )}
                </div>
                {g.descricao && (
                  <p className="mt-1 text-muted-foreground">{g.descricao}</p>
                )}
                {g.dificuldade_implementacao && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Dificuldade: {g.dificuldade_implementacao}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {ticket?.comparativo_mercado && Object.keys(ticket.comparativo_mercado).length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold">Comparativo de ticket (mercado)</h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ticket.comparativo_mercado).map(([nome, valor]) => (
              <Badge key={nome} variant="outline" className="font-normal">
                {nome.replace(/_/g, ' ')}: R$ {valor}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
