/**
 * PosicionamentoCard — output A9 (Framework ERRC / oceano azul).
 */
import { OceanoBadge } from '@/components/domain/OceanoBadge'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PosicionamentoEstrategicoJSON } from '@/hooks/useRelatorioDetail'

const ERRC_LABELS: { key: keyof NonNullable<PosicionamentoEstrategicoJSON['framework_errc']>; title: string; color: string }[] = [
  { key: 'eliminar', title: 'Eliminar', color: 'hsl(var(--veredito-reprovado))' },
  { key: 'reduzir', title: 'Reduzir', color: 'hsl(var(--veredito-ressalvas))' },
  { key: 'aumentar', title: 'Aumentar', color: 'hsl(var(--status-investigate))' },
  { key: 'criar', title: 'Criar', color: 'hsl(var(--veredito-aprovado))' },
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
        {data.fonte_geracao === 'langcache' && (
          <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
            cache A9
          </Badge>
        )}
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

      {data.headroom_renda && data.headroom_renda.headroom_ratio != null && (
        <div className="rounded-xl border border-border p-4">
          <div className="mb-2 flex items-center gap-2">
            <h4 className="text-sm font-semibold">Headroom de renda (determinístico)</h4>
            <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
              IPECE Censo {data.headroom_renda.ano_renda ?? 2022}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-3">
            <Metric label="Renda per capita" value={`R$ ${data.headroom_renda.renda_pc?.toLocaleString('pt-BR')}`} />
            <Metric label="Ranking na cidade" value={`${data.headroom_renda.ranking_cidade}º`} />
            <Metric label="Percentil" value={`${Math.round((data.headroom_renda.renda_percentil ?? 0) * 100)}%`} />
            <Metric label="Ticket sustentável" value={`R$ ${data.headroom_renda.ticket_teto_sustentavel?.toLocaleString('pt-BR')}`} />
            <Metric label="Ticket de mercado" value={`R$ ${data.headroom_renda.ticket_mercado?.toLocaleString('pt-BR')}`} />
            <Metric label="Headroom" value={`R$ ${data.headroom_renda.headroom_premium?.toLocaleString('pt-BR')} (${data.headroom_renda.headroom_ratio}×)`} />
          </div>
          {data.veredito_posicionamento_llm && data.veredito_posicionamento_llm !== data.veredito_posicionamento && (
            <p className="mt-3 text-xs text-muted-foreground">
              Veredito determinístico <strong className="text-foreground">{data.veredito_posicionamento}</strong> (headroom {data.headroom_renda.headroom_ratio}×)
              sobrepõe o do LLM (<span className="line-through">{data.veredito_posicionamento_llm}</span>).
            </p>
          )}
          {data.veto_absorcao_roubo && data.veredito_antes_veto_absorcao && (
            <p className="mt-2 text-xs text-muted-foreground">
              Absorção (disputa com o parque) derrubou{' '}
              <span className="line-through">{data.veredito_antes_veto_absorcao}</span> →{' '}
              <strong className="text-foreground">{data.veredito_posicionamento}</strong>.
            </p>
          )}
        </div>
      )}

      {data.justificativa_veredito && (
        <p className="text-sm leading-relaxed text-muted-foreground">{data.justificativa_veredito}</p>
      )}

      {errc && (
        <div className="grid gap-3 sm:grid-cols-2">
          {ERRC_LABELS.map(({ key, title, color }) => {
            const items = errc[key]
            if (!items?.length) return null
            return (
              <div
                key={key}
                className="rounded-xl border border-border p-4"
                style={{
                  borderLeftWidth: 3,
                  borderLeftColor: color,
                  background: `color-mix(in oklch, ${color} 6%, var(--card))`,
                }}
              >
                <h4 className="mb-2 text-sm font-semibold" style={{ color }}>
                  {title}
                </h4>
                <ul className="space-y-1.5 text-sm text-muted-foreground">
                  {items.slice(0, 5).map((item, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="mt-1.5 size-1 shrink-0 rounded-full" style={{ background: color }} />
                      <span>{item}</span>
                    </li>
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-medium text-foreground">{value}</div>
    </div>
  )
}
