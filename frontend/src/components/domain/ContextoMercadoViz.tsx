/**
 * ContextoMercadoViz — contexto de mercado em mini-cards KPI (não tabela descritiva).
 * Drop-in enxuto da ContextoMercadoCard: números-chave como cards, redes como
 * chips, tendência destacada. Consome o mesmo MarketContextJSON.
 */
import type { MarketContextJSON } from '@/hooks/useRelatorioDetail'
import { Badge } from '@/components/ui/badge'
import { TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ContextoMercadoVizProps {
  marketContext?: MarketContextJSON
  nivelSaturacao?: string | null
  aluguelMedianaM2?: number | null
  totalConcorrentes?: number
  className?: string
}

const brl = (n: unknown) =>
  typeof n === 'number'
    ? new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        maximumFractionDigits: 0,
      }).format(n)
    : null

const txt = (v: unknown) =>
  typeof v === 'string' && v.trim() ? v.trim() : typeof v === 'number' ? String(v) : null

export function ContextoMercadoViz({
  marketContext,
  nivelSaturacao,
  aluguelMedianaM2,
  totalConcorrentes,
  className,
}: ContextoMercadoVizProps) {
  const mc = (marketContext ?? {}) as Record<string, unknown>

  const kpis: { label: string; value: string | null }[] = [
    { label: 'Ticket médio mercado', value: brl(mc.ticket_medio_mercado) },
    { label: 'Aluguel R$/m²', value: brl(aluguelMedianaM2 ?? mc.aluguel_medio_m) },
    { label: 'Renda média bairro', value: brl(mc.renda_media_bairro) },
    { label: 'Faixa etária', value: txt(mc.faixa_etaria_predominante) },
    { label: 'Gênero alvo', value: txt(mc.genero_alvo) },
    { label: 'Parque ativo', value: txt(mc.parque_ativo_total) },
    { label: 'Novos CNPJ fitness', value: txt(mc.novos_cnpj_fitness_ ?? mc.novos_cnpj_fitness) },
    { label: 'Saturação', value: txt(nivelSaturacao) },
    { label: 'Concorrentes analisados', value: txt(totalConcorrentes) },
  ].filter((k) => k.value != null)

  const tendencia = txt(mc.tendencia_mercado)
  const redes = Array.isArray(mc.principais_redes_concorrentes)
    ? (mc.principais_redes_concorrentes as unknown[])
        .map((r) => (typeof r === 'string' ? r : txt((r as Record<string, unknown>)?.nome)))
        .filter((r): r is string => !!r)
    : []

  if (kpis.length === 0 && !tendencia && redes.length === 0) return null

  return (
    <div className={cn('space-y-4', className)}>
      {kpis.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {kpis.map((k) => (
            <div key={k.label} className="rounded-xl border border-border bg-card p-3.5">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {k.label}
              </p>
              <p className="mt-0.5 font-mono text-lg font-semibold leading-tight">{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {tendencia && (
        <div className="flex items-start gap-2.5 rounded-xl border border-primary/40 bg-primary/5 p-4">
          <TrendingUp size={16} className="mt-0.5 shrink-0 text-primary" />
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-primary">
              Tendência de mercado
            </p>
            <p className="text-sm leading-relaxed text-foreground/90">{tendencia}</p>
          </div>
        </div>
      )}

      {redes.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">
            Principais redes concorrentes
          </p>
          <div className="flex flex-wrap gap-2">
            {redes.slice(0, 12).map((r, i) => (
              <Badge key={`${r}-${i}`} variant="secondary" className="font-normal">
                {r}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
