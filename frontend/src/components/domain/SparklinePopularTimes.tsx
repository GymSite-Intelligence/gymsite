/**
 * SparklinePopularTimes — mini gráfico 24h de pico semanal.
 *
 * Recebe `horarios_pico` (7 dias × 24h) e renderiza 24 barras
 * representando a média de movimento por hora (agregada da semana).
 * Largura ~120px, altura ~28px — cabe numa coluna de tabela.
 *
 * Tooltip nativo (title) mostra hora + percentual.
 */
import { useMemo } from 'react'
import { cn } from '@/lib/utils'

export interface SparklinePopularTimesProps {
  horariosPico: Record<string, Record<string, number>> | null | undefined
  picoSemanal?: string | null
  className?: string
}

const HORAS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))

function corPorIntensidade(pct: number): string {
  if (pct >= 70) return 'hsl(0 70% 50%)' // vermelho — muito cheio
  if (pct >= 50) return 'hsl(45 95% 55%)' // amarelo
  if (pct >= 25) return 'hsl(142 60% 45%)' // verde
  return 'hsl(220 10% 45%)' // cinza — pouco movimento
}

export function SparklinePopularTimes({
  horariosPico,
  picoSemanal,
  className,
}: SparklinePopularTimesProps) {
  const mediaPorHora = useMemo<number[] | null>(() => {
    if (!horariosPico || typeof horariosPico !== 'object') return null
    const dias = Object.values(horariosPico)
    if (dias.length === 0) return null
    return HORAS.map((h) => {
      const valores = dias
        .map((d) => (typeof d === 'object' && d ? Number(d[h] ?? 0) : 0))
        .filter((v) => Number.isFinite(v))
      if (!valores.length) return 0
      return Math.round(valores.reduce((a, b) => a + b, 0) / valores.length)
    })
  }, [horariosPico])

  if (!mediaPorHora || mediaPorHora.every((v) => v === 0)) {
    return (
      <span className={cn('text-[10px] italic text-muted-foreground', className)}>
        —
      </span>
    )
  }

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-end gap-[1px] h-7" aria-hidden>
        {mediaPorHora.map((pct, i) => {
          const h = Math.max(2, Math.round((pct / 100) * 28))
          return (
            <div
              key={i}
              title={`${HORAS[i]}h: ${pct}%`}
              className="w-[3px] rounded-sm"
              style={{
                height: `${h}px`,
                background: corPorIntensidade(pct),
                opacity: pct === 0 ? 0.25 : 0.85,
              }}
            />
          )
        })}
      </div>
      {picoSemanal && (
        <p className="text-[10px] text-muted-foreground font-mono leading-tight">
          {picoSemanal}
        </p>
      )}
    </div>
  )
}
