/**
 * AlertasGlobais — lista de alertas do A6.
 *
 * UI Lote 1: usa o Alert primitive shadcn-style em vez do bloco custom
 * com texto solto. Cada alerta vira um <Alert> separado com variant
 * baseada no veredito global (critical pra REPROVADO, warning pros demais).
 */
import { AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { cn } from '@/lib/utils'
import type { Veredito } from '@/types/domain'

export interface AlertasGlobaisProps {
  alertas: string[] | undefined
  veredito?: Veredito
  /** Quando true, omite o header inline (útil quando envelopado em Section). */
  hideHeader?: boolean
  className?: string
}

export function AlertasGlobais({
  alertas,
  veredito,
  hideHeader,
  className,
}: AlertasGlobaisProps) {
  if (!alertas || alertas.length === 0) return null

  const variant = veredito === 'REPROVADO' ? 'destructive' : 'warning'
  const titulo =
    veredito === 'REPROVADO' ? 'Alertas críticos' : 'Alertas e ressalvas'

  return (
    <div className={cn('space-y-2.5', className)}>
      {!hideHeader && (
        <header className="flex items-center gap-2 text-xs uppercase tracking-wider font-mono text-muted-foreground">
          <AlertTriangle
            size={12}
            className={cn(
              variant === 'destructive'
                ? 'text-status-critical'
                : 'text-status-warning',
            )}
          />
          {titulo} ({alertas.length})
        </header>
      )}
      <div className="space-y-2">
        {alertas.map((texto, i) => {
          const split = texto.split(':')
          const hasTitulo = split.length > 1 && split[0].length < 60
          const alertTitulo = hasTitulo ? split[0].trim() : null
          const alertDesc = hasTitulo
            ? split.slice(1).join(':').trim()
            : texto
          return (
            <Alert key={i} variant={variant}>
              <AlertTriangle className="h-4 w-4" />
              {alertTitulo && <AlertTitle>{alertTitulo}</AlertTitle>}
              <AlertDescription>{alertDesc}</AlertDescription>
            </Alert>
          )
        })}
      </div>
    </div>
  )
}
