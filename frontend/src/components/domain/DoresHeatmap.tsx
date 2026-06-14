/**
 * DoresHeatmap — dores dominantes do mercado (agregado de todos concorrentes).
 *
 * Aditivo: fica ACIMA da CompetidoresDoresTable (drill-down por concorrente).
 * Re-agrega leve as dores citadas em reviews nota ≤3, por categoria. Cada dor
 * vira um badge colorido + barra de intensidade. Mais citada = maior fraqueza
 * do mercado = sua oportunidade de posicionamento.
 *
 * categoria_dor vem composto do backend (ex: "atendimento_ruim",
 * "equipamento_problema"). Resolve pela BASE (antes do "_") → label + token de
 * cor --color-dor-*; desconhecido degrada com label humanizado + cor heatmap.
 */
import type { CompetidorJSON } from '@/hooks/useRelatorioDetail'
import { cn } from '@/lib/utils'

const BASE: Record<string, { label: string; dor: string }> = {
  atendimento: { label: 'Atendimento', dor: 'atendimento' },
  lotacao: { label: 'Lotação', dor: 'lotacao' },
  equipamento: { label: 'Equipamento', dor: 'equipamento' },
  seguranca: { label: 'Segurança', dor: 'seguranca' },
  climatizacao: { label: 'Climatização', dor: 'climatizacao' },
  contrato: { label: 'Contrato', dor: 'contrato' },
  ausencia: { label: 'Serviço ausente', dor: 'servico' },
  servico: { label: 'Serviço', dor: 'servico' },
  ruido: { label: 'Ruído', dor: 'ruido' },
  estrutura: { label: 'Estrutura', dor: 'estrutura' },
  preco: { label: 'Preço', dor: 'preco' },
  limpeza: { label: 'Limpeza', dor: 'limpeza' },
  horarios: { label: 'Horários', dor: 'horarios' },
  estacionamento: { label: 'Estacionamento', dor: 'estacionamento' },
}

function resolveCat(cat: string, bin: number): { label: string; color: string } {
  // Cor SEMPRE pela rampa heatmap (--chart-* são runtime vars; os --color-dor-*
  // do @theme inline NÃO são acessíveis via var() em runtime).
  const color = `var(--chart-${bin})`
  const base = cat.split('_')[0]
  const m = BASE[base]
  if (m) return { label: m.label, color }
  const label = cat.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
  return { label, color }
}

export interface DoresHeatmapProps {
  competidores: CompetidorJSON[] | undefined
  className?: string
}

export function DoresHeatmap({ competidores, className }: DoresHeatmapProps) {
  if (!competidores || competidores.length === 0) return null

  const counts = new Map<string, number>()
  for (const c of competidores) {
    const reviews = c.reviews ?? c.reviews_traduzidas ?? []
    for (const r of reviews) {
      if ((r.rating ?? 5) > 3) continue
      const cat = (r.categoria_dor || '').trim()
      if (!cat || cat === 'outra') continue
      counts.set(cat, (counts.get(cat) ?? 0) + 1)
    }
  }

  const dores = Array.from(counts.entries())
    .map(([cat, count]) => ({ cat, count }))
    .sort((a, b) => b.count - a.count)

  if (dores.length === 0) return null
  const max = Math.max(...dores.map((d) => d.count), 1)

  return (
    <div className={cn('rounded-xl border border-border bg-card p-4', className)}>
      <p className="mb-3 text-sm font-semibold">
        Dores dominantes do mercado
        <span className="ml-2 text-xs font-normal text-muted-foreground">
          gaps = sua oportunidade
        </span>
      </p>
      <div className="space-y-2">
        {dores.map((d) => {
          const ratio = d.count / max
          const bin = Math.min(5, Math.max(1, Math.ceil(ratio * 5)))
          const { label, color } = resolveCat(d.cat, bin)
          return (
            <div key={d.cat} className="flex items-center gap-3">
              {/* Badge da dor */}
              <span
                className="inline-flex w-36 shrink-0 items-center gap-1.5 truncate rounded-full px-2.5 py-0.5 text-xs font-medium"
                style={{
                  color,
                  background: `color-mix(in oklch, ${color} 15%, transparent)`,
                }}
                title={label}
              >
                <span
                  className="size-1.5 shrink-0 rounded-full"
                  style={{ background: color }}
                />
                <span className="truncate">{label}</span>
              </span>
              {/* Barra de intensidade */}
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${Math.max(5, ratio * 100)}%`, background: color }}
                />
              </div>
              <span className="w-8 shrink-0 text-right font-mono text-sm tabular-nums">
                {d.count}
              </span>
            </div>
          )
        })}
      </div>
      <p className="mt-3 border-t border-border pt-2 text-[11px] text-muted-foreground">
        Reclamações por categoria nas avaliações ≤3★ dos concorrentes · barra = volume
      </p>
    </div>
  )
}
