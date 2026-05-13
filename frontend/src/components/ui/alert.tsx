/**
 * Alert — primitivo shadcn/ui (versão copiada, sem CLI).
 *
 * Variantes semânticas alinhadas aos tokens --status-*:
 *  - default — neutro/informativo
 *  - success — confirmação positiva (verde)
 *  - warning — atenção / ressalvas (amarelo)
 *  - destructive — alerta crítico (vermelho)
 *
 * Uso recomendado:
 *   <Alert variant="warning">
 *     <AlertTriangle className="h-4 w-4" />
 *     <AlertTitle>Alerta — Modelo Premium</AlertTitle>
 *     <AlertDescription>...</AlertDescription>
 *   </Alert>
 *
 * O ícone fica posicionado absolutamente no canto esquerdo via CSS — passar
 * apenas o componente do lucide-react como primeiro child.
 */
import { type VariantProps, cva } from 'class-variance-authority'
import { forwardRef, type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const alertVariants = cva(
  'relative w-full rounded-lg border px-4 py-3 text-sm [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg~*]:pl-7',
  {
    variants: {
      variant: {
        default: 'bg-background text-foreground border-border',
        success:
          'border-status-good/40 bg-status-good/5 text-status-good [&>svg]:text-status-good',
        warning:
          'border-status-warning/40 bg-status-warning/5 text-status-warning [&>svg]:text-status-warning',
        investigate:
          'border-status-investigate/40 bg-status-investigate/5 text-status-investigate [&>svg]:text-status-investigate',
        destructive:
          'border-status-critical/40 bg-status-critical/5 text-status-critical [&>svg]:text-status-critical',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface AlertProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  ),
)
Alert.displayName = 'Alert'

export const AlertTitle = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn('mb-1 font-semibold leading-none tracking-tight', className)}
    {...props}
  />
))
AlertTitle.displayName = 'AlertTitle'

export const AlertDescription = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('text-sm leading-relaxed [&_p]:leading-relaxed', className)}
    {...props}
  />
))
AlertDescription.displayName = 'AlertDescription'
