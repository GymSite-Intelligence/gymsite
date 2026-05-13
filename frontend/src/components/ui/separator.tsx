/**
 * Separator — primitivo shadcn/ui simples (sem @radix-ui/react-separator).
 *
 * Vez de instalar radix, usamos uma <div role="separator"> com border.
 * Padrão de uso: separador horizontal de 1px usando token --border.
 */
import { forwardRef, type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export interface SeparatorProps extends HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical'
  decorative?: boolean
}

export const Separator = forwardRef<HTMLDivElement, SeparatorProps>(
  (
    { className, orientation = 'horizontal', decorative = true, ...props },
    ref,
  ) => (
    <div
      ref={ref}
      role={decorative ? 'none' : 'separator'}
      aria-orientation={orientation}
      className={cn(
        'shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        className,
      )}
      {...props}
    />
  ),
)
Separator.displayName = 'Separator'
