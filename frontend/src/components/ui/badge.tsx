/**
 * Badge — primitivo shadcn/ui (versão copiada/customizada, sem CLI).
 *
 * Variantes semânticas alinhadas ao design system v1.6 (tokens --status-*):
 *  - default / secondary / outline / destructive — primitivos
 *  - success / warning / investigate — semânticos (alto valor pro produto)
 *
 * Prop `mono` (default false) ativa a fonte mono — usada em códigos, IDs,
 * valores numéricos. Default sans pra badges de status legíveis ao cliente.
 *
 * Domain components (VeredictoBadge, CategoriaDorBadge) ainda usam
 * className override pra cor customizada; novos usos preferem variants.
 */
import { type VariantProps, cva } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-muted text-foreground',
        outline: 'border-border text-foreground',
        destructive: 'border-transparent bg-status-critical text-white',
        // Semânticos — preferir nos componentes novos
        success: 'border-status-good/40 bg-status-good/10 text-status-good',
        warning: 'border-status-warning/40 bg-status-warning/10 text-status-warning',
        investigate:
          'border-status-investigate/40 bg-status-investigate/10 text-status-investigate',
        critical: 'border-status-critical/40 bg-status-critical/10 text-status-critical',
      },
      mono: {
        true: 'font-mono',
        false: 'font-sans',
      },
    },
    defaultVariants: { variant: 'default', mono: false },
  },
)

export interface BadgeProps
  extends Omit<HTMLAttributes<HTMLSpanElement>, 'className'>,
    VariantProps<typeof badgeVariants> {
  className?: string
}

export function Badge({ className, variant, mono, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, mono }), className)} {...props} />
  )
}

export { badgeVariants }
