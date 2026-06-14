/**
 * AlertasViz — alertas/ressalvas na linguagem de card.
 * Drop-in da AlertasGlobais: cada alerta vira um card com borda-acento +
 * ícone por severidade (REPROVADO = crítico/vermelho; demais = ressalva/âmbar).
 */
import type { Veredito } from '@/types/domain'
import { AlertCircle, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface AlertasVizProps {
  alertas: string[] | undefined
  veredito?: Veredito
  className?: string
}

export function AlertasViz({ alertas, veredito, className }: AlertasVizProps) {
  if (!alertas || alertas.length === 0) return null

  const critical = veredito === 'REPROVADO'
  const color = critical
    ? 'hsl(var(--veredito-reprovado))'
    : 'hsl(var(--veredito-ressalvas))'
  const Icon = critical ? AlertCircle : AlertTriangle

  return (
    <div className={cn('grid grid-cols-1 gap-2.5 md:grid-cols-2', className)}>
      {alertas.map((texto, i) => (
        <div
          key={i}
          className="flex items-start gap-3 rounded-xl border border-border bg-card p-4"
          style={{
            borderLeftWidth: 3,
            borderLeftColor: color,
            background: `color-mix(in oklch, ${color} 5%, var(--card))`,
          }}
        >
          <Icon size={16} className="mt-0.5 shrink-0" style={{ color }} />
          <p className="text-sm leading-relaxed text-foreground/90">{texto}</p>
        </div>
      ))}
    </div>
  )
}
