/**
 * PopularTimesHeatmap — grid 7 dias × 24h de intensidade de movimento.
 *
 * Dados: CompetidorJSON.horarios_pico (ex: { domingo: { '00': 0, '18': 87 } }).
 * Agrega múltiplos competidores por média ou máximo.
 *
 * Cores: escala HSL de verde (0%) → amarelo (50%) → vermelho (100%).
 */
import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import type { CompetidorJSON } from '@/hooks/useRelatorioDetail'

const DIAS_ORDEM = [
  'domingo',
  'segunda',
  'terca',
  'quarta',
  'quinta',
  'sexta',
  'sabado',
]

const DIAS_LABEL = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

const HORAS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))

/** Normaliza chaves de dia (acentos, hífens, case). */
function normalizarDia(d: string): string {
  const s = d.toLowerCase().replace(/[-\s]/g, '').replace(/[ç]/g, 'c').replace(/[áãâ]/g, 'a')
  if (s.startsWith('dom')) return 'domingo'
  if (s.startsWith('seg')) return 'segunda'
  if (s.startsWith('ter')) return 'terca'
  if (s.startsWith('qua')) return 'quarta'
  if (s.startsWith('qui')) return 'quinta'
  if (s.startsWith('sex')) return 'sexta'
  if (s.startsWith('sab')) return 'sabado'
  return s
}

function corPorIntensidade(pct: number): string {
  // HSL: 120 (verde) → 60 (amarelo) → 0 (vermelho)
  const hue = Math.max(0, 120 - pct * 1.2)
  return `hsl(${hue} 80% 45%)`
}

function bgCorPorIntensidade(pct: number): string {
  const hue = Math.max(0, 120 - pct * 1.2)
  return `hsl(${hue} 80% 92%)`
}

export interface PopularTimesHeatmapProps {
  competidores: CompetidorJSON[]
  /** 'mean' | 'max' — como agregar quando há múltiplos competidores */
  agregacao?: 'mean' | 'max'
  className?: string
  /** Se true, mostra só 6h-23h (horário comercial + pico) */
  compact?: boolean
}

export function PopularTimesHeatmap({
  competidores,
  agregacao = 'mean',
  className,
  compact = true,
}: PopularTimesHeatmapProps) {
  const horasVisiveis = compact ? HORAS.slice(6) : HORAS

  const matriz = useMemo(() => {
    const resultado: number[][] = DIAS_ORDEM.map(() =>
      horasVisiveis.map(() => 0),
    )
    const contagem: number[][] = DIAS_ORDEM.map(() =>
      horasVisiveis.map(() => 0),
    )

    for (const c of competidores) {
      const hp = c.horarios_pico
      if (!hp) continue
      for (const [diaRaw, horasMap] of Object.entries(hp)) {
        const dia = normalizarDia(diaRaw)
        const diaIdx = DIAS_ORDEM.indexOf(dia)
        if (diaIdx === -1) continue
        for (const [hora, valor] of Object.entries(horasMap)) {
          if (!horasVisiveis.includes(hora)) continue
          const hIdx = horasVisiveis.indexOf(hora)
          const v = typeof valor === 'number' ? valor : 0
          if (agregacao === 'max') {
            resultado[diaIdx][hIdx] = Math.max(resultado[diaIdx][hIdx], v)
          } else {
            resultado[diaIdx][hIdx] += v
            contagem[diaIdx][hIdx] += 1
          }
        }
      }
    }

    if (agregacao === 'mean') {
      for (let d = 0; d < DIAS_ORDEM.length; d++) {
        for (let h = 0; h < horasVisiveis.length; h++) {
          const c = contagem[d][h]
          if (c > 0) resultado[d][h] = resultado[d][h] / c
        }
      }
    }

    return resultado
  }, [competidores, agregacao, horasVisiveis])

  const maxVal = useMemo(() => {
    let m = 0
    for (const row of matriz) {
      for (const v of row) {
        if (v > m) m = v
      }
    }
    return m || 100
  }, [matriz])

  const temDados = competidores.some((c) => c.horarios_pico)

  if (!temDados) {
    return (
      <div className={cn('rounded-lg border border-border bg-card p-4', className)}>
        <p className="text-xs text-muted-foreground text-center py-4">
          Dados de horários de pico indisponíveis para esses competidores.
        </p>
      </div>
    )
  }

  return (
    <div className={cn('rounded-lg border border-border bg-card p-4 overflow-auto', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs uppercase tracking-wider font-mono text-muted-foreground">
          Horários de pico (intensidade %)
        </h3>
        <span className="text-[10px] text-muted-foreground font-mono">
          {agregacao === 'max' ? 'Máx.' : 'Média'} de {competidores.length} concorrente
          {competidores.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="min-w-[420px]">
        {/* Header de horas */}
        <div className="grid" style={{ gridTemplateColumns: `36px repeat(${horasVisiveis.length}, 1fr)` }}>
          <div />
          {horasVisiveis.map((h) => (
            <div key={h} className="text-[9px] text-center text-muted-foreground font-mono py-1">
              {h}h
            </div>
          ))}
        </div>

        {/* Grid de valores */}
        {DIAS_ORDEM.map((dia, dIdx) => (
          <div
            key={dia}
            className="grid items-center"
            style={{ gridTemplateColumns: `36px repeat(${horasVisiveis.length}, 1fr)` }}
          >
            <div className="text-[10px] text-muted-foreground font-medium pr-2">
              {DIAS_LABEL[dIdx]}
            </div>
            {horasVisiveis.map((h, hIdx) => {
              const val = matriz[dIdx][hIdx]
              const pct = maxVal > 0 ? (val / maxVal) * 100 : 0
              return (
                <div
                  key={h}
                  className="h-6 rounded-sm border border-transparent hover:border-foreground/20 transition-colors relative group cursor-default"
                  style={{ backgroundColor: bgCorPorIntensidade(pct) }}
                  title={`${DIAS_LABEL[dIdx]} ${h}h — ${val.toFixed(0)}%`}
                >
                  <div
                    className="absolute bottom-0 left-0 right-0 rounded-sm"
                    style={{
                      height: `${Math.max(4, pct)}%`,
                      backgroundColor: corPorIntensidade(pct),
                      minHeight: pct > 0 ? 2 : 0,
                    }}
                  />
                  {/* Tooltip inline */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10 bg-popover text-popover-foreground text-[10px] px-1.5 py-0.5 rounded shadow border border-border whitespace-nowrap">
                    {val.toFixed(0)}%
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>

      {/* Legenda */}
      <div className="flex items-center gap-2 mt-3 justify-end">
        <span className="text-[9px] text-muted-foreground font-mono">0%</span>
        <div className="w-24 h-2 rounded-full" style={{ background: 'linear-gradient(to right, hsl(120,80%,45%), hsl(60,80%,45%), hsl(0,80%,45%))' }} />
        <span className="text-[9px] text-muted-foreground font-mono">{maxVal.toFixed(0)}%</span>
      </div>
    </div>
  )
}
